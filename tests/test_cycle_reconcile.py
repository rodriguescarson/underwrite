"""Exercise the reconciliation and exit logic that runs live, with the two Alpaca channels faked."""
import os
from pathlib import Path

import pytest


from underwrite import audit_cli, cycle, ledger, market, mcp_exec  # noqa: E402
from underwrite.market import LegQuote  # noqa: E402
from underwrite.mcp_exec import parse_order_id  # noqa: E402


def test_parse_order_id_variants():
    assert parse_order_id('{"id": "61e69015-8549-4bfd-b9c3-01e75843f47d", "status": "accepted"}') == "61e69015-8549-4bfd-b9c3-01e75843f47d"
    assert parse_order_id("Order placed successfully.\nOrder ID: 61e69015-8549-4bfd-b9c3-01e75843f47d\nStatus: accepted") == "61e69015-8549-4bfd-b9c3-01e75843f47d"
    assert parse_order_id("no id here") is None


def _claim(**over):
    base = {"claim_id": "clm_a", "kind": "open", "proposal_id": "prp_a", "decision_id": "dec_a", "order_id": "61e69015-8549-4bfd-b9c3-01e75843f47d", "client_order_id": "uwo_1", "claimed_status": "accepted", "p_profit": 0.66, "underlying": "SPY", "structure": "bull_put_spread", "qty": 1, "limit_price": -0.93,
            "legs": [{"symbol": "SPY260925P00600000", "side": "sell", "ratio_qty": 1, "strike": 600, "right": "put", "expiration": "2026-09-25"}, {"symbol": "SPY260925P00595000", "side": "buy", "ratio_qty": 1, "strike": 595, "right": "put", "expiration": "2026-09-25"}]}
    base.update(over)
    return ledger.append("orders", base)


def test_audit_confirms_consistent_claim(monkeypatch):
    c = _claim()
    monkeypatch.setattr(audit_cli, "order", lambda oid: {"id": oid, "status": "filled", "filled_qty": "1", "filled_avg_price": None, "legs": [{"symbol": "SPY260925P00600000", "side": "sell", "filled_qty": "1", "filled_avg_price": "1.50", "status": "filled"}, {"symbol": "SPY260925P00595000", "side": "buy", "filled_qty": "1", "filled_avg_price": "0.55", "status": "filled"}]})
    a = cycle.audit_claim(c)
    assert a["observed"] and a["observed_status"] == "filled" and a["matches_claim"]
    assert cycle.open_structures()[0]["proposal_id"] == "prp_a"


def test_audit_flags_silent_failure(monkeypatch):
    c = _claim(claimed_status="filled")
    monkeypatch.setattr(audit_cli, "order", lambda oid: {"id": oid, "status": "canceled", "filled_qty": "0", "legs": []})
    a = cycle.audit_claim(c)
    assert a["observed"] and not a["matches_claim"] and "claimed filled" in a["note"]
    from underwrite import calibration
    s = calibration.compute()
    assert s.silent_failures == 1 and not s.earned


def test_audit_falls_back_to_client_order_id(monkeypatch):
    c = _claim(order_id=None)
    monkeypatch.setattr(audit_cli, "orders", lambda status="all", limit=200: [{"id": "abc", "client_order_id": "uwo_1", "status": "new", "filled_qty": "0", "legs": []}])
    a = cycle.audit_claim(c)
    assert a["observed"] and a["order_id"] == "abc" and a["matches_claim"]


def test_take_profit_exit_places_reverse_mleg_and_resolves(monkeypatch):
    c = _claim()
    monkeypatch.setattr(audit_cli, "order", lambda oid: {"id": oid, "status": "filled", "filled_qty": "1", "legs": [{"symbol": "SPY260925P00600000", "side": "sell", "filled_qty": "1", "filled_avg_price": "1.50", "status": "filled"}, {"symbol": "SPY260925P00595000", "side": "buy", "filled_qty": "1", "filled_avg_price": "0.55", "status": "filled"}]})
    cycle.audit_claim(c)
    # credit received 0.95; now the spread is worth 0.40 → captured 0.55 ≥ 50% → take profit
    monkeypatch.setattr(market, "quotes_for", lambda syms: {"SPY260925P00600000": LegQuote("SPY260925P00600000", 0.58, 0.62, 5000, -0.1, 0.15), "SPY260925P00595000": LegQuote("SPY260925P00595000", 0.18, 0.22, 4000, -0.06, 0.16)})
    monkeypatch.setattr(market, "dte", lambda exp, today=None: 20)
    placed = {}
    def fake_place(legs, qty, limit, coid):
        placed.update(legs=legs, qty=qty, limit=limit)
        return '{"id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d", "status": "accepted"}'
    monkeypatch.setattr(mcp_exec, "place_mleg", fake_place)
    monkeypatch.setattr(cycle.time, "sleep", lambda s: None)
    # the closing order's audit: filled at 0.60 / 0.20 → paid 0.40 to close
    monkeypatch.setattr(audit_cli, "order", lambda oid: {"id": oid, "status": "filled", "filled_qty": "1", "legs": [{"symbol": "SPY260925P00600000", "side": "buy", "filled_qty": "1", "filled_avg_price": "0.60", "status": "filled"}, {"symbol": "SPY260925P00595000", "side": "sell", "filled_qty": "1", "filled_avg_price": "0.20", "status": "filled"}]})
    actions = cycle.manage_exits()
    assert actions[0]["exit"].startswith("take profit"), actions
    assert placed["legs"][0]["side"] == "buy" and placed["legs"][0]["position_intent"] == "buy_to_close"
    assert placed["limit"] == pytest.approx(0.43, abs=0.01)  # pay up 3 cents over the 0.40 mid
    assert cycle.resolve_outcomes() == 1
    o = ledger.read("outcomes")[0]
    assert o["win"] and o["pnl"] == pytest.approx(55.0)  # (0.95 - 0.40) * 100
    assert cycle.open_structures() == []
