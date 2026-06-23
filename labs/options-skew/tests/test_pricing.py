import math

import pytest

from options_skew_sentinel.pricing import black_scholes_price, implied_volatility


def test_black_scholes_call_put_prices_match_known_reference_values():
    call = black_scholes_price("call", spot=100, strike=100, rate=0.05, days_to_expiry=30, volatility=0.20)
    put = black_scholes_price("put", spot=100, strike=100, rate=0.05, days_to_expiry=30, volatility=0.20)

    assert call == pytest.approx(2.4934, abs=1e-4)
    assert put == pytest.approx(2.0833, abs=1e-4)


def test_implied_volatility_recovers_vol_from_market_price():
    price = black_scholes_price("put", spot=420, strike=400, rate=0.04, days_to_expiry=45, volatility=0.31)

    recovered = implied_volatility("put", market_price=price, spot=420, strike=400, rate=0.04, days_to_expiry=45)

    assert recovered == pytest.approx(0.31, abs=1e-4)


def test_implied_volatility_rejects_price_below_intrinsic_value():
    with pytest.raises(ValueError, match="below intrinsic"):
        implied_volatility("call", market_price=1.0, spot=105, strike=100, rate=0.0, days_to_expiry=30)
