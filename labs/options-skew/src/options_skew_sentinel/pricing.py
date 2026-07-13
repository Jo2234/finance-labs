from __future__ import annotations

import math


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def black_scholes_price(
    option_type: str,
    *,
    spot: float,
    strike: float,
    rate: float,
    days_to_expiry: float,
    volatility: float,
) -> float:
    """Price a European call or put with Black-Scholes.

    Parameters use annualized rate and volatility, and calendar days to expiry.
    """
    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be positive")
    if days_to_expiry <= 0:
        raise ValueError("days_to_expiry must be positive")
    if volatility <= 0:
        raise ValueError("volatility must be positive")

    kind = option_type.lower()
    if kind not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")

    t = days_to_expiry / 365.0
    sqrt_t = math.sqrt(t)
    d1 = (math.log(spot / strike) + (rate + 0.5 * volatility * volatility) * t) / (volatility * sqrt_t)
    d2 = d1 - volatility * sqrt_t
    discounted_strike = strike * math.exp(-rate * t)

    if kind == "call":
        return spot * _normal_cdf(d1) - discounted_strike * _normal_cdf(d2)
    return discounted_strike * _normal_cdf(-d2) - spot * _normal_cdf(-d1)


def intrinsic_value(option_type: str, *, spot: float, strike: float) -> float:
    kind = option_type.lower()
    if kind == "call":
        return max(0.0, spot - strike)
    if kind == "put":
        return max(0.0, strike - spot)
    raise ValueError("option_type must be 'call' or 'put'")


def implied_volatility(
    option_type: str,
    *,
    market_price: float,
    spot: float,
    strike: float,
    rate: float,
    days_to_expiry: float,
    tolerance: float = 1e-7,
    max_iterations: int = 120,
) -> float:
    """Recover Black-Scholes implied volatility with robust bisection."""
    if market_price <= 0:
        raise ValueError("market_price must be positive")
    floor = intrinsic_value(option_type, spot=spot, strike=strike)
    if market_price < floor - 1e-12:
        raise ValueError(f"market price {market_price:.4f} is below intrinsic value {floor:.4f}")

    low = 1e-6
    high = 5.0
    low_price = black_scholes_price(option_type, spot=spot, strike=strike, rate=rate, days_to_expiry=days_to_expiry, volatility=low)
    high_price = black_scholes_price(option_type, spot=spot, strike=strike, rate=rate, days_to_expiry=days_to_expiry, volatility=high)
    if market_price < low_price - 1e-8:
        raise ValueError(f"market price {market_price:.4f} is below no-volatility model price {low_price:.4f}")
    if market_price > high_price + 1e-8:
        raise ValueError("market price implies volatility above 500%")

    for _ in range(max_iterations):
        mid = (low + high) / 2.0
        price = black_scholes_price(option_type, spot=spot, strike=strike, rate=rate, days_to_expiry=days_to_expiry, volatility=mid)
        if abs(price - market_price) <= tolerance:
            return mid
        if price < market_price:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0
