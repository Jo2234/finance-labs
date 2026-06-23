from options_skew_sentinel.analysis import analyze_chain


def test_analyze_chain_computes_skew_term_and_tail_flags():
    rows = [
        {"symbol": "SPY", "expiry": "2026-08-21", "option_type": "put", "strike": 390, "mid": 4.45, "spot": 420, "rate": 0.04, "days_to_expiry": 45},
        {"symbol": "SPY", "expiry": "2026-08-21", "option_type": "call", "strike": 450, "mid": 2.95, "spot": 420, "rate": 0.04, "days_to_expiry": 45},
        {"symbol": "SPY", "expiry": "2026-09-18", "option_type": "put", "strike": 385, "mid": 7.25, "spot": 420, "rate": 0.04, "days_to_expiry": 73},
        {"symbol": "SPY", "expiry": "2026-09-18", "option_type": "call", "strike": 460, "mid": 3.15, "spot": 420, "rate": 0.04, "days_to_expiry": 73},
    ]

    report = analyze_chain(rows)

    assert report.symbol == "SPY"
    assert len(report.expiries) == 2
    assert report.expiries[0].risk_reversal < 0
    assert report.expiries[0].put_wing_iv > report.expiries[0].call_wing_iv
    assert report.term_structure_slope > 0
    assert "left-tail hedge demand" in report.headline.lower()
    assert report.alert_level in {"watch", "elevated", "extreme"}
