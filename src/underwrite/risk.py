"""The deterministic gate. No LLM. Every rejection is a sentence a judge can read."""
from __future__ import annotations

import math

from . import ledger
from .calibration import CalibrationState
from .config import RISK
from .market import LegQuote, dte
from .models import GateDecision, Proposal


def _structure_math(p: Proposal, q: dict[str, LegQuote]) -> tuple[float, float, list[str]]:
    """Returns (net_credit_per_share at mid, max_loss_per_1x in $, notes). Positive credit = received."""
    notes: list[str] = []
    credit = 0.0
    for leg in p.legs:
        lq = q[leg.symbol]
        credit += lq.mid * leg.ratio_qty if leg.side == "sell" else -lq.mid * leg.ratio_qty
    credit = round(credit, 4)
    puts = sorted([l for l in p.legs if l.right == "put"], key=lambda l: l.strike)
    calls = sorted([l for l in p.legs if l.right == "call"], key=lambda l: l.strike)

    def width(legs):
        return (legs[-1].strike - legs[0].strike) if len(legs) == 2 else 0.0

    if p.structure in ("bull_put_spread", "bear_put_spread") and len(puts) == 2:
        w = width(puts)
    elif p.structure in ("bear_call_spread", "bull_call_spread") and len(calls) == 2:
        w = width(calls)
    elif p.structure == "iron_condor" and len(puts) == 2 and len(calls) == 2:
        w = max(width(puts), width(calls))
    else:
        return credit, math.inf, [f"unrecognised leg layout for {p.structure}"]
    if credit >= 0:
        max_loss = (w - credit) * 100
        notes.append(f"defined risk: width {w:.2f} - credit {credit:.2f} = {w - credit:.2f}/share")
    else:
        max_loss = (-credit) * 100
        notes.append(f"debit structure: max loss = debit {-credit:.2f}/share")
    return credit, round(max_loss, 2), notes


def evaluate(proposal_id: str, p: Proposal, q: dict[str, LegQuote], equity: float, open_positions: list[dict], calib: CalibrationState) -> GateDecision:
    reasons: list[str] = []
    reject = False

    if p.underlying not in RISK.allowed_underlyings:
        reject, _ = True, reasons.append(f"{p.underlying} not in the liquid-underlyings allowlist")
    if not (2 <= len(p.legs) <= 4):
        reject, _ = True, reasons.append("only 2–4 leg defined-risk structures are allowed")
    if p.p_profit < RISK.min_p_profit:
        reject, _ = True, reasons.append(f"stated p_profit {p.p_profit:.2f} < {RISK.min_p_profit} — no claimed edge, no trade")
    for leg in p.legs:
        d = dte(leg.expiration)
        if not (RISK.min_dte <= d <= RISK.max_dte):
            reject, _ = True, reasons.append(f"{leg.symbol}: {d} DTE outside [{RISK.min_dte},{RISK.max_dte}]")
        lq = q.get(leg.symbol)
        if lq is None or lq.mid <= 0:
            reject, _ = True, reasons.append(f"{leg.symbol}: no live quote")
            continue
        if lq.spread_frac > RISK.max_bid_ask_spread_frac and (lq.ask - lq.bid) > RISK.max_abs_spread + 1e-9:
            reject, _ = True, reasons.append(f"{leg.symbol}: bid/ask spread {lq.spread_frac:.0%} > {RISK.max_bid_ask_spread_frac:.0%} and wider than ${RISK.max_abs_spread:.2f}")
        if lq.open_interest is not None and lq.open_interest < RISK.min_open_interest:
            reject, _ = True, reasons.append(f"{leg.symbol}: open interest {lq.open_interest} < {RISK.min_open_interest}")

    # concurrency, from the CLI's view of positions (truth), not the agent's memory
    open_underlyings = [pos.get("symbol", "")[:6].rstrip("0123456789") for pos in open_positions if pos.get("asset_class") == "us_option"]
    distinct = {u for u in open_underlyings if u}
    if len(distinct) >= RISK.max_open_structures:
        reject, _ = True, reasons.append(f"{len(distinct)} structures already open ≥ cap {RISK.max_open_structures}")
    if sum(1 for u in open_underlyings if u == p.underlying) >= RISK.max_structures_per_underlying * 2:  # 2 legs per structure
        reject, _ = True, reasons.append(f"already positioned in {p.underlying}")

    credit_mid, max_loss, notes = (0.0, math.inf, []) if any(l.symbol not in q for l in p.legs) else _structure_math(p, q)
    reasons.extend(notes)
    if max_loss is math.inf or max_loss <= 0:
        reject, _ = True, reasons.append("could not compute a finite max loss from live quotes")
    else:
        if abs(p.max_loss_per_structure - max_loss) > 0.25 * max_loss:
            reasons.append(f"strategist stated max loss {p.max_loss_per_structure:.0f} vs verified {max_loss:.0f} — using verified")
        cap = equity * RISK.max_loss_per_trade_frac
        if max_loss > cap:
            reject, _ = True, reasons.append(f"verified max loss ${max_loss:.0f} per 1x > 1% of equity (${cap:.0f})")

    qty = 0
    if not reject:
        budget = equity * calib.risk_frac
        qty = int(budget // max_loss)
        if qty < 1:
            # The floor is "one structure", never zero: a desk that cannot trade can never earn calibration.
            # The 1%-of-equity hard cap on max loss was already enforced above.
            qty = 1
            reasons.append(f"floor sizing 1x: budget ${budget:.0f} ({calib.risk_frac:.2%} of equity, {'earned' if calib.earned else 'calibration not yet earned'}) < max loss ${max_loss:.0f}; the 1% hard cap still holds")
        else:
            qty = min(qty, 5)
            reasons.append(f"sized {qty}x: budget ${budget:.0f} = {calib.risk_frac:.2%} of equity ({'earned' if calib.earned else 'floor'}), verified max loss ${max_loss:.0f}/structure")

    dec = GateDecision(proposal_id=proposal_id, accepted=not reject, reasons=reasons, qty=qty, risk_frac_used=calib.risk_frac if not reject else 0.0, equity=equity, verified_max_loss=None if max_loss is math.inf else max_loss, verified_mid_credit=credit_mid)
    ledger.append("gate", {"decision_id": ledger.new_id("dec"), **dec.model_dump()})
    return dec
