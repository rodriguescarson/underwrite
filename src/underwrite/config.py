"""Runtime configuration. Every risk number lives here so the write-up can quote it."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
load_dotenv(Path.home() / "Projects" / "hack-sprint" / ".env")  # Carson's shared sprint env, if present

LEDGER_DIR = Path(os.getenv("UNDERWRITE_LEDGER_DIR", ROOT / "ledger"))
LEDGER_DIR.mkdir(exist_ok=True)


@dataclass(frozen=True)
class Risk:
    """The gate. Deterministic, no LLM. Numbers are the ones the one-page write-up quotes."""

    max_loss_per_trade_frac: float = 0.01      # hard cap: 1% of equity at risk per structure
    floor_risk_frac: float = 0.0025            # sizing floor until calibration is earned: 0.25% of equity
    earned_risk_frac: float = 0.01             # sizing once calibration passes
    min_dte: int = 7
    max_dte: int = 45
    max_open_structures: int = 4
    max_structures_per_underlying: int = 1
    max_bid_ask_spread_frac: float = 0.15      # per leg: (ask-bid)/mid must be <= 15% ...
    max_abs_spread: float = 0.10               # ...unless the absolute spread is <= $0.10 (cheap far-OTM wings)
    min_open_interest: int = 100
    min_p_profit: float = 0.55                 # the agent must believe it has an edge to trade
    allowed_underlyings: tuple[str, ...] = ("SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA")
    # calibration gate — position size only scales when ALL hold
    calib_min_resolved: int = 10
    calib_max_ece: float = 0.15
    calib_max_brier: float = 0.25
    calib_min_claim_accuracy: float = 0.99     # reported-vs-verified


RISK = Risk()


def alpaca_env() -> dict[str, str]:
    key = os.getenv("ALPACA_API_KEY", "")
    secret = os.getenv("ALPACA_SECRET_KEY", "")
    if not key or not secret:
        raise RuntimeError("ALPACA_API_KEY / ALPACA_SECRET_KEY missing (fresh paper account, $100k)")
    return {"ALPACA_API_KEY": key, "ALPACA_SECRET_KEY": secret, "ALPACA_PAPER_TRADE": "true"}


MODEL = os.getenv("UNDERWRITE_MODEL", "gemini-3.5-flash")
FALLBACK_MODEL = os.getenv("UNDERWRITE_FALLBACK_MODEL", "gemini-2.5-flash")
