import math

import pytest

from cbpathlab.core import (
    Meeting,
    PathInputs,
    analyze_path,
    futures_price_to_rate,
    infer_step_probabilities,
)


def test_futures_price_to_rate_converts_cme_style_price_to_implied_rate():
    assert futures_price_to_rate(94.625) == pytest.approx(5.375)


def test_infer_step_probabilities_recovers_incremental_cut_odds_from_expected_rates():
    meetings = [
        Meeting(date="2026-03-18", expected_rate=5.10),
        Meeting(date="2026-05-06", expected_rate=4.86),
        Meeting(date="2026-06-17", expected_rate=4.59),
    ]

    steps = infer_step_probabilities(current_rate=5.35, meetings=meetings, step_bps=25)

    assert [s.meeting_date for s in steps] == ["2026-03-18", "2026-05-06", "2026-06-17"]
    assert [s.expected_change_bps for s in steps] == pytest.approx([-25, -24, -27])
    assert [s.cut_probability for s in steps] == pytest.approx([1.0, 0.96, 1.0])
    assert [s.hike_probability for s in steps] == pytest.approx([0.0, 0.0, 0.0])


def test_analyze_path_flags_policy_story_inconsistency_and_terminal_easing():
    result = analyze_path(
        PathInputs(
            current_rate=5.35,
            neutral_rate=3.25,
            meetings=[
                Meeting(date="2026-03-18", expected_rate=5.10, contract="ZQH6", futures_price=94.90),
                Meeting(date="2026-05-06", expected_rate=4.86, contract="ZQK6", futures_price=95.14),
                Meeting(date="2026-06-17", expected_rate=4.59, contract="ZQM6", futures_price=95.41),
                Meeting(date="2026-07-29", expected_rate=4.48, contract="ZQN6", futures_price=95.52),
            ],
            macro={"core_pce_yoy": 3.1, "unemployment_rate": 4.8, "ism_new_orders": 46.0},
        )
    )

    assert result.terminal_expected_rate == pytest.approx(4.48)
    assert result.total_easing_bps == pytest.approx(-87)
    assert result.neutral_gap_bps == pytest.approx(123)
    assert result.regime == "hard-landing hedge"
    assert any("market prices aggressive easing" in flag for flag in result.flags)
    assert any("above neutral" in flag for flag in result.flags)


def test_analyze_path_rejects_unsorted_meeting_dates():
    with pytest.raises(ValueError, match="chronological"):
        analyze_path(
            PathInputs(
                current_rate=5.0,
                neutral_rate=3.0,
                meetings=[
                    Meeting(date="2026-06-17", expected_rate=4.75),
                    Meeting(date="2026-05-06", expected_rate=4.50),
                ],
                macro={},
            )
        )
