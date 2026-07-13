from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
import math
from typing import Iterable, Mapping, Sequence


class CrowdingInputError(ValueError):
    """Raised when portfolio input cannot support crowding analysis."""


@dataclass(frozen=True)
class Position:
    name: str
    weight: float
    factor: str
    returns: tuple[float, ...]


@dataclass(frozen=True)
class CrowdingReport:
    portfolio_weight: float
    factor_exposures: dict[str, float]
    top_factor: str
    top_factor_weight: float
    concentration_hhi: float
    average_pairwise_correlation: float
    correlation_breadth: float
    crowding_score: int
    risk_level: str
    unwind_loss_pct: float
    alerts: list[str]
    methodology: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def weighted_correlation(x: Sequence[float], y: Sequence[float], weights: Sequence[float] | None = None) -> float:
    """Return weighted Pearson correlation for equal-length vectors.

    Zero-variance vectors are treated as uncorrelated because they add no traded
    return signal to the crowding estimate.
    """
    if len(x) != len(y):
        raise CrowdingInputError("correlation inputs must have the same length")
    if not x:
        raise CrowdingInputError("correlation inputs cannot be empty")
    if weights is None:
        weights = [1.0 / len(x)] * len(x)
    if len(weights) != len(x):
        raise CrowdingInputError("weights must match return vector length")
    total_weight = sum(weights)
    if total_weight <= 0:
        raise CrowdingInputError("weights must sum to a positive value")

    norm = [w / total_weight for w in weights]
    mean_x = sum(v * w for v, w in zip(x, norm))
    mean_y = sum(v * w for v, w in zip(y, norm))
    cov = sum(w * (a - mean_x) * (b - mean_y) for a, b, w in zip(x, y, norm))
    var_x = sum(w * (a - mean_x) ** 2 for a, w in zip(x, norm))
    var_y = sum(w * (b - mean_y) ** 2 for b, w in zip(y, norm))
    if var_x <= 1e-18 or var_y <= 1e-18:
        return 0.0
    return cov / math.sqrt(var_x * var_y)


def analyze_crowding(raw_positions: Iterable[Mapping[str, object]], shock_bps: float = 350) -> CrowdingReport:
    """Analyze factor concentration, co-movement, and simple unwind stress.

    Parameters
    ----------
    raw_positions:
        Iterable of mappings with ``name``, ``weight``, ``factor`` and ``returns``.
    shock_bps:
        Basis-point shock applied to the crowded sleeve. A 450 bps shock means a
        -4.5% move in the top factor sleeve, amplified by correlation breadth.
    """
    positions = _parse_positions(raw_positions)
    portfolio_weight = sum(p.weight for p in positions)
    if not 0.99 <= portfolio_weight <= 1.01:
        raise CrowdingInputError("position weights must sum to approximately 1.0")

    factor_exposures = _factor_exposures(positions)
    top_factor, top_factor_weight = max(factor_exposures.items(), key=lambda item: item[1])
    concentration_hhi = sum(weight**2 for weight in factor_exposures.values())
    top_factor_positions = [position for position in positions if position.factor == top_factor]
    avg_corr = _average_weighted_pairwise_correlation(top_factor_positions)
    correlation_breadth = sum(
        min(a.weight, b.weight)
        for a, b in combinations(positions, 2)
        if a.factor == b.factor or weighted_correlation(a.returns, b.returns) >= 0.65
    )
    crowding_score = _score(top_factor_weight, concentration_hhi, avg_corr, correlation_breadth)
    risk_level = _risk_level(crowding_score)
    shock = shock_bps / 10_000
    amplification = 1 + max(0.0, avg_corr) * 0.75 + correlation_breadth * 0.5
    unwind_loss_pct = -100 * top_factor_weight * shock * amplification
    alerts = _alerts(top_factor, top_factor_weight, concentration_hhi, avg_corr, correlation_breadth, unwind_loss_pct)

    return CrowdingReport(
        portfolio_weight=round(portfolio_weight, 6),
        factor_exposures={factor: round(weight, 6) for factor, weight in sorted(factor_exposures.items())},
        top_factor=top_factor,
        top_factor_weight=round(top_factor_weight, 6),
        concentration_hhi=round(concentration_hhi, 6),
        average_pairwise_correlation=round(avg_corr, 6),
        correlation_breadth=round(correlation_breadth, 6),
        crowding_score=crowding_score,
        risk_level=risk_level,
        unwind_loss_pct=round(unwind_loss_pct, 4),
        alerts=alerts,
        methodology=[
            "Aggregates gross portfolio weight by declared factor bucket.",
            "Computes normalized factor HHI to quantify concentration.",
            "Measures position-return co-movement using exposure-weighted pairwise correlations.",
            "Applies a basis-point unwind shock to the top factor sleeve with correlation amplification.",
        ],
    )


def _parse_positions(raw_positions: Iterable[Mapping[str, object]]) -> list[Position]:
    positions: list[Position] = []
    expected_length: int | None = None
    for index, item in enumerate(raw_positions, start=1):
        try:
            name = str(item["name"])
            factor = str(item["factor"])
            weight = float(item["weight"])
            returns = tuple(float(value) for value in item["returns"])  # type: ignore[index]
        except (KeyError, TypeError, ValueError) as exc:
            raise CrowdingInputError(f"position {index} must include name, weight, factor, and numeric returns") from exc
        if not name or not factor:
            raise CrowdingInputError("position name and factor cannot be empty")
        if weight < 0:
            raise CrowdingInputError("position weights must be non-negative")
        if expected_length is None:
            expected_length = len(returns)
        if len(returns) < 2 or len(returns) != expected_length:
            raise CrowdingInputError("all positions must have at least two returns with the same length")
        positions.append(Position(name=name, weight=weight, factor=factor, returns=returns))
    if len(positions) < 2:
        raise CrowdingInputError("at least two positions are required")
    return positions


def _factor_exposures(positions: Sequence[Position]) -> dict[str, float]:
    exposures: dict[str, float] = {}
    for position in positions:
        exposures[position.factor] = exposures.get(position.factor, 0.0) + position.weight
    return exposures


def _average_weighted_pairwise_correlation(positions: Sequence[Position]) -> float:
    weighted_corrs = []
    total_pair_weight = 0.0
    for a, b in combinations(positions, 2):
        pair_weight = math.sqrt(a.weight * b.weight)
        weighted_corrs.append(weighted_correlation(a.returns, b.returns) * pair_weight)
        total_pair_weight += pair_weight
    if not weighted_corrs or total_pair_weight <= 0:
        return 0.0
    return sum(weighted_corrs) / total_pair_weight


def _score(top_weight: float, hhi: float, avg_corr: float, breadth: float) -> int:
    raw = (top_weight * 45) + (hhi * 35) + (max(0.0, avg_corr) * 35) + (breadth * 25)
    return max(0, min(100, round(raw)))


def _risk_level(score: int) -> str:
    if score >= 75:
        return "High"
    if score >= 50:
        return "Elevated"
    if score >= 30:
        return "Moderate"
    return "Low"


def _alerts(top_factor: str, top_weight: float, hhi: float, avg_corr: float, breadth: float, unwind_loss_pct: float) -> list[str]:
    alerts: list[str] = []
    if top_weight >= 0.45:
        alerts.append(f"{top_factor} holds {top_weight:.1%} of portfolio weight; single-factor exit liquidity may dominate risk.")
    if avg_corr >= 0.65:
        alerts.append(f"Average pairwise correlation is {avg_corr:.2f}; positions may de-risk together.")
    if hhi >= 0.40:
        alerts.append(f"Factor HHI is {hhi:.2f}; exposures are materially concentrated.")
    if breadth >= 0.25:
        alerts.append(f"Correlation breadth is {breadth:.1%}; multiple sleeves share similar return paths.")
    if unwind_loss_pct <= -3.0:
        alerts.append(f"Modeled unwind stress loss is {unwind_loss_pct:.2f}%, large enough to merit desk-level review.")
    return alerts or ["No crowding threshold breached under the configured assumptions."]
