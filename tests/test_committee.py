from underwrite.committee import agree, direction


def test_direction_families():
    assert direction("bull_put_spread") == "bullish" and direction("bear_call_spread") == "bearish" and direction("iron_condor") == "neutral"


def test_agreement_rules():
    a = {"underlying": "SPY", "structure": "bull_put_spread", "p_profit": 0.7}
    assert agree(a, {"underlying": "SPY", "structure": "bull_call_spread", "p_profit": 0.6})[0]
    assert not agree(a, {"underlying": "QQQ", "structure": "bull_put_spread"})[0]
    assert not agree(a, {"underlying": "SPY", "structure": "bear_call_spread"})[0]
    assert not agree(a, {"no_trade": True})[0]
    assert not agree(None, a)[0]
