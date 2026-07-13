from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class CovenantSpec:
    """Debt covenant thresholds used by a credit agreement."""

    max_net_leverage: float
    min_interest_coverage: float
    min_liquidity: float


@dataclass(frozen=True)
class PeriodFinancials:
    """Financial statement inputs for one reporting period."""

    period: str
    revenue: float
    adjusted_ebitda: float
    net_debt: float
    cash_interest: float
    liquidity: float


@dataclass(frozen=True)
class CovenantResult:
    period: str
    scenario: str
    metrics: dict[str, float]
    headroom: dict[str, float]
    headroom_pct: dict[str, float]
    breaches: list[str]
    status: str
    inputs: PeriodFinancials

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


def _require_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive; got {value!r}")


def analyze_period(
    period: PeriodFinancials,
    spec: CovenantSpec,
    *,
    scenario: str = "base",
) -> CovenantResult:
    """Compute covenant ratios, absolute headroom, and breach status."""
    _require_positive("adjusted_ebitda", period.adjusted_ebitda)
    _require_positive("cash_interest", period.cash_interest)
    _require_positive("max_net_leverage", spec.max_net_leverage)
    _require_positive("min_interest_coverage", spec.min_interest_coverage)

    net_leverage = period.net_debt / period.adjusted_ebitda
    interest_coverage = period.adjusted_ebitda / period.cash_interest
    liquidity = period.liquidity

    metrics = {
        "net_leverage": net_leverage,
        "interest_coverage": interest_coverage,
        "liquidity": liquidity,
    }
    headroom = {
        "net_leverage": spec.max_net_leverage - net_leverage,
        "interest_coverage": interest_coverage - spec.min_interest_coverage,
        "liquidity": liquidity - spec.min_liquidity,
    }
    headroom_pct = {
        "net_leverage": headroom["net_leverage"] / spec.max_net_leverage,
        "interest_coverage": headroom["interest_coverage"] / spec.min_interest_coverage,
        "liquidity": headroom["liquidity"] / spec.min_liquidity if spec.min_liquidity else 0.0,
    }
    breaches = [name for name, value in headroom.items() if value < 0]
    return CovenantResult(
        period=period.period,
        scenario=scenario,
        metrics=metrics,
        headroom=headroom,
        headroom_pct=headroom_pct,
        breaches=breaches,
        status="breach" if breaches else "pass",
        inputs=period,
    )


def run_scenario(
    period: PeriodFinancials,
    spec: CovenantSpec,
    *,
    name: str,
    ebitda_shock_pct: float = 0.0,
    net_debt_delta: float = 0.0,
    liquidity_delta: float = 0.0,
) -> CovenantResult:
    """Apply a stress scenario and analyze the shocked period."""
    shocked = PeriodFinancials(
        period=period.period,
        revenue=period.revenue,
        adjusted_ebitda=period.adjusted_ebitda * (1.0 + ebitda_shock_pct / 100.0),
        net_debt=period.net_debt + net_debt_delta,
        cash_interest=period.cash_interest,
        liquidity=period.liquidity + liquidity_delta,
    )
    return analyze_period(shocked, spec, scenario=name)


def load_periods_csv(path: str | Path) -> list[PeriodFinancials]:
    rows: list[PeriodFinancials] = []
    with Path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"period", "revenue", "adjusted_ebitda", "net_debt", "cash_interest", "liquidity"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")
        for row in reader:
            rows.append(
                PeriodFinancials(
                    period=row["period"],
                    revenue=float(row["revenue"]),
                    adjusted_ebitda=float(row["adjusted_ebitda"]),
                    net_debt=float(row["net_debt"]),
                    cash_interest=float(row["cash_interest"]),
                    liquidity=float(row["liquidity"]),
                )
            )
    if not rows:
        raise ValueError("CSV contained no periods")
    return rows


def summarize_results(results: Iterable[CovenantResult]) -> dict[str, float | int | str]:
    result_list = list(results)
    base_results = [r for r in result_list if r.scenario == "base"]
    worst = max(result_list, key=lambda r: r.metrics["net_leverage"])
    tightest = min(result_list, key=lambda r: min(r.headroom_pct.values()))
    return {
        "periods": len({r.period for r in base_results}),
        "scenarios": len({r.scenario for r in result_list}),
        "base_breaches": sum(1 for r in base_results if r.status == "breach"),
        "total_breaches": sum(1 for r in result_list if r.status == "breach"),
        "worst_net_leverage": worst.metrics["net_leverage"],
        "worst_net_leverage_period": worst.period,
        "worst_net_leverage_scenario": worst.scenario,
        "tightest_headroom_period": tightest.period,
        "tightest_headroom_scenario": tightest.scenario,
    }
