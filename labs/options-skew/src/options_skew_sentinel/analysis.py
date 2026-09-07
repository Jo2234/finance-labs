from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isclose, isfinite
from statistics import mean
from typing import Iterable

from .pricing import implied_volatility


@dataclass(frozen=True)
class ExpirySkew:
    expiry: str
    days_to_expiry: float
    put_wing_iv: float
    call_wing_iv: float
    risk_reversal: float
    skew_ratio: float
    put_strike: float
    call_strike: float


@dataclass(frozen=True)
class SkewReport:
    symbol: str
    spot: float
    expiries: list[ExpirySkew]
    term_structure_slope: float
    average_risk_reversal: float
    alert_level: str
    headline: str
    methodology: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["expiries"] = [asdict(expiry) for expiry in self.expiries]
        return payload


def _float(row: dict, key: str) -> float:
    try:
        value = float(row[key])
    except KeyError as exc:
        raise ValueError(f"missing required column: {key}") from exc
    if not isfinite(value):
        raise ValueError(f"{key} must be finite")
    return value


def _best_wing_pair(rows: list[dict]) -> tuple[dict, dict]:
    puts = [r for r in rows if str(r.get("option_type", "")).lower() == "put"]
    calls = [r for r in rows if str(r.get("option_type", "")).lower() == "call"]
    if not puts or not calls:
        raise ValueError("each expiry needs at least one put and one call")
    spot = _float(rows[0], "spot")
    # Prefer roughly symmetric 5-10% wings, falling back to the farthest available wings.
    put = min(puts, key=lambda r: abs((_float(r, "strike") / spot) - 0.93))
    call = min(calls, key=lambda r: abs((_float(r, "strike") / spot) - 1.07))
    return put, call


def _level(avg_rr: float, slope: float) -> str:
    stress = abs(avg_rr) + max(0.0, slope)
    if stress >= 0.16:
        return "extreme"
    if stress >= 0.10:
        return "elevated"
    if stress >= 0.04:
        return "watch"
    return "normal"


def _headline(symbol: str, avg_rr: float, slope: float, level: str) -> str:
    direction = "left-tail hedge demand" if avg_rr < 0 else "upside chase demand"
    term = "rising across expiries" if slope > 0.005 else "flat across expiries"
    return f"{symbol} options skew is {level}: {direction}, with implied volatility {term}."


def analyze_chain(rows: Iterable[dict]) -> SkewReport:
    """Analyze wing skew from CSV-like option chain rows.

    Expected columns: symbol, expiry, option_type, strike, mid, spot, rate,
    days_to_expiry. The report compares a put-wing IV with a call-wing IV for
    each expiry; risk reversal = call-wing IV - put-wing IV.
    """
    materialized = list(rows)
    if not materialized:
        raise ValueError("option chain is empty")

    symbol = str(materialized[0].get("symbol", "")).strip()
    if not symbol:
        raise ValueError("symbol is required")
    spot = _float(materialized[0], "spot")
    if spot <= 0:
        raise ValueError("spot must be positive")
    by_expiry: dict[str, list[dict]] = {}
    for row in materialized:
        if str(row.get("symbol", "")).strip() != symbol:
            raise ValueError("option chain must contain a single underlying symbol")
        if not isclose(_float(row, "spot"), spot, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError("option chain must use a consistent spot snapshot")
        expiry = str(row.get("expiry", "")).strip()
        if not expiry:
            raise ValueError("expiry is required")
        by_expiry.setdefault(expiry, []).append(row)

    expiries: list[ExpirySkew] = []
    for expiry, expiry_rows in sorted(by_expiry.items(), key=lambda item: _float(item[1][0], "days_to_expiry")):
        for key in ("days_to_expiry", "rate"):
            expected = _float(expiry_rows[0], key)
            if any(not isclose(_float(row, key), expected, rel_tol=1e-9, abs_tol=1e-9) for row in expiry_rows):
                raise ValueError(f"expiry {expiry} must use consistent {key}")
        put, call = _best_wing_pair(expiry_rows)
        put_iv = implied_volatility(
            "put",
            market_price=_float(put, "mid"),
            spot=_float(put, "spot"),
            strike=_float(put, "strike"),
            rate=_float(put, "rate"),
            days_to_expiry=_float(put, "days_to_expiry"),
        )
        call_iv = implied_volatility(
            "call",
            market_price=_float(call, "mid"),
            spot=_float(call, "spot"),
            strike=_float(call, "strike"),
            rate=_float(call, "rate"),
            days_to_expiry=_float(call, "days_to_expiry"),
        )
        expiries.append(
            ExpirySkew(
                expiry=expiry,
                days_to_expiry=_float(put, "days_to_expiry"),
                put_wing_iv=put_iv,
                call_wing_iv=call_iv,
                risk_reversal=call_iv - put_iv,
                skew_ratio=put_iv / call_iv if call_iv else float("inf"),
                put_strike=_float(put, "strike"),
                call_strike=_float(call, "strike"),
            )
        )

    if len(expiries) >= 2:
        term_structure_slope = expiries[-1].put_wing_iv - expiries[0].put_wing_iv
    else:
        term_structure_slope = 0.0
    avg_rr = mean(expiry.risk_reversal for expiry in expiries)
    level = _level(avg_rr, term_structure_slope)
    return SkewReport(
        symbol=symbol,
        spot=spot,
        expiries=expiries,
        term_structure_slope=term_structure_slope,
        average_risk_reversal=avg_rr,
        alert_level=level,
        headline=_headline(symbol, avg_rr, term_structure_slope, level),
        methodology=(
            "Compute Black-Scholes implied volatility for selected put and call wings per expiry; "
            "risk reversal is call-wing IV minus put-wing IV; term slope compares far and near put-wing IV."
        ),
    )
