"""Second opinion. Two strategists with different models propose independently; the desk only
acts when they agree on the underlying and the direction. Disagreement is recorded, not traded.

Agreement is deliberately coarse (underlying + bullish/bearish), because two models will never
name identical strikes; the primary's legs are what the gate re-prices."""
from __future__ import annotations

import os
from typing import Any

from . import agent, ledger

BULLISH = {"bull_put_spread", "bull_call_spread"}
BEARISH = {"bear_call_spread", "bear_put_spread"}


def direction(structure: str | None) -> str:
    if structure in BULLISH:
        return "bullish"
    if structure in BEARISH:
        return "bearish"
    if structure == "iron_condor":
        return "neutral"
    return "none"


def agree(a: dict[str, Any] | None, b: dict[str, Any] | None) -> tuple[bool, str]:
    if not a or a.get("no_trade"):
        return False, "primary declined"
    if not b or b.get("no_trade"):
        return False, "second opinion declined"
    if a.get("underlying") != b.get("underlying"):
        return False, f"underlying disagreement: {a.get('underlying')} vs {b.get('underlying')}"
    da, db = direction(a.get("structure")), direction(b.get("structure"))
    if da != db:
        return False, f"direction disagreement on {a.get('underlying')}: {da} vs {db}"
    return True, f"agreed: {a.get('underlying')} {da} (p={a.get('p_profit')} / {b.get('p_profit')})"


def second_model() -> str | None:
    return os.getenv("UNDERWRITE_SECOND_MODEL") or None


def consult(context: dict[str, Any], primary: dict[str, Any] | None, proposal_id: str) -> tuple[bool, str, dict[str, Any] | None]:
    """Runs the second opinion (if configured) and records its view against the primary proposal.

    UNDERWRITE_COMMITTEE=review (default): the second model reviews THIS trade and must agree; its own
    p_profit is recorded and the gate uses the more conservative of the two.
    UNDERWRITE_COMMITTEE=independent: the second model proposes on its own; agreement = same underlying + direction."""
    model = second_model()
    if not model or not primary or primary.get("no_trade"):
        return True, "no second model configured" if not model else "primary declined", None
    mode = os.getenv("UNDERWRITE_COMMITTEE", "review")
    if mode == "independent":
        prev_primary, prev_fallback = agent.MODEL, agent.FALLBACK_MODEL
        agent.MODEL, agent.FALLBACK_MODEL = model, model
        try:
            pj, text, calls, used = agent.propose(context, attempts=2)
        finally:
            agent.MODEL, agent.FALLBACK_MODEL = prev_primary, prev_fallback
        ok, why = agree(primary, pj)
        ledger.append("proposals", {"proposal_id": ledger.new_id("prp"), "role": "second_opinion", "mode": mode, "for_proposal": proposal_id, "model": used, "tool_calls": calls, "proposal": pj, "agreement": ok, "why": why, "transcript": (text or "")[-3000:]})
        return ok, why, pj
    rj, text, calls = agent.review(context, primary, model)
    if not rj or "agree" not in rj:
        why = "second opinion returned no parsable review — trade not taken"
        ledger.append("proposals", {"proposal_id": ledger.new_id("prp"), "role": "second_opinion", "mode": mode, "for_proposal": proposal_id, "model": model, "tool_calls": calls, "proposal": rj, "agreement": False, "why": why, "transcript": (text or "")[-3000:]})
        return False, why, rj
    ok = bool(rj.get("agree"))
    p2 = rj.get("p_profit")
    why = (f"agreed: reviewer p={p2} vs primary p={primary.get('p_profit')}" if ok else f"vetoed: {'; '.join(str(o) for o in (rj.get('objections') or [])[:3]) or rj.get('reasoning', '')[:160]}")
    ledger.append("proposals", {"proposal_id": ledger.new_id("prp"), "role": "second_opinion", "mode": mode, "for_proposal": proposal_id, "model": model, "tool_calls": calls, "proposal": rj, "agreement": ok, "why": why, "transcript": (text or "")[-3000:]})
    if ok and isinstance(p2, (int, float)) and isinstance(primary.get("p_profit"), (int, float)):
        primary["p_profit_primary"] = primary["p_profit"]
        primary["p_profit"] = round(min(float(p2), float(primary["p_profit"])), 4)  # the desk records the more conservative belief
    return ok, why, rj
