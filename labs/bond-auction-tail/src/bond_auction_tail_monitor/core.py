from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AuctionResult:
    """One Treasury auction observation.

    Yields are expressed as percentage yields (for example 4.315 means 4.315%).
    Investor allocation fields are percentages of accepted bids.
    """

    date: str
    tenor: str
    high_yield: float
    when_issued_yield: float
    bid_to_cover: float
    indirect_pct: float
    direct_pct: float
    dealer_pct: float

    @property
    def tail_bp(self) -> float:
        """Auction tail in basis points: high yield minus when-issued yield."""
        return (self.high_yield - self.when_issued_yield) * 100.0


@dataclass(frozen=True)
class AuctionReport:
    date: str
    tenor: str
    tail_bp: float
    bid_to_cover: float
    indirect_pct: float
    dealer_pct: float
    tail_z: float
    bid_to_cover_z: float
    indirect_z: float
    dealer_z: float
    stress_score: int
    regime: str
    drivers: list[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "date": self.date,
            "tenor": self.tenor,
            "tail_bp": round(self.tail_bp, 2),
            "bid_to_cover": round(self.bid_to_cover, 2),
            "indirect_pct": round(self.indirect_pct, 1),
            "dealer_pct": round(self.dealer_pct, 1),
            "tail_z": round(self.tail_z, 2),
            "bid_to_cover_z": round(self.bid_to_cover_z, 2),
            "indirect_z": round(self.indirect_z, 2),
            "dealer_z": round(self.dealer_z, 2),
            "stress_score": self.stress_score,
            "regime": self.regime,
            "drivers": self.drivers,
        }


def load_csv(path: str | Path) -> list[AuctionResult]:
    rows: list[AuctionResult] = []
    with Path(path).open(newline="") as fh:
        reader = csv.DictReader(fh)
        required = {
            "date",
            "tenor",
            "high_yield",
            "when_issued_yield",
            "bid_to_cover",
            "indirect_pct",
            "direct_pct",
            "dealer_pct",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing required CSV columns: {', '.join(sorted(missing))}")
        for row in reader:
            rows.append(
                AuctionResult(
                    date=row["date"],
                    tenor=row["tenor"],
                    high_yield=float(row["high_yield"]),
                    when_issued_yield=float(row["when_issued_yield"]),
                    bid_to_cover=float(row["bid_to_cover"]),
                    indirect_pct=float(row["indirect_pct"]),
                    direct_pct=float(row["direct_pct"]),
                    dealer_pct=float(row["dealer_pct"]),
                )
            )
    return rows


def analyze_series(rows: list[AuctionResult], lookback: int = 6) -> list[AuctionReport]:
    if lookback < 2:
        raise ValueError("lookback must be at least 2 auctions")
    by_tenor: dict[str, list[AuctionResult]] = {}
    reports: list[AuctionReport] = []
    for row in sorted(rows, key=lambda item: (item.tenor, item.date)):
        history = by_tenor.setdefault(row.tenor, [])
        reports.append(_analyze_one(row, history[-lookback:]))
        history.append(row)
    return sorted(reports, key=lambda item: (item.date, item.tenor))


def _z(value: float, history: list[float]) -> float:
    if len(history) < 2:
        return 0.0
    sigma = statistics.pstdev(history)
    if sigma == 0:
        return 0.0 if value == statistics.mean(history) else (3.0 if value > statistics.mean(history) else -3.0)
    return (value - statistics.mean(history)) / sigma


def _analyze_one(row: AuctionResult, history: list[AuctionResult]) -> AuctionReport:
    tail_z = _z(row.tail_bp, [h.tail_bp for h in history])
    btc_z = _z(row.bid_to_cover, [h.bid_to_cover for h in history])
    indirect_z = _z(row.indirect_pct, [h.indirect_pct for h in history])
    dealer_z = _z(row.dealer_pct, [h.dealer_pct for h in history])

    score = 10
    drivers: list[str] = []
    if row.tail_bp >= 2.0 or tail_z >= 1.5:
        score += 35
        drivers.append("large positive tail")
    elif row.tail_bp >= 0.75:
        score += 18
        drivers.append("modest tail concession")
    elif row.tail_bp <= -0.75:
        score -= 8
        drivers.append("stop-through versus when-issued")

    if btc_z <= -1.25 or row.bid_to_cover < 2.2:
        score += 25
        drivers.append("soft bid-to-cover")
    elif btc_z >= 1.25:
        score -= 8
        drivers.append("firm bid-to-cover")

    if indirect_z <= -1.25 or row.indirect_pct < 58:
        score += 20
        drivers.append("weak indirect demand")
    elif indirect_z >= 1.25:
        score -= 5
        drivers.append("strong indirect demand")

    if dealer_z >= 1.25 or row.dealer_pct > 28:
        score += 15
        drivers.append("elevated dealer takedown")

    score = max(0, min(100, score))
    if score >= 70:
        regime = "strained"
    elif score >= 40:
        regime = "watch"
    else:
        regime = "orderly"
    if not drivers:
        drivers = ["near-normal auction versus tenor history"]

    return AuctionReport(
        date=row.date,
        tenor=row.tenor,
        tail_bp=row.tail_bp,
        bid_to_cover=row.bid_to_cover,
        indirect_pct=row.indirect_pct,
        dealer_pct=row.dealer_pct,
        tail_z=tail_z,
        bid_to_cover_z=btc_z,
        indirect_z=indirect_z,
        dealer_z=dealer_z,
        stress_score=score,
        regime=regime,
        drivers=drivers,
    )
