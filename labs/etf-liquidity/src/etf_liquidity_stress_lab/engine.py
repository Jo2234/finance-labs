from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Literal

LiquidityTier = Literal["liquid", "moderate", "thin"]

_TIER_HAIRCUTS: dict[str, float] = {"liquid": 0.35, "moderate": 0.20, "thin": 0.06}


@dataclass(frozen=True)
class Holding:
    ticker: str
    weight: float
    adv_usd: float
    spread_bps: float
    liquidity_tier: LiquidityTier


@dataclass(frozen=True)
class StressScenario:
    fund_aum_usd: float
    redemption_pct: float
    ap_daily_capacity_usd: float
    market_depth_multiplier: float = 1.0
    tracking_buffer_bps: float = 25.0


@dataclass(frozen=True)
class LiquidityProfile:
    effective_daily_liquidity_usd: float
    weighted_spread_bps: float
    thin_weight: float
    largest_position_weight: float


@dataclass(frozen=True)
class StressReport:
    redemption_usd: float
    effective_underlying_liquidity_usd: float
    ap_daily_capacity_usd: float
    liquidity_gap_usd: float
    estimated_discount_bps: float
    liquidation_days: float
    weighted_spread_bps: float
    thin_weight: float
    risk_level: str
    key_warnings: list[str]
    methodology: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _validate_holdings(holdings: list[Holding]) -> None:
    if not holdings:
        raise ValueError("at least one holding is required")
    total_weight = sum(h.weight for h in holdings)
    if abs(total_weight - 1.0) > 0.005:
        raise ValueError(f"holding weights must sum to 1.0; got {total_weight:.4f}")
    for holding in holdings:
        if holding.weight <= 0:
            raise ValueError(f"{holding.ticker}: weight must be positive")
        if holding.adv_usd <= 0:
            raise ValueError(f"{holding.ticker}: adv_usd must be positive")
        if holding.spread_bps < 0:
            raise ValueError(f"{holding.ticker}: spread_bps cannot be negative")
        if holding.liquidity_tier not in _TIER_HAIRCUTS:
            raise ValueError(f"{holding.ticker}: liquidity_tier must be one of {sorted(_TIER_HAIRCUTS)}")


def compute_underlying_liquidity(holdings: Iterable[Holding]) -> LiquidityProfile:
    basket = list(holdings)
    _validate_holdings(basket)
    effective = sum(h.adv_usd * _TIER_HAIRCUTS[h.liquidity_tier] for h in basket)
    weighted_spread = sum(h.weight * h.spread_bps for h in basket)
    thin_weight = sum(h.weight for h in basket if h.liquidity_tier == "thin")
    largest = max(h.weight for h in basket)
    return LiquidityProfile(
        effective_daily_liquidity_usd=effective,
        weighted_spread_bps=weighted_spread,
        thin_weight=thin_weight,
        largest_position_weight=largest,
    )


def analyze_liquidity_stress(holdings: Iterable[Holding], scenario: StressScenario) -> StressReport:
    if scenario.fund_aum_usd <= 0:
        raise ValueError("fund_aum_usd must be positive")
    if not 0 < scenario.redemption_pct < 1:
        raise ValueError("redemption_pct must be between 0 and 1")
    if scenario.ap_daily_capacity_usd <= 0:
        raise ValueError("ap_daily_capacity_usd must be positive")
    if scenario.market_depth_multiplier <= 0:
        raise ValueError("market_depth_multiplier must be positive")

    profile = compute_underlying_liquidity(holdings)
    redemption = scenario.fund_aum_usd * scenario.redemption_pct
    effective_liquidity = profile.effective_daily_liquidity_usd * scenario.market_depth_multiplier
    practical_capacity = min(effective_liquidity, scenario.ap_daily_capacity_usd)
    gap = max(0.0, redemption - practical_capacity)
    liquidation_days = redemption / max(practical_capacity, 1.0)
    gap_ratio = gap / redemption if redemption else 0.0

    discount = (
        profile.weighted_spread_bps
        + scenario.tracking_buffer_bps
        + gap_ratio * 520
        + profile.thin_weight * 90
        + max(0.0, liquidation_days - 1.0) * 35
    )

    warnings: list[str] = []
    if redemption > scenario.ap_daily_capacity_usd:
        warnings.append("AP capacity overwhelmed")
    if redemption > effective_liquidity:
        warnings.append("Underlying basket cannot absorb redemption")
    if profile.thin_weight >= 0.35:
        warnings.append("Large weight in thinly traded constituents")
    if liquidation_days > 2:
        warnings.append("Multi-day liquidation risk")

    if discount >= 180 or gap_ratio >= 0.45 or liquidation_days >= 2.0:
        risk = "severe"
    elif discount >= 90 or gap_ratio >= 0.20 or profile.thin_weight >= 0.35:
        risk = "elevated"
    else:
        risk = "contained"

    return StressReport(
        redemption_usd=redemption,
        effective_underlying_liquidity_usd=effective_liquidity,
        ap_daily_capacity_usd=scenario.ap_daily_capacity_usd,
        liquidity_gap_usd=gap,
        estimated_discount_bps=discount,
        liquidation_days=liquidation_days,
        weighted_spread_bps=profile.weighted_spread_bps,
        thin_weight=profile.thin_weight,
        risk_level=risk,
        key_warnings=warnings,
        methodology={
            "liquidity_model": "ADV is haircut by liquidity tier (liquid 35%, moderate 20%, thin 6%) and scaled by market-depth stress.",
            "capacity_model": "Daily stress capacity is the lesser of authorized-participant capacity and stressed underlying basket liquidity.",
            "discount_model": "Estimated discount combines weighted spread, tracking buffer, liquidity gap ratio, thin-basket penalty, and liquidation-days penalty.",
        },
    )
