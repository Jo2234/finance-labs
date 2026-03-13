from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .engine import Holding, StressScenario, analyze_liquidity_stress


def load_holdings_csv(path: str | Path) -> list[Holding]:
    holdings: list[Holding] = []
    with Path(path).open(newline="") as f:
        reader = csv.DictReader(f)
        required = {"ticker", "weight", "adv_usd", "spread_bps", "liquidity_tier"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")
        for row in reader:
            holdings.append(
                Holding(
                    ticker=row["ticker"],
                    weight=float(row["weight"]),
                    adv_usd=float(row["adv_usd"]),
                    spread_bps=float(row["spread_bps"]),
                    liquidity_tier=row["liquidity_tier"].strip().lower(),  # type: ignore[arg-type]
                )
            )
    return holdings


def _format_money(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    return f"${value / 1_000_000:.1f}M"


def render_markdown(report) -> str:
    warnings = "\n".join(f"- {warning}" for warning in report.key_warnings) or "- No major warnings"
    return f"""# ETF Liquidity Stress Report

**Risk level:** {report.risk_level.upper()}

| Metric | Value |
|---|---:|
| Redemption shock | {_format_money(report.redemption_usd)} |
| Stressed underlying liquidity | {_format_money(report.effective_underlying_liquidity_usd)} |
| AP daily capacity | {_format_money(report.ap_daily_capacity_usd)} |
| Liquidity gap | {_format_money(report.liquidity_gap_usd)} |
| Estimated discount | {report.estimated_discount_bps:.1f} bps |
| Liquidation days | {report.liquidation_days:.2f} |
| Weighted spread | {report.weighted_spread_bps:.1f} bps |
| Thin-basket weight | {report.thin_weight:.1%} |

## Key warnings

{warnings}

## Methodology

- {report.methodology['liquidity_model']}
- {report.methodology['capacity_model']}
- {report.methodology['discount_model']}
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ETF liquidity illusion and redemption-stress diagnostics")
    sub = parser.add_subparsers(dest="command", required=True)
    stress = sub.add_parser("stress", help="stress a holdings CSV")
    stress.add_argument("holdings_csv")
    stress.add_argument("--aum", type=float, required=True, help="fund AUM in USD")
    stress.add_argument("--redemption-pct", type=float, required=True, help="one-day redemption shock as decimal")
    stress.add_argument("--ap-capacity", type=float, required=True, help="authorized participant daily capacity in USD")
    stress.add_argument("--market-depth", type=float, default=1.0, help="market depth multiplier during stress")
    stress.add_argument("--tracking-buffer-bps", type=float, default=25.0, help="baseline tracking buffer in bps")
    stress.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "stress":
        holdings = load_holdings_csv(args.holdings_csv)
        scenario = StressScenario(
            fund_aum_usd=args.aum,
            redemption_pct=args.redemption_pct,
            ap_daily_capacity_usd=args.ap_capacity,
            market_depth_multiplier=args.market_depth,
            tracking_buffer_bps=args.tracking_buffer_bps,
        )
        report = analyze_liquidity_stress(holdings, scenario)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        else:
            print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
