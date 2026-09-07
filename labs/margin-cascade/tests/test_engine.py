from margin_cascade_lab.engine import Position, run_cascade


def test_unlevered_book_survives_moderate_shock_without_forced_sales():
    positions = [
        Position(fund="Atlas", asset="ALPHA", units=100, price=50, debt=0, market_depth=1_000_000),
        Position(fund="Atlas", asset="BETA", units=50, price=80, debt=0, market_depth=1_000_000),
    ]

    result = run_cascade(positions, shocks={"ALPHA": -0.10}, maintenance_margin=0.25, target_margin=0.35)

    assert result.rounds == 1
    assert result.total_liquidated_value == 0
    assert result.final_prices["ALPHA"] == 45
    assert result.fund_summaries["Atlas"].margin_ratio > 0.99


def test_levered_shock_triggers_pro_rata_liquidation_and_price_impact():
    positions = [
        # After the -20% ALPHA shock, assets fall to 13,000 against
        # 11,200 debt: equity/assets = 13.8%, below the 18% maintenance line.
        Position(fund="Beacon", asset="ALPHA", units=100, price=100, debt=11_200, market_depth=20_000),
        Position(fund="Beacon", asset="BETA", units=100, price=50, debt=0, market_depth=10_000),
    ]

    result = run_cascade(
        positions,
        shocks={"ALPHA": -0.20},
        maintenance_margin=0.18,
        target_margin=0.32,
        impact_coefficient=0.35,
        max_rounds=5,
    )

    assert result.rounds >= 2
    assert result.total_liquidated_value > 0
    assert result.final_prices["ALPHA"] < 80
    assert result.final_prices["BETA"] < 50
    assert result.fund_summaries["Beacon"].margin_ratio >= 0.18
    assert any(event.reason == "margin_breach" for event in result.events)


def test_insolvent_fund_retains_creditor_shortfall_after_sales():
    import pytest
    result = run_cascade(
        [Position('F', 'A', 1, 100, debt=80)],
        shocks={'A': -0.5}, impact_coefficient=0, max_rounds=3,
    )
    summary = result.fund_summaries['F']
    assert summary.debt == pytest.approx(80 - result.total_liquidated_value)
    assert summary.equity == pytest.approx(summary.gross_asset_value - summary.debt)
    assert summary.equity == pytest.approx(-30)
    assert summary.status == 'insolvent'
    assert summary.margin_ratio < 0
    assert summary.leverage is None


def test_repeated_lots_match_combined_book_including_stress():
    whole = [Position('F', 'A', 100, 100, debt=8500, market_depth=20000)]
    lots = [Position('F', 'A', 30, 100, debt=8500, market_depth=20000),
            Position('F', 'A', 70, 100, debt=8500, market_depth=20000)]
    kwargs = {'shocks': {'A': -.1}, 'max_rounds': 3}
    assert run_cascade(whole, **kwargs) == run_cascade(lots, **kwargs)
    assert run_cascade(lots, **kwargs) == run_cascade(list(reversed(lots)), **kwargs)


def test_score_normalizes_fund_count_and_stays_bounded_after_near_total_liquidation():
    small = run_cascade([Position('F', 'A', 1, 100, debt=70)])
    large = run_cascade([Position(str(i), 'A', 1, 100, debt=70) for i in range(10)])
    assert small.systemic_risk_score == large.systemic_risk_score == 15
    result = run_cascade([Position('F', 'A', 1, 100, debt=120)], impact_coefficient=0, max_rounds=15)
    assert 0 <= result.systemic_risk_score <= 100
    assert result.risk_components['liquidation_fraction'] <= 1
    assert result.initial_gross_asset_value == 100


def test_zero_asset_debtor_is_insolvent_not_healthy():
    result = run_cascade([Position('F', 'A', 0, 100, debt=10)])
    summary = result.fund_summaries['F']
    assert summary.debt == 10 and summary.equity == -10
    assert summary.margin_ratio is None and summary.leverage is None
    assert summary.status == 'insolvent'
    assert result.risk_components['stressed_fund_fraction'] == 1
