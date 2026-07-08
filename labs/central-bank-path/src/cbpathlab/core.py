from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Mapping


@dataclass(frozen=True)
class Meeting:
    """A policy meeting and the market-implied average policy rate after it."""

    date: str
    expected_rate: float
    contract: str | None = None
    futures_price: float | None = None


@dataclass(frozen=True)
class PathInputs:
    current_rate: float
    neutral_rate: float
    meetings: list[Meeting]
    macro: Mapping[str, float] = field(default_factory=dict)
    step_bps: int = 25


@dataclass(frozen=True)
class StepProbability:
    meeting_date: str
    expected_change_bps: float
    cut_probability: float
    hike_probability: float
    hold_probability: float
    cumulative_expected_rate: float


@dataclass(frozen=True)
class PathAnalysis:
    current_rate: float
    terminal_expected_rate: float
    total_easing_bps: float
    neutral_gap_bps: float
    regime: str
    steps: list[StepProbability]
    flags: list[str]
    macro: Mapping[str, float]


def futures_price_to_rate(price: float) -> float:
    """Convert a CME Fed Funds futures-style price (100 - rate) to percent rate."""
    if not 0 < price < 100:
        raise ValueError("futures price must be between 0 and 100")
    return 100.0 - price


def _validate_chronological(meetings: list[Meeting]) -> None:
    parsed = [date.fromisoformat(m.date) for m in meetings]
    if parsed != sorted(parsed):
        raise ValueError("policy meetings must be in chronological order")


def _clamp_probability(value: float) -> float:
    return min(1.0, max(0.0, value))


def infer_step_probabilities(
    current_rate: float, meetings: list[Meeting], step_bps: int = 25
) -> list[StepProbability]:
    """Infer per-meeting cut/hold/hike odds from adjacent expected policy rates.

    The method intentionally uses a transparent one-step approximation:
    adjacent expected-rate changes are divided by the configured policy step size.
    Values larger than one step are capped at 100% and surfaced through the bps field.
    """
    if step_bps <= 0:
        raise ValueError("step_bps must be positive")
    _validate_chronological(meetings)

    previous_rate = current_rate
    steps: list[StepProbability] = []
    for meeting in meetings:
        change_bps = round((meeting.expected_rate - previous_rate) * 100, 6)
        cut_probability = _clamp_probability(-change_bps / step_bps)
        hike_probability = _clamp_probability(change_bps / step_bps)
        hold_probability = _clamp_probability(1.0 - cut_probability - hike_probability)
        steps.append(
            StepProbability(
                meeting_date=meeting.date,
                expected_change_bps=change_bps,
                cut_probability=cut_probability,
                hike_probability=hike_probability,
                hold_probability=hold_probability,
                cumulative_expected_rate=meeting.expected_rate,
            )
        )
        previous_rate = meeting.expected_rate
    return steps


def analyze_path(inputs: PathInputs) -> PathAnalysis:
    if not inputs.meetings:
        raise ValueError("at least one policy meeting is required")
    _validate_chronological(inputs.meetings)

    steps = infer_step_probabilities(inputs.current_rate, inputs.meetings, inputs.step_bps)
    terminal_rate = inputs.meetings[-1].expected_rate
    total_easing_bps = round((terminal_rate - inputs.current_rate) * 100, 6)
    neutral_gap_bps = round((terminal_rate - inputs.neutral_rate) * 100, 6)

    macro = inputs.macro
    unemployment = macro.get("unemployment_rate")
    ism_new_orders = macro.get("ism_new_orders")
    core_pce = macro.get("core_pce_yoy")

    flags: list[str] = []
    if total_easing_bps <= -75 and (unemployment or 0) >= 4.5:
        flags.append("market prices aggressive easing while unemployment is already elevated")
    if neutral_gap_bps > 75:
        flags.append("terminal expected rate remains materially above neutral")
    if core_pce is not None and core_pce > 2.8 and total_easing_bps <= -50:
        flags.append("easing path conflicts with still-sticky core inflation")
    if ism_new_orders is not None and ism_new_orders < 48 and total_easing_bps <= -50:
        flags.append("weak new orders make the path look like a growth-shock hedge")

    if total_easing_bps <= -75 and ((unemployment or 0) >= 4.5 or (ism_new_orders or 100) < 48):
        regime = "hard-landing hedge"
    elif total_easing_bps <= -50:
        regime = "dovish normalization"
    elif total_easing_bps >= 25:
        regime = "renewed inflation pressure"
    else:
        regime = "wait-and-see"

    return PathAnalysis(
        current_rate=inputs.current_rate,
        terminal_expected_rate=terminal_rate,
        total_easing_bps=total_easing_bps,
        neutral_gap_bps=neutral_gap_bps,
        regime=regime,
        steps=steps,
        flags=flags,
        macro=macro,
    )
