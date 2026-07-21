from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Iterable

from .engine import CascadeResult, Position, run_cascade


def parse_book(path: str | Path) -> list[Position]:
    with Path(path).open(newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"fund", "asset", "units", "price", "debt", "market_depth"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"book is missing columns: {', '.join(sorted(missing))}")
        return [
            Position(
                fund=row["fund"].strip(),
                asset=row["asset"].strip(),
                units=float(row["units"]),
                price=float(row["price"]),
                debt=float(row.get("debt") or 0),
                market_depth=float(row.get("market_depth") or 1_000_000),
            )
            for row in reader
        ]


def parse_shocks(items: Iterable[str]) -> dict[str, float]:
    shocks: dict[str, float] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"shock must look like ASSET=-0.15, got {item!r}")
        asset, value = item.split("=", 1)
        shocks[asset.strip()] = float(value)
    return shocks


def result_to_dict(result: CascadeResult) -> dict:
    return {
        "scenario": result.scenario,
        "rounds": result.rounds,
        "initial_prices": result.initial_prices,
        "final_prices": result.final_prices,
        "total_liquidated_value": result.total_liquidated_value,
        "systemic_risk_score": result.systemic_risk_score,
        "risk_components": result.risk_components,
        "initial_gross_asset_value": result.initial_gross_asset_value,
        "most_stressed_fund": result.most_stressed_fund,
        "fund_summaries": {k: _clean(v) for k, v in result.fund_summaries.items()},
        "events": [_clean(e) for e in result.events],
    }


def render_markdown(result: CascadeResult) -> str:
    data = result_to_dict(result)
    lines = [
        "# Margin Cascade Report",
        "",
        f"- Rounds simulated: **{data['rounds']}**",
        f"- Total forced liquidation: **${data['total_liquidated_value']:,.0f}**",
        f"- Systemic risk score: **{data['systemic_risk_score']}/100**",
        f"- Most stressed fund: **{data['most_stressed_fund']}**",
        "",
        "## Final fund health",
        "",
        "| Fund | Assets | Debt | Equity | Margin | Leverage | Status |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for summary in data["fund_summaries"].values():
        margin = f"{summary['margin_ratio']:.1%}" if summary['margin_ratio'] is not None else "N/A"
        leverage = f"{summary['leverage']:.2f}x" if summary['leverage'] is not None else "N/A"
        lines.append(
            f"| {summary['fund']} | ${summary['gross_asset_value']:,.0f} | ${summary['debt']:,.0f} | "
            f"${summary['equity']:,.0f} | {margin} | {leverage} | {summary['status']} |"
        )
    lines.extend(["", "## Final prices", "", "| Asset | Initial | Final | Move |", "|---|---:|---:|---:|"])
    for asset, initial in data["initial_prices"].items():
        final = data["final_prices"][asset]
        move = (final / initial - 1) if initial else 0
        lines.append(f"| {asset} | {initial:.2f} | {final:.2f} | {move:.1%} |")
    if data["events"]:
        lines.extend(["", "## Liquidation tape", "", "| Round | Fund | Asset | Sale value | Impact |", "|---:|---|---|---:|---:|"])
        for event in data["events"][:25]:
            lines.append(
                f"| {event['round']} | {event['fund']} | {event['asset']} | "
                f"${event['sale_value']:,.0f} | {event['price_impact']:.2%} |"
            )
    return "\n".join(lines) + "\n"


def _clean(obj):
    if is_dataclass(obj):
        return asdict(obj)
    return obj


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulate margin-call cascades from an offline CSV book")
    parser.add_argument("--book", required=True, help="CSV with fund,asset,units,price,debt,market_depth")
    parser.add_argument("--shock", action="append", default=[], help="Asset shock, e.g. ALPHA=-0.20. Repeatable.")
    parser.add_argument("--maintenance-margin", type=float, default=0.18)
    parser.add_argument("--target-margin", type=float, default=0.32)
    parser.add_argument("--impact-coefficient", type=float, default=0.35)
    parser.add_argument("--max-rounds", type=int, default=8)
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--output", help="Write report to a file instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    positions = parse_book(args.book)
    result = run_cascade(
        positions,
        shocks=parse_shocks(args.shock),
        maintenance_margin=args.maintenance_margin,
        target_margin=args.target_margin,
        impact_coefficient=args.impact_coefficient,
        max_rounds=args.max_rounds,
    )
    rendered = (
        json.dumps(result_to_dict(result), indent=2, sort_keys=True, allow_nan=False)
        if args.format == "json"
        else render_markdown(result)
    )
    if args.output:
        Path(args.output).write_text(rendered)
        print(f"wrote {args.format} report to {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
