import math

import pytest

from factor_crowding_radar.core import (
    analyze_crowding,
    weighted_correlation,
    CrowdingInputError,
)


def test_weighted_correlation_matches_known_reference_value():
    x = [0.01, 0.02, -0.01, 0.03]
    y = [0.02, 0.01, -0.02, 0.04]
    weights = [0.4, 0.3, 0.2, 0.1]

    result = weighted_correlation(x, y, weights)

    assert result == pytest.approx(0.8342201141712826, rel=1e-12)


def test_analyze_crowding_flags_concentrated_correlated_positions():
    positions = [
        {"name": "AlphaTech", "weight": 0.32, "factor": "AI Momentum", "returns": [0.012, 0.018, -0.015, 0.020, 0.009, -0.011]},
        {"name": "ChipWorks", "weight": 0.28, "factor": "AI Momentum", "returns": [0.011, 0.017, -0.014, 0.019, 0.008, -0.010]},
        {"name": "CloudScale", "weight": 0.18, "factor": "AI Momentum", "returns": [0.010, 0.016, -0.013, 0.018, 0.007, -0.009]},
        {"name": "BondProxy", "weight": 0.12, "factor": "Rates Defensive", "returns": [-0.002, 0.001, 0.003, -0.001, 0.002, 0.001]},
        {"name": "Cash", "weight": 0.10, "factor": "Cash", "returns": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
    ]

    report = analyze_crowding(positions, shock_bps=450)

    assert report.portfolio_weight == pytest.approx(1.0)
    assert report.factor_exposures["AI Momentum"] == pytest.approx(0.78)
    assert report.top_factor == "AI Momentum"
    assert report.crowding_score >= 80
    assert report.risk_level == "High"
    assert report.average_pairwise_correlation > 0.75
    assert report.unwind_loss_pct < -3.0
    assert any("AI Momentum" in item for item in report.alerts)


def test_analyze_crowding_rejects_bad_weights_and_return_lengths():
    bad_positions = [
        {"name": "A", "weight": 0.7, "factor": "Growth", "returns": [0.01, 0.02]},
        {"name": "B", "weight": -0.1, "factor": "Value", "returns": [0.01]},
    ]

    with pytest.raises(CrowdingInputError, match="non-negative"):
        analyze_crowding(bad_positions)


def test_breadth_is_bounded_and_identical_exposure_split_preserves_report():
    def portfolio(n):
        return [{'name': str(i), 'weight': 1 / n, 'factor': 'Same',
                 'returns': [.01, -.01, .02]} for i in range(n)]
    small = analyze_crowding(portfolio(2))
    large = analyze_crowding(portfolio(100))
    assert small.correlation_breadth == large.correlation_breadth == 1
    assert small.unwind_loss_pct == large.unwind_loss_pct
    assert small.crowding_score == large.crowding_score
    assert small.average_pairwise_correlation == large.average_pairwise_correlation == 1


def test_splitting_one_position_preserves_heterogeneous_book_metrics():
    original = [
        {'name': 'A', 'weight': .4, 'factor': 'Growth', 'returns': [.02, -.01, .03]},
        {'name': 'B', 'weight': .3, 'factor': 'Growth', 'returns': [-.01, .02, .01]},
        {'name': 'C', 'weight': .3, 'factor': 'Value', 'returns': [-.02, .01, -.03]},
    ]
    split = [dict(original[0], name='A1', weight=.1), dict(original[0], name='A2', weight=.3)] + original[1:]
    a, b = analyze_crowding(original), analyze_crowding(split)
    assert a.factor_exposures == b.factor_exposures
    assert a.correlation_breadth == b.correlation_breadth
    assert a.average_pairwise_correlation == b.average_pairwise_correlation
    assert a.crowding_score == b.crowding_score
    assert a.unwind_loss_pct == b.unwind_loss_pct


def test_dollar_pair_breadth_has_hand_calculated_reference():
    report = analyze_crowding([
        {'name': 'A', 'weight': .6, 'factor': 'One', 'returns': [.01, -.01]},
        {'name': 'B', 'weight': .4, 'factor': 'Two', 'returns': [-.01, .01]},
    ])
    # Cross-factor returns are negatively correlated; only same-factor draws qualify.
    assert report.correlation_breadth == pytest.approx(.6 ** 2 + .4 ** 2)
