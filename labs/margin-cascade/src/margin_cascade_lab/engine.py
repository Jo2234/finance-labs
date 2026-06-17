from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Mapping


@dataclass(frozen=True)
class Position:
    """A fund's long position in one asset.

    Debt is fund-level debt. If repeated across rows for a fund, the simulator
    uses the largest value to avoid double-counting sample-book convenience rows.
    """

    fund: str
    asset: str
    units: float
    price: float
    debt: float = 0.0
    market_depth: float = 1_000_000.0

    def __post_init__(self) -> None:
        for name in ("units", "price", "debt", "market_depth"):
            value = getattr(self, name)
            if not isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.units < 0:
            raise ValueError("units must be non-negative")
        if self.price <= 0:
            raise ValueError("price must be positive")
        if self.debt < 0:
            raise ValueError("debt must be non-negative")
        if self.market_depth <= 0:
            raise ValueError("market_depth must be positive")


@dataclass(frozen=True)
class FundSummary:
    fund: str
    gross_asset_value: float
    debt: float
    equity: float
    margin_ratio: float
    leverage: float


@dataclass(frozen=True)
class LiquidationEvent:
    round: int
    fund: str
    asset: str
    units_sold: float
    sale_value: float
    price_impact: float
    reason: str = "margin_breach"


@dataclass(frozen=True)
class CascadeResult:
    rounds: int
    initial_prices: dict[str, float]
    final_prices: dict[str, float]
    fund_summaries: dict[str, FundSummary]
    events: list[LiquidationEvent] = field(default_factory=list)
    scenario: dict = field(default_factory=dict)

    @property
    def total_liquidated_value(self) -> float:
        return round(sum(event.sale_value for event in self.events), 6)

    @property
    def systemic_risk_score(self) -> float:
        if not self.initial_prices:
            return 0.0
        avg_drawdown = sum(
            max(0.0, (self.initial_prices[a] - self.final_prices[a]) / self.initial_prices[a])
            for a in self.initial_prices
        ) / len(self.initial_prices)
        stressed_funds = sum(1 for s in self.fund_summaries.values() if s.margin_ratio < 0.35)
        liquidation_load = self.total_liquidated_value / max(
            1.0, sum(s.gross_asset_value for s in self.fund_summaries.values())
        )
        return round(100 * (0.55 * avg_drawdown + 0.30 * liquidation_load + 0.15 * stressed_funds), 2)

    @property
    def most_stressed_fund(self) -> str | None:
        if not self.fund_summaries:
            return None
        return min(self.fund_summaries.values(), key=lambda s: s.margin_ratio).fund


def run_cascade(
    positions: list[Position],
    shocks: Mapping[str, float] | None = None,
    maintenance_margin: float = 0.20,
    target_margin: float = 0.35,
    impact_coefficient: float = 0.25,
    max_rounds: int = 8,
) -> CascadeResult:
    """Simulate margin breaches, forced sales, and market-impact feedback.

    The model is intentionally transparent rather than predictive: funds below
    maintenance margin sell a pro-rata slice of risky assets large enough to move
    toward target margin. Sales reduce the fund's debt by cash raised; aggregate
    sale value pushes down each asset price according to market depth.
    """

    if not positions:
        raise ValueError("positions must not be empty")
    if not (0 <= maintenance_margin < target_margin < 1):
        raise ValueError("require 0 <= maintenance_margin < target_margin < 1")
    if impact_coefficient < 0:
        raise ValueError("impact_coefficient must be non-negative")
    if max_rounds < 1:
        raise ValueError("max_rounds must be at least 1")

    shocks = dict(shocks or {})
    prices = _initial_prices(positions)
    initial_prices = dict(prices)
    depths = _asset_depths(positions)
    debt = _fund_debt(positions)
    units = {(p.fund, p.asset): float(p.units) for p in positions}

    for asset, shock in shocks.items():
        if asset not in prices:
            raise ValueError(f"shock references unknown asset: {asset}")
        if shock <= -1:
            raise ValueError("shock cannot be less than or equal to -100%")
        prices[asset] = round(prices[asset] * (1 + shock), 10)

    events: list[LiquidationEvent] = []
    rounds_completed = 1

    for round_number in range(1, max_rounds + 1):
        summaries = _summaries(units, prices, debt)
        breached = [s for s in summaries.values() if s.margin_ratio < maintenance_margin and s.gross_asset_value > 0]
        if not breached:
            rounds_completed = round_number
            break

        sale_value_by_asset = {asset: 0.0 for asset in prices}
        any_sale = False
        for summary in breached:
            # To reach target after using sale proceeds to repay debt:
            # (A - D) / A >= target, sell x, repay debt with x:
            # equity unchanged while x <= debt; new assets A-x, debt D-x.
            desired_assets = summary.equity / target_margin if summary.equity > 0 else 0.0
            sale_needed = max(0.0, summary.gross_asset_value - desired_assets)
            sale_needed = min(sale_needed, summary.gross_asset_value * 0.60)  # liquidity brake
            if sale_needed <= 1e-9:
                continue
            fund_positions = [
                ((fund, asset), qty * prices[asset])
                for (fund, asset), qty in units.items()
                if fund == summary.fund and qty > 0
            ]
            gross = sum(value for _, value in fund_positions)
            if gross <= 0:
                continue
            any_sale = True
            for key, value in fund_positions:
                fund, asset = key
                asset_sale_value = min(value, sale_needed * value / gross)
                units_sold = asset_sale_value / prices[asset]
                units[key] = max(0.0, units[key] - units_sold)
                sale_value_by_asset[asset] += asset_sale_value
                debt[fund] = max(0.0, debt[fund] - asset_sale_value)
                impact = impact_coefficient * asset_sale_value / depths[asset]
                events.append(
                    LiquidationEvent(
                        round=round_number,
                        fund=fund,
                        asset=asset,
                        units_sold=round(units_sold, 6),
                        sale_value=round(asset_sale_value, 6),
                        price_impact=round(impact, 6),
                    )
                )

        if not any_sale:
            rounds_completed = round_number
            break
        for asset, sold_value in sale_value_by_asset.items():
            impact = min(0.85, impact_coefficient * sold_value / depths[asset])
            prices[asset] = round(max(0.01, prices[asset] * (1 - impact)), 10)
        rounds_completed = round_number + 1

    return CascadeResult(
        rounds=rounds_completed,
        initial_prices={k: round(v, 6) for k, v in initial_prices.items()},
        final_prices={k: round(v, 6) for k, v in prices.items()},
        fund_summaries=_summaries(units, prices, debt),
        events=events,
        scenario={
            "shocks": shocks,
            "maintenance_margin": maintenance_margin,
            "target_margin": target_margin,
            "impact_coefficient": impact_coefficient,
            "max_rounds": max_rounds,
        },
    )


def _initial_prices(positions: list[Position]) -> dict[str, float]:
    prices: dict[str, float] = {}
    for p in positions:
        if p.asset in prices and abs(prices[p.asset] - p.price) > 1e-9:
            raise ValueError(f"conflicting prices for asset {p.asset}")
        prices[p.asset] = float(p.price)
    return prices


def _asset_depths(positions: list[Position]) -> dict[str, float]:
    depths: dict[str, float] = {}
    for p in positions:
        depths[p.asset] = min(depths.get(p.asset, p.market_depth), p.market_depth)
    return depths


def _fund_debt(positions: list[Position]) -> dict[str, float]:
    debt: dict[str, float] = {}
    for p in positions:
        debt[p.fund] = max(debt.get(p.fund, 0.0), float(p.debt))
    return debt


def _summaries(
    units: Mapping[tuple[str, str], float], prices: Mapping[str, float], debt: Mapping[str, float]
) -> dict[str, FundSummary]:
    funds = sorted({fund for fund, _ in units} | set(debt))
    summaries: dict[str, FundSummary] = {}
    for fund in funds:
        assets = sum(qty * prices[asset] for (f, asset), qty in units.items() if f == fund)
        d = min(debt.get(fund, 0.0), assets)
        equity = assets - d
        margin = equity / assets if assets > 0 else 1.0
        leverage = assets / equity if equity > 0 else float("inf")
        summaries[fund] = FundSummary(
            fund=fund,
            gross_asset_value=round(assets, 6),
            debt=round(d, 6),
            equity=round(equity, 6),
            margin_ratio=round(margin, 6),
            leverage=round(leverage, 6) if leverage != float("inf") else leverage,
        )
    return summaries
