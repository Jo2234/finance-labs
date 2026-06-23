import csv
from pathlib import Path

import pytest

from microstress.metrics import (
    Bar,
    OrderBookSnapshot,
    amihud_illiquidity,
    classify_stress,
    order_book_imbalance,
    spread_bps,
    stress_score,
    volume_shock,
)


def test_spread_bps_uses_mid_price_reference():
    assert spread_bps(bid=99.95, ask=100.05) == pytest.approx(10.0)


def test_order_book_imbalance_is_signed_depth_pressure():
    snapshot = OrderBookSnapshot(bid_size=1200, ask_size=800)
    assert order_book_imbalance(snapshot) == pytest.approx(0.2)


def test_amihud_illiquidity_scales_absolute_return_by_dollar_volume():
    bars = [
        Bar(timestamp="t1", close=100.0, volume=1_000),
        Bar(timestamp="t2", close=101.0, volume=2_000),
        Bar(timestamp="t3", close=99.0, volume=1_500),
    ]
    value = amihud_illiquidity(bars)
    expected = ((0.01 / 202_000) + (abs(99 / 101 - 1) / 148_500)) / 2
    assert value == pytest.approx(expected)


def test_volume_shock_compares_latest_volume_to_previous_average():
    bars = [
        Bar("t1", close=10, volume=100),
        Bar("t2", close=10, volume=200),
        Bar("t3", close=10, volume=600),
    ]
    assert volume_shock(bars) == pytest.approx(4.0)


def test_stress_score_combines_liquidity_spread_volume_and_imbalance():
    score = stress_score(
        spread_bps=42.0,
        volume_shock=3.2,
        amihud=0.00000009,
        abs_imbalance=0.65,
    )
    assert 0 <= score <= 100
    assert score == pytest.approx(73.25)
    assert classify_stress(score) == "elevated"


def test_invalid_quote_rejected():
    with pytest.raises(ValueError, match="ask must be greater than bid"):
        spread_bps(bid=100, ask=99)
