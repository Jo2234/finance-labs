from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Bar:
    timestamp: str
    close: float
    volume: float


@dataclass(frozen=True)
class OrderBookSnapshot:
    bid_size: float
    ask_size: float


def spread_bps(*, bid: float, ask: float) -> float:
    """Return quoted spread in basis points relative to mid-price."""
    if bid <= 0 or ask <= 0:
        raise ValueError("bid and ask must be positive")
    if ask <= bid:
        raise ValueError("ask must be greater than bid")
    mid = (bid + ask) / 2
    return ((ask - bid) / mid) * 10_000


def order_book_imbalance(snapshot: OrderBookSnapshot) -> float:
    """Signed depth pressure: positive means bid-side depth dominates."""
    total = snapshot.bid_size + snapshot.ask_size
    if snapshot.bid_size < 0 or snapshot.ask_size < 0:
        raise ValueError("depth sizes cannot be negative")
    if total == 0:
        raise ValueError("at least one side of the book must have depth")
    return (snapshot.bid_size - snapshot.ask_size) / total


def _returns(bars: list[Bar]) -> list[tuple[float, float]]:
    if len(bars) < 2:
        raise ValueError("at least two bars are required")
    out: list[tuple[float, float]] = []
    previous = bars[0]
    if previous.close <= 0:
        raise ValueError("close prices must be positive")
    for bar in bars[1:]:
        if bar.close <= 0:
            raise ValueError("close prices must be positive")
        if bar.volume <= 0:
            raise ValueError("volumes must be positive")
        ret = (bar.close / previous.close) - 1
        dollar_volume = bar.close * bar.volume
        out.append((ret, dollar_volume))
        previous = bar
    return out


def amihud_illiquidity(bars: list[Bar]) -> float:
    """Average |return| per dollar traded; higher means thinner liquidity."""
    scaled_returns = [abs(ret) / dollar_volume for ret, dollar_volume in _returns(bars)]
    return sum(scaled_returns) / len(scaled_returns)


def volume_shock(bars: list[Bar]) -> float:
    """Latest volume divided by the previous-bars average volume."""
    if len(bars) < 2:
        raise ValueError("at least two bars are required")
    previous_volumes = [bar.volume for bar in bars[:-1]]
    if any(volume <= 0 for volume in previous_volumes) or bars[-1].volume <= 0:
        raise ValueError("volumes must be positive")
    baseline = sum(previous_volumes) / len(previous_volumes)
    return bars[-1].volume / baseline


def stress_score(*, spread_bps: float, volume_shock: float, amihud: float, abs_imbalance: float) -> float:
    """Blend microstructure indicators into a bounded 0-100 stress score.

    Components intentionally saturate so a single pathological feature cannot
    dominate the whole score:
    - spread: 30 points, full stress by 60 bps
    - volume shock: 25 points, full stress at 4x recent volume
    - Amihud: 25 points, full stress at 1e-7 |return|/dollar
    - depth imbalance: 15 points, full stress at absolute imbalance of 1
    - baseline friction: 5 points for non-zero trading frictions
    """
    if min(spread_bps, volume_shock, amihud, abs_imbalance) < 0:
        raise ValueError("stress inputs cannot be negative")
    if abs_imbalance > 1:
        raise ValueError("absolute imbalance must be between 0 and 1")

    score = 0.0
    score += min(spread_bps / 60.0, 1.0) * 30.0
    score += min(volume_shock / 4.0, 1.0) * 25.0
    score += min(amihud / 0.0000001, 1.0) * 25.0
    score += abs_imbalance * 15.0
    return round(min(score, 100.0), 2)


def classify_stress(score: float) -> str:
    if score < 30:
        return "calm"
    if score < 55:
        return "watch"
    if score < 80:
        return "elevated"
    return "severe"
