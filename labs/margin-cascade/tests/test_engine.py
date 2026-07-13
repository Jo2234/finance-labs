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
