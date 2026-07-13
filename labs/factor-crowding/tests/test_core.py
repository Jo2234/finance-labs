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
