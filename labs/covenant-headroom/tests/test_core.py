import math

from covenant_headroom_lab.core import CovenantSpec, PeriodFinancials, analyze_period, run_scenario


def test_analyze_period_computes_covenant_headroom_and_status():
    spec = CovenantSpec(max_net_leverage=4.0, min_interest_coverage=2.0, min_liquidity=25.0)
    period = PeriodFinancials(
        period="2026-Q1",
        revenue=120.0,
        adjusted_ebitda=30.0,
        net_debt=105.0,
        cash_interest=10.0,
        liquidity=40.0,
    )

    result = analyze_period(period, spec)

    assert math.isclose(result.metrics["net_leverage"], 3.5)
    assert math.isclose(result.metrics["interest_coverage"], 3.0)
    assert math.isclose(result.headroom["net_leverage"], 0.5)
    assert math.isclose(result.headroom["interest_coverage"], 1.0)
    assert result.status == "pass"
    assert result.breaches == []


def test_analyze_period_flags_breach_when_ratio_exceeds_limit():
    spec = CovenantSpec(max_net_leverage=4.0, min_interest_coverage=2.0, min_liquidity=25.0)
    period = PeriodFinancials(
        period="2026-Q2",
        revenue=100.0,
        adjusted_ebitda=20.0,
        net_debt=100.0,
        cash_interest=12.0,
        liquidity=18.0,
    )

    result = analyze_period(period, spec)

    assert result.status == "breach"
    assert set(result.breaches) == {"net_leverage", "interest_coverage", "liquidity"}
    assert math.isclose(result.headroom["net_leverage"], -1.0)
    assert math.isclose(result.headroom["interest_coverage"], -0.33333333333333326)
    assert math.isclose(result.headroom["liquidity"], -7.0)


def test_run_scenario_applies_recession_shock_without_mutating_original_period():
    spec = CovenantSpec(max_net_leverage=4.0, min_interest_coverage=2.0, min_liquidity=25.0)
    period = PeriodFinancials(
        period="2026-Q3",
        revenue=100.0,
        adjusted_ebitda=25.0,
        net_debt=80.0,
        cash_interest=8.0,
        liquidity=35.0,
    )

    result = run_scenario(
        period,
        spec,
        name="hard landing",
        ebitda_shock_pct=-20.0,
        net_debt_delta=15.0,
        liquidity_delta=-8.0,
    )

    assert result.scenario == "hard landing"
    assert math.isclose(result.metrics["net_leverage"], 4.75)
    assert result.status == "breach"
    assert period.adjusted_ebitda == 25.0
    assert period.net_debt == 80.0
