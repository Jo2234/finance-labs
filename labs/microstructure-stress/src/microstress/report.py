from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .metrics import (
    Bar,
    OrderBookSnapshot,
    amihud_illiquidity,
    classify_stress,
    order_book_imbalance,
    spread_bps,
    stress_score,
    volume_shock,
)

_REQUIRED_COLUMNS = {"timestamp", "close", "volume", "bid", "ask", "bid_size", "ask_size"}


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        missing = _REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")
        rows = list(reader)
    if len(rows) < 2:
        raise ValueError("at least two CSV rows are required")
    return rows


def _recommendations(label: str, summary: dict[str, Any]) -> list[str]:
    actions = []
    if summary["latest_spread_bps"] > 25:
        actions.append("Route orders with tighter participation caps; quoted spread is wide versus normal liquid conditions.")
    if summary["volume_shock"] > 2:
        actions.append("Check news and auction calendars; latest volume is materially above the prior tape average.")
    if abs(summary["order_book_imbalance"]) > 0.35:
        side = "bid" if summary["order_book_imbalance"] > 0 else "ask"
        actions.append(f"Monitor {side}-side depth concentration; book pressure is meaningfully one-sided.")
    if label in {"elevated", "severe"}:
        actions.append("Require human review before slicing block orders or widening market-making inventory limits.")
    if not actions:
        actions.append("No immediate liquidity intervention; continue normal monitoring.")
    return actions


def analyze_csv(path: str | Path) -> dict[str, Any]:
    csv_path = Path(path)
    rows = _read_rows(csv_path)
    bars = [Bar(row["timestamp"], float(row["close"]), float(row["volume"])) for row in rows]
    latest = rows[-1]
    latest_spread = spread_bps(bid=float(latest["bid"]), ask=float(latest["ask"]))
    imbalance = order_book_imbalance(
        OrderBookSnapshot(bid_size=float(latest["bid_size"]), ask_size=float(latest["ask_size"]))
    )
    volume_ratio = volume_shock(bars)
    amihud = amihud_illiquidity(bars)
    score = stress_score(
        spread_bps=latest_spread,
        volume_shock=volume_ratio,
        amihud=amihud,
        abs_imbalance=abs(imbalance),
    )
    label = classify_stress(score)
    summary: dict[str, Any] = {
        "source": str(csv_path),
        "observations": len(rows),
        "latest_timestamp": latest["timestamp"],
        "latest_close": float(latest["close"]),
        "latest_spread_bps": latest_spread,
        "order_book_imbalance": imbalance,
        "volume_shock": volume_ratio,
        "amihud_illiquidity": amihud,
        "stress_score": score,
        "stress_label": label,
    }
    summary["recommendations"] = _recommendations(label, summary)
    return summary


def render_markdown(summary: dict[str, Any], *, title: str = "Microstructure Stress Report") -> str:
    lines = [
        f"# {title}",
        "",
        f"Source: `{summary['source']}`",
        f"Latest timestamp: **{summary['latest_timestamp']}**",
        "",
        "## Stress snapshot",
        "",
        f"- Stress score: **{summary['stress_score']:.2f}/100** (`{summary['stress_label']}`)",
        f"- Latest close: **{summary['latest_close']:.4f}**",
        f"- Quoted spread: **{summary['latest_spread_bps']:.2f} bps**",
        f"- Volume shock: **{summary['volume_shock']:.2f}x** prior average",
        f"- Order-book imbalance: **{summary['order_book_imbalance']:.2f}** (-1 ask-heavy, +1 bid-heavy)",
        f"- Amihud illiquidity: **{summary['amihud_illiquidity']:.3e}**",
        "",
        "## Desk actions",
        "",
    ]
    lines.extend(f"- {action}" for action in summary["recommendations"])
    lines.extend(
        [
            "",
            "## Methodology",
            "",
            "The score blends four bounded microstructure signals: quoted spread in basis points, latest-volume shock, Amihud |return|/dollar-volume illiquidity, and absolute top-of-book depth imbalance. The blend is deliberately explainable and saturating, making it useful for risk triage rather than black-box prediction.",
        ]
    )
    return "\n".join(lines) + "\n"
