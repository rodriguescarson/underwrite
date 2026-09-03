"""Fill docs/deck.html placeholders from the ledger and render docs/deck.pdf via headless Chrome."""
import json, subprocess
from pathlib import Path
from underwrite import calibration, ledger

ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / "docs" / "deck.html").read_text()
state = calibration.compute()
props = ledger.read("proposals"); gates = ledger.read("gate"); orders = ledger.read("orders"); audits = ledger.latest_by("audits", "claim_id"); outcomes = [o for o in ledger.read("outcomes") if o.get("resolved")]
snaps = [a for a in ledger.read("audits") if a.get("type") == "snapshot"]
opens = [o for o in orders if o.get("kind") == "open"]
filled = [o for o in opens if audits.get(o["claim_id"], {}).get("observed_status") == "filled"]
at_risk = 0.0
for o in filled:
    g = next((g for g in gates if g.get("proposal_id") == o["proposal_id"]), {})
    at_risk += float(g.get("verified_max_loss") or 0) * int(o.get("qty") or 1)
pnl = sum(float(o.get("pnl") or 0) for o in outcomes)
mtm = sum(float(p.get("unrealized_pl") or 0) for p in (snaps[-1].get("positions_mtm", []) if snaps else []))
vals = {
    "SESSION_DATE": (snaps[0]["ts"][:10] if snaps else "—") + (" → " + snaps[-1]["ts"][:10] if len(snaps) > 1 and snaps[-1]["ts"][:10] != snaps[0]["ts"][:10] else ""),
    "N_PROPOSALS": str(len(props)), "N_ACCEPTED": str(sum(1 for g in gates if g.get("accepted"))),
    "CLAIM_ACC": f"{state.claim_accuracy:.0%}" if state.claim_accuracy is not None else "—", "SILENT": str(state.silent_failures),
    "PNL": f"${pnl:+,.0f} realised, ${mtm:+,.0f} MTM", "AT_RISK": f"${at_risk:,.0f}",
    "N_RESOLVED": str(state.n_resolved), "BRIER": f"{state.brier}" if state.brier is not None else "n/a", "ECE": f"{state.ece}" if state.ece is not None else "n/a",
    "VERDICT": "floor — " + "; ".join(state.reasons),
}
for k, v in vals.items():
    html = html.replace("{{" + k + "}}", v)
out = ROOT / "docs" / "deck.filled.html"
out.write_text(html)
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={ROOT/'docs'/'deck.pdf'}", f"file://{out}"], check=False, capture_output=True)
print(json.dumps(vals, indent=1)); print("deck.pdf", (ROOT / "docs" / "deck.pdf").stat().st_size, "bytes")
