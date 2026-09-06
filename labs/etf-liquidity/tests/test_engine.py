import pytest

from etf_liquidity_stress_lab.engine import (
    Holding,
    StressScenario,
    analyze_liquidity_stress,
    compute_underlying_liquidity,
)


def test_underlying_liquidity_haircuts_by_liquidity_tier():
    holdings = [
        Holding("MEGA", weight=0.50, adv_usd=1_000_000_000, spread_bps=3, liquidity_tier="liquid"),
        Holding("MICRO", weight=0.50, adv_usd=20_000_000, spread_bps=80, liquidity_tier="thin"),
    ]

    profile = compute_underlying_liquidity(holdings)

    assert profile.effective_daily_liquidity_usd == pytest.approx(2_400_000)
    assert profile.weighted_spread_bps == pytest.approx(41.5)
    assert profile.thin_weight == pytest.approx(0.50)


def test_stress_flags_etf_when_flow_exceeds_ap_and_underlying_capacity():
    holdings = [
        Holding("AAA", weight=0.40, adv_usd=100_000_000, spread_bps=12, liquidity_tier="moderate"),
        Holding("BBB", weight=0.35, adv_usd=40_000_000, spread_bps=45, liquidity_tier="thin"),
        Holding("CCC", weight=0.25, adv_usd=30_000_000, spread_bps=65, liquidity_tier="thin"),
    ]
    scenario = StressScenario(
        fund_aum_usd=1_200_000_000,
        redemption_pct=0.18,
        ap_daily_capacity_usd=90_000_000,
        market_depth_multiplier=0.65,
        tracking_buffer_bps=35,
    )

    report = analyze_liquidity_stress(holdings, scenario)

    assert report.redemption_usd == pytest.approx(216_000_000)
    assert report.liquidity_gap_usd > 120_000_000
    assert report.estimated_discount_bps > 180
    assert report.risk_level == "severe"
    assert "AP capacity overwhelmed" in report.key_warnings
    assert "Underlying basket cannot absorb redemption" in report.key_warnings


def test_invalid_holdings_weights_are_rejected():
    holdings = [
        Holding("AAA", weight=0.70, adv_usd=100_000_000, spread_bps=10, liquidity_tier="liquid"),
        Holding("BBB", weight=0.20, adv_usd=50_000_000, spread_bps=20, liquidity_tier="moderate"),
    ]

    with pytest.raises(ValueError, match="weights must sum to 1.0"):
        compute_underlying_liquidity(holdings)


def test_fixed_weight_redemption_cannot_substitute_liquid_name_for_bottleneck():
    holdings = [Holding('LARGE', .5, 1_000_000_000, 2, 'liquid'),
                Holding('SMALL', .5, 1_000_000, 2, 'liquid')]
    report = analyze_liquidity_stress(holdings, StressScenario(500_000_000, .1, 1_000_000_000))
    assert report.effective_underlying_liquidity_usd == pytest.approx(700_000)
    assert report.liquidation_days == pytest.approx(25_000_000 / 350_000)
    assert report.liquidity_gap_usd == pytest.approx(49_300_000)
    assert report.limiting_constituent == 'SMALL'
    assert report.risk_level == 'severe'
    deeper = analyze_liquidity_stress(holdings, StressScenario(500_000_000, .1, 1_000_000_000, .5))
    assert deeper.liquidation_days == pytest.approx(2 * report.liquidation_days)


def test_ap_capacity_still_binds_when_smaller_than_basket_capacity():
    report = analyze_liquidity_stress([Holding('A', 1, 1_000_000, 2, 'liquid')],
                                     StressScenario(1_000_000, .1, 10_000))
    assert report.liquidation_days == 10
    assert report.liquidity_gap_usd == 90_000


def test_duplicate_ticker_cannot_multiply_market_capacity():
    with pytest.raises(ValueError, match='unique'):
        compute_underlying_liquidity([Holding('A', .5, 100, 2, 'liquid'),
                                      Holding('A', .5, 100, 2, 'liquid')])
