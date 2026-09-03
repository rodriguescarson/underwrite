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
    """Runs the second strategist (if configured) and records its view against the primary proposal."""
    model = second_model()
    if not model:
        return True, "no second model configured", None
    prev_primary, prev_fallback = agent.MODEL, agent.FALLBACK_MODEL
    agent.MODEL, agent.FALLBACK_MODEL = model, model
    try:
        pj, text, calls, used = agent.propose(context, attempts=2)
    finally:
        agent.MODEL, agent.FALLBACK_MODEL = prev_primary, prev_fallback
    ok, why = agree(primary, pj)
    ledger.append("proposals", {"proposal_id": ledger.new_id("prp"), "role": "second_opinion", "for_proposal": proposal_id, "model": used, "tool_calls": calls, "proposal": pj, "agreement": ok, "why": why, "transcript": (text or "")[-3000:]})
    return ok, why, pj
