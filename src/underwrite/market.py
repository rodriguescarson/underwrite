"""Read-side market access for the GATE, through alpaca-py directly.

The strategist reads the market through the MCP server; the gate re-reads the exact
legs it is about to trade through a different client and does its own arithmetic.
The gate never uses a number the LLM typed."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import OptionSnapshotRequest
from alpaca.trading.client import TradingClient

from .config import alpaca_env


def _creds():
    e = alpaca_env()
    return e["ALPACA_API_KEY"], e["ALPACA_SECRET_KEY"]


def trading() -> TradingClient:
    k, s = _creds()
    return TradingClient(k, s, paper=True)


def option_data() -> OptionHistoricalDataClient:
    k, s = _creds()
    return OptionHistoricalDataClient(k, s)


@dataclass
class LegQuote:
    symbol: str
    bid: float
    ask: float
    open_interest: Optional[int]
    delta: Optional[float]
    iv: Optional[float]

    @property
    def mid(self) -> float:
        return round((self.bid + self.ask) / 2, 4)

    @property
    def spread_frac(self) -> float:
        return (self.ask - self.bid) / self.mid if self.mid > 0 else 1.0


def quotes_for(symbols: list[str]) -> dict[str, LegQuote]:
    snaps = option_data().get_option_snapshot(OptionSnapshotRequest(symbol_or_symbols=symbols))
    tc = trading()
    out: dict[str, LegQuote] = {}
    for sym in symbols:
        snap = snaps.get(sym)
        if snap is None or snap.latest_quote is None:
            continue
        oi = None
        try:
            c = tc.get_option_contract(sym)
            oi = int(c.open_interest) if getattr(c, "open_interest", None) is not None else None
        except Exception:
            pass
        g = getattr(snap, "greeks", None)
        out[sym] = LegQuote(sym, float(snap.latest_quote.bid_price), float(snap.latest_quote.ask_price), oi, float(g.delta) if g and g.delta is not None else None, float(snap.implied_volatility) if getattr(snap, "implied_volatility", None) is not None else None)
    return out


def market_open() -> tuple[bool, str]:
    c = trading().get_clock()
    return bool(c.is_open), f"open={c.is_open} next_open={c.next_open} next_close={c.next_close}"


def account_equity() -> tuple[float, dict]:
    a = trading().get_account()
    return float(a.equity), {"equity": float(a.equity), "cash": float(a.cash), "buying_power": float(a.buying_power), "options_buying_power": float(getattr(a, "options_buying_power", 0) or 0), "options_approved_level": getattr(a, "options_approved_level", None), "account_number": a.account_number, "created_at": str(getattr(a, "created_at", ""))}


def dte(expiration: str, today: Optional[date] = None) -> int:
    d = datetime.strptime(expiration, "%Y-%m-%d").date()
    return (d - (today or date.today())).days
