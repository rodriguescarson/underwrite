"""Builds docs/REPORT.md and docs/index.html from the ledger. Every number here has a ledger line behind it."""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

from . import calibration, ledger
from .config import RISK, ROOT

DOCS = ROOT / "docs"


def _table(rows: list[list[str]], header: list[str]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def build() -> tuple[str, str]:
    state = calibration.compute()
    snaps = [a for a in ledger.read("audits") if a.get("type") == "snapshot"]
    claims = ledger.read("orders")
    audits = ledger.latest_by("audits", "claim_id")
    gates = ledger.read("gate")
    props = ledger.read("proposals")
    outcomes = ledger.read("outcomes")
    first, last = (snaps[0] if snaps else {}), (snaps[-1] if snaps else {})

    md = [f"# Underwrite — desk report", f"_Generated {datetime.now(timezone.utc).isoformat(timespec='minutes')} from the ledger. Action channel: Alpaca MCP server. Audit channel: Alpaca CLI {last.get('cli_version', '')}._", ""]
    md += ["## Account (as the CLI sees it)", _table([[first.get("ts", "—"), first.get("equity", "—"), last.get("ts", "—"), last.get("equity", "—"), last.get("account_number", "—")]], ["first snapshot", "equity", "latest snapshot", "equity", "account"]), ""]
    md += ["## Calibration — the numbers that set position size", _table([[state.n_claims, state.n_audited, state.claim_accuracy, state.silent_failures, state.n_resolved, state.wins, state.brier, state.ece, f"{state.risk_frac:.2%}", "earned" if state.earned else "floor"]], ["claims", "audited", "claim accuracy", "silent failures", "resolved", "wins", "Brier", "ECE", "risk/trade", "status"]), "", "Gate verdict: " + "; ".join(state.reasons), ""]
    md += ["## Claims vs. audits (executor said → CLI observed)", _table([[c["ts"][:19], c.get("kind"), c.get("underlying"), c.get("structure"), c.get("qty"), c.get("limit_price"), c.get("claimed_status"), audits.get(c["claim_id"], {}).get("observed_status", "—"), "✔" if audits.get(c["claim_id"], {}).get("matches_claim") else "✘", (c.get("order_id") or "—")[:8]] for c in claims], ["time", "kind", "underlying", "structure", "qty", "limit", "claimed", "observed", "match", "order"]) if claims else "_no orders yet_", ""]
    md += ["## Gate decisions", _table([[g["ts"][:19], "accept" if g.get("accepted") else "reject", g.get("qty", 0), "<br>".join(html.escape(r) for r in g.get("reasons", []))] for g in gates], ["time", "verdict", "qty", "reasons"]) if gates else "_none_", ""]
    md += ["## Strategist proposals", _table([[p["ts"][:19], p.get("model"), len(p.get("tool_calls") or []), "no trade" if (p.get("proposal") or {}).get("no_trade") else ((p.get("proposal") or {}).get("structure", "unparsed")), (p.get("proposal") or {}).get("p_profit", "—"), html.escape(str((p.get("proposal") or {}).get("thesis") or (p.get("proposal") or {}).get("reason") or "")[:220])] for p in props], ["time", "model", "tool calls", "structure", "p_profit", "thesis"]) if props else "_none_", ""]
    md += ["## Resolved structures", _table([[o["ts"][:19], o.get("underlying"), o.get("structure"), o.get("p_profit"), "win" if o.get("win") else "loss", o.get("pnl"), o.get("exit_reason")] for o in outcomes if o.get("resolved")], ["time", "underlying", "structure", "p_profit", "result", "P&L $", "exit"]) if outcomes else "_none resolved yet — provisional MTM is in the latest snapshot below_", ""]
    md += ["## Open positions, mark-to-market (latest CLI snapshot)", _table([[p.get("symbol"), p.get("qty"), p.get("avg_entry"), p.get("market_value"), p.get("unrealized_pl")] for p in last.get("positions_mtm", [])], ["symbol", "qty", "avg entry", "market value", "unrealized P&L"]) if last.get("positions_mtm") else "_flat_", ""]
    md += ["## The gate's constants", _table([[k, v] for k, v in RISK.__dict__.items()], ["parameter", "value"]), ""]
    curve = calibration.coverage_curve()
    if curve:
        md += ["## Risk–coverage (auto-accept threshold on stated p_profit)", _table([[c["threshold"], c["coverage"], c["risk"], c["n"]] for c in curve], ["threshold", "coverage", "residual risk", "n"]), ""]
    text = "\n".join(md)
    page = "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Underwrite — desk report</title><style>body{font:15px/1.5 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#111}table{border-collapse:collapse;width:100%;font-size:13px;margin:.5rem 0 1.5rem}th,td{border:1px solid #ddd;padding:.35rem .5rem;text-align:left;vertical-align:top}th{background:#f3f3f3}h1{margin-bottom:0}h2{margin-top:2rem;border-bottom:1px solid #ddd;padding-bottom:.25rem}code{background:#f3f3f3;padding:0 .25rem}</style>" + _md_to_html(text)
    return text, page


def _md_to_html(md: str) -> str:
    out, in_table = [], False
    for line in md.splitlines():
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= set("-") for c in cells):
                continue
            tag = "th" if not in_table else "td"
            if not in_table:
                out.append("<table>")
                in_table = True
            out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
            continue
        if in_table:
            out.append("</table>")
            in_table = False
        if line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("_") and line.endswith("_"):
            out.append(f"<p><em>{html.escape(line.strip('_'))}</em></p>")
        elif line.strip():
            out.append(f"<p>{html.escape(line)}</p>")
    if in_table:
        out.append("</table>")
    return "\n".join(out)


def write() -> Path:
    DOCS.mkdir(exist_ok=True)
    md, page = build()
    (DOCS / "REPORT.md").write_text(md)
    (DOCS / "index.html").write_text(page)
    (DOCS / "ledger.json").write_text(json.dumps(ledger.dump_all(), indent=1, default=str))
    return DOCS / "REPORT.md"
