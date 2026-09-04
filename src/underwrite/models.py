"""Typed records shared by the strategist, the gate, the executor and the auditor."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Side = Literal["buy", "sell"]
Intent = Literal["buy_to_open", "sell_to_open", "buy_to_close", "sell_to_close"]
Structure = Literal["bull_put_spread", "bear_call_spread", "iron_condor", "bull_call_spread", "bear_put_spread"]


class Leg(BaseModel):
    symbol: str = Field(description="OCC option symbol, e.g. SPY260918P00600000")
    side: Side
    ratio_qty: int = 1
    strike: float
    right: Literal["call", "put"]
    expiration: str = Field(description="YYYY-MM-DD")


class Proposal(BaseModel):
    """What the strategist claims. Everything here is re-verified by the gate against live quotes."""

    underlying: str
    structure: Structure
    legs: list[Leg]
    net_credit: float = Field(description="Per 1x structure, in $ per share (positive = credit received, negative = debit paid)")
    max_loss_per_structure: float = Field(description="$ per 1x structure, contract multiplier applied (100)")
    limit_price: float = Field(description="Limit for the multi-leg order, $ per share; positive number, direction given by side of first leg per Alpaca mleg convention")
    p_profit: float = Field(ge=0, le=1, description="The desk's recorded probability this structure is closed for a profit (the more conservative of primary and reviewer when a second opinion ran)")
    p_profit_primary: Optional[float] = Field(default=None, description="The primary strategist's own number, when a reviewer adjusted p_profit")
    thesis: str
    data_cited: list[str] = Field(description="Which live tool results the thesis rests on")
    exit_plan: str = "take profit at 50% of credit, stop at 2x credit, close at 2 DTE"


class GateDecision(BaseModel):
    proposal_id: str
    accepted: bool
    reasons: list[str]
    qty: int = 0
    risk_frac_used: float = 0.0
    equity: float = 0.0
    verified_max_loss: Optional[float] = None
    verified_mid_credit: Optional[float] = None


class Claim(BaseModel):
    """The executor's claim: 'I placed this order and here is what the MCP server said.'"""

    proposal_id: str
    decision_id: str
    order_id: Optional[str]
    client_order_id: str
    claimed_status: str
    claimed_filled_qty: float = 0
    p_profit: float
    raw: dict


class Audit(BaseModel):
    """What the CLI saw. Never derived from the claim."""

    claim_id: str
    order_id: Optional[str]
    observed: bool
    observed_status: Optional[str] = None
    observed_filled_qty: float = 0
    observed_filled_avg_price: Optional[float] = None
    matches_claim: bool = False
    note: str = ""
