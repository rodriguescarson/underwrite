"""One cycle of the desk. Order matters: truth first, then claims, then new risk.

  1. snapshot       CLI → account, positions, clock            (audits.jsonl, type=snapshot)
  2. reconcile      every open claim re-checked through the CLI (audits.jsonl, type=claim)
  3. exits          open structures against the exit plan      (orders.jsonl, kind=close)
  4. calibration    the three numbers → risk fraction
  5. strategist     Gemini over MCP proposes or declines        (proposals.jsonl)
  6. gate           deterministic re-pricing + sizing           (gate.jsonl)
  7. execute        MCP place_option_order → CLAIM              (orders.jsonl, kind=open)
  8. audit          CLI confirms or contradicts the claim       (audits.jsonl)
"""
from __future__ import annotations

import re
import time
from typing import Any

from . import agent, audit_cli, calibration, ledger, market, mcp_exec, risk
from .config import RISK
from .models import Leg, Proposal

TERMINAL = {"filled", "canceled", "expired", "rejected", "replaced", "done_for_day"}
STATUS_RE = re.compile(r"status[\"':\s]+([a-z_]+)", re.I)


def _underlying_of(occ: str) -> str:
    return re.match(r"^([A-Z]+)", occ).group(1) if re.match(r"^([A-Z]+)", occ) else occ


def snapshot() -> dict[str, Any]:
    acct = audit_cli.account()
    positions = audit_cli.positions()
    clock = audit_cli.clock()
    mtm = [{"symbol": p.get("symbol"), "qty": p.get("qty"), "avg_entry": p.get("avg_entry_price"), "market_value": p.get("market_value"), "unrealized_pl": p.get("unrealized_pl")} for p in positions if p.get("asset_class") == "us_option"]
    rec = ledger.append("audits", {"type": "snapshot", "claim_id": None, "account_number": acct.get("account_number"), "equity": acct.get("equity"), "cash": acct.get("cash"), "options_buying_power": acct.get("options_buying_power"), "n_positions": len(positions), "positions_mtm": mtm, "market_open": clock.get("is_open"), "next_open": clock.get("next_open"), "next_close": clock.get("next_close"), "cli_version": audit_cli.version()})
    return {"account": acct, "positions": positions, "clock": clock, "snapshot": rec}


def audit_claim(claim: dict[str, Any]) -> dict[str, Any]:
    """The CLI has the last word on what an order is."""
    oid = claim.get("order_id")
    observed = None
    if oid:
        try:
            observed = audit_cli.order(oid)
        except audit_cli.CliError as e:
            observed = {"_error": str(e)}
    if not oid or (observed and "_error" in observed):
        for o in audit_cli.orders(status="all", limit=200):
            if o.get("client_order_id") == claim.get("client_order_id"):
                observed = o
                oid = o.get("id")
                break
    if not observed or "_error" in observed:
        rec = {"type": "claim", "claim_id": claim["claim_id"], "order_id": oid, "observed": False, "observed_status": None, "observed_filled_qty": 0, "matches_claim": False, "note": "CLI cannot find the order the executor claimed to have placed"}
    else:
        st = observed.get("status")
        fq = float(observed.get("filled_qty") or 0)
        claimed = claim.get("claimed_status")
        consistent = (claimed == st) or (claimed in ("accepted", "new", "pending_new", "unknown") and st in ("new", "accepted", "pending_new", "partially_filled", "filled", "canceled", "expired"))
        if claimed in ("filled", "partially_filled") and st not in ("filled", "partially_filled"):
            consistent = False
        legs = observed.get("legs") or []
        rec = {"type": "claim", "claim_id": claim["claim_id"], "order_id": oid, "observed": True, "observed_status": st, "observed_filled_qty": fq, "observed_filled_avg_price": observed.get("filled_avg_price"), "observed_legs": [{"symbol": l.get("symbol"), "side": l.get("side"), "filled_qty": l.get("filled_qty"), "filled_avg_price": l.get("filled_avg_price"), "status": l.get("status")} for l in legs], "matches_claim": bool(consistent), "note": "" if consistent else f"executor claimed {claimed}, CLI observes {st}"}
    return ledger.append("audits", rec)


def reconcile() -> int:
    latest = ledger.latest_by("audits", "claim_id")
    n = 0
    for c in ledger.read("orders"):
        a = latest.get(c["claim_id"])
        if a is None or a.get("observed_status") not in TERMINAL:
            audit_claim(c)
            n += 1
    return n


def open_structures() -> list[dict[str, Any]]:
    """Structures whose opening order the CLI has confirmed filled and that have no filled close."""
    latest = ledger.latest_by("audits", "claim_id")
    claims = ledger.read("orders")
    closed = {c["closes_proposal_id"] for c in claims if c.get("kind") == "close" and latest.get(c["claim_id"], {}).get("observed_status") == "filled"}
    out = []
    for c in claims:
        if c.get("kind") != "open":
            continue
        a = latest.get(c["claim_id"], {})
        if a.get("observed_status") == "filled" and c["proposal_id"] not in closed:
            out.append({**c, "audit": a})
    return out


def _fill_credit(audit: dict[str, Any], legs: list[dict[str, Any]]) -> float | None:
    """Net credit per share actually received, from the CLI's per-leg fills."""
    by = {l["symbol"]: l for l in audit.get("observed_legs", []) if l.get("filled_avg_price") is not None}
    if len(by) < len(legs):
        return None
    total = 0.0
    for l in legs:
        px = float(by[l["symbol"]]["filled_avg_price"])
        total += px * l["ratio_qty"] if l["side"] == "sell" else -px * l["ratio_qty"]
    return round(total, 4)


def manage_exits(dry: bool = False) -> list[dict[str, Any]]:
    actions = []
    for s in open_structures():
        legs = s["legs"]
        q = market.quotes_for([l["symbol"] for l in legs])
        if any(l["symbol"] not in q for l in legs):
            continue
        open_credit = _fill_credit(s["audit"], legs)
        if open_credit is None:
            open_credit = -float(s["limit_price"])
        cur = round(sum(q[l["symbol"]].mid * l["ratio_qty"] * (1 if l["side"] == "sell" else -1) for l in legs), 4)
        pnl = round(open_credit - cur, 4)  # per share
        min_dte = min(market.dte(l["expiration"]) for l in legs)
        reason = None
        if open_credit > 0 and pnl >= 0.5 * open_credit:
            reason = f"take profit: captured {pnl:.2f} of {open_credit:.2f} credit"
        elif open_credit > 0 and pnl <= -1.0 * open_credit:
            reason = f"stop: loss {pnl:.2f} reached 1x credit ({open_credit:.2f}), 2x-credit exit rule"
        elif open_credit < 0 and pnl >= 0.5 * abs(open_credit):
            reason = f"take profit on debit structure: +{pnl:.2f}"
        elif open_credit < 0 and pnl <= -0.5 * abs(open_credit):
            reason = f"stop on debit structure: {pnl:.2f}"
        elif min_dte <= 2:
            reason = f"time exit: {min_dte} DTE"
        actions.append({"proposal_id": s["proposal_id"], "open_credit": open_credit, "current_credit": cur, "pnl_per_share": pnl, "min_dte": min_dte, "exit": reason})
        if reason and not dry:
            rev = [{"symbol": l["symbol"], "ratio_qty": str(l["ratio_qty"]), "side": "buy" if l["side"] == "sell" else "sell", "position_intent": "buy_to_close" if l["side"] == "sell" else "sell_to_close"} for l in legs]
            limit = cur + 0.03 if cur > 0 else cur - 0.03  # pay up a little to get out
            coid = ledger.new_id("uwc")
            text = mcp_exec.place_mleg(rev, int(s["qty"]), limit, coid)
            oid = mcp_exec.parse_order_id(text)
            m = STATUS_RE.search(text)
            claim = ledger.append("orders", {"claim_id": ledger.new_id("clm"), "kind": "close", "closes_proposal_id": s["proposal_id"], "proposal_id": s["proposal_id"], "decision_id": None, "order_id": oid, "client_order_id": coid, "claimed_status": (m.group(1).lower() if m else "unknown"), "p_profit": s["p_profit"], "underlying": s["underlying"], "structure": s["structure"], "legs": [{**l, "side": r["side"]} for l, r in zip(legs, rev)], "qty": s["qty"], "limit_price": round(limit, 2), "exit_reason": reason, "open_credit": open_credit, "mcp_response": text[:2000]})
            time.sleep(2)
            audit_claim(claim)
    return actions


def resolve_outcomes() -> int:
    """A structure resolves when the CLI confirms its closing order filled. P&L from CLI fills only."""
    latest = ledger.latest_by("audits", "claim_id")
    already = {o["proposal_id"] for o in ledger.read("outcomes") if o.get("resolved")}
    n = 0
    for c in ledger.read("orders"):
        if c.get("kind") != "close" or c["closes_proposal_id"] in already:
            continue
        a = latest.get(c["claim_id"], {})
        if a.get("observed_status") != "filled":
            continue
        close_debit = _fill_credit(a, c["legs"])  # sells are now buys → this is -(debit paid)
        open_credit = float(c.get("open_credit") or 0)
        pnl_share = round(open_credit + (close_debit if close_debit is not None else -float(c["limit_price"])), 4)
        pnl = round(pnl_share * 100 * int(c["qty"]), 2)
        ledger.append("outcomes", {"proposal_id": c["closes_proposal_id"], "p_profit": c["p_profit"], "win": pnl > 0, "pnl": pnl, "pnl_per_share": pnl_share, "resolved": True, "exit_reason": c.get("exit_reason"), "underlying": c["underlying"], "structure": c["structure"]})
        already.add(c["closes_proposal_id"])
        n += 1
    return n


def run_once(dry: bool = False) -> dict[str, Any]:
    log: dict[str, Any] = {"dry": dry}
    snap = snapshot()
    log["equity"] = snap["account"].get("equity")
    log["reconciled"] = reconcile()
    log["exits"] = manage_exits(dry=dry)
    log["resolved"] = resolve_outcomes()
    state = calibration.compute()
    log["calibration"] = state.as_dict()
    if not snap["clock"].get("is_open"):
        log["skipped"] = f"market closed (next open {snap['clock'].get('next_open')})"
        return log
    opens = open_structures()
    if len(opens) >= RISK.max_open_structures:
        log["skipped"] = f"{len(opens)} structures open, cap {RISK.max_open_structures}"
        return log
    context = {"equity": snap["account"].get("equity"), "open_structures": [{"underlying": s["underlying"], "structure": s["structure"]} for s in opens], "risk_frac_available": state.risk_frac, "calibration": state.reasons, "held_symbols": [p.get("symbol") for p in snap["positions"]]}
    pj, transcript, calls, model = agent.propose(context)
    prop_rec = ledger.append("proposals", {"proposal_id": ledger.new_id("prp"), "model": model, "tool_calls": calls, "proposal": pj, "transcript": transcript[-6000:]})
    log["strategist"] = {"model": model, "tool_calls": calls, "no_trade": bool(pj and pj.get("no_trade")), "parsed": pj is not None}
    if not pj or pj.get("no_trade"):
        log["skipped"] = "strategist declined" if pj else "strategist returned no parsable proposal"
        return log
    try:
        p = Proposal(**{**pj, "legs": [Leg(**l) for l in pj["legs"]]})
    except Exception as e:
        ledger.append("gate", {"decision_id": ledger.new_id("dec"), "proposal_id": prop_rec["proposal_id"], "accepted": False, "reasons": [f"proposal failed schema validation: {e}"], "qty": 0})
        log["skipped"] = f"schema: {e}"
        return log
    q = market.quotes_for([l.symbol for l in p.legs])
    dec = risk.evaluate(prop_rec["proposal_id"], p, q, float(snap["account"]["equity"]), snap["positions"], state)
    log["gate"] = dec.model_dump()
    if not dec.accepted or dry:
        return log
    credit = dec.verified_mid_credit or 0.0
    limit = -(credit - 0.02) if credit > 0 else (-credit + 0.02)  # mleg convention: negative = credit
    legs = [{"symbol": l.symbol, "ratio_qty": str(l.ratio_qty), "side": l.side, "position_intent": "sell_to_open" if l.side == "sell" else "buy_to_open"} for l in p.legs]
    coid = ledger.new_id("uwo")
    text = mcp_exec.place_mleg(legs, dec.qty, limit, coid)
    oid = mcp_exec.parse_order_id(text)
    m = STATUS_RE.search(text)
    dec_id = ledger.read("gate")[-1]["decision_id"]
    claim = ledger.append("orders", {"claim_id": ledger.new_id("clm"), "kind": "open", "proposal_id": prop_rec["proposal_id"], "decision_id": dec_id, "order_id": oid, "client_order_id": coid, "claimed_status": (m.group(1).lower() if m else "unknown"), "p_profit": p.p_profit, "underlying": p.underlying, "structure": p.structure, "legs": [l.model_dump() for l in p.legs], "qty": dec.qty, "limit_price": round(limit, 2), "thesis": p.thesis, "mcp_response": text[:2000]})
    time.sleep(3)
    a = audit_claim(claim)
    log["order"] = {"order_id": oid, "claimed": claim["claimed_status"], "observed": a.get("observed_status"), "matches": a.get("matches_claim")}
    return log
