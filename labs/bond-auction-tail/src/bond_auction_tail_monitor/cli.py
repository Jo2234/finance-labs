from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import analyze_series, load_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bond-auction-tail-monitor",
        description="Rank Treasury auctions by tail, bid-to-cover, and investor demand stress.",
    )
    parser.add_argument("csv", type=Path, help="Auction CSV with date, tenor, yields, and allocation percentages")
    parser.add_argument("--lookback", type=int, default=6, help="Per-tenor history window for z-scores (default: 6)")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--latest-only", action="store_true", help="Show only the latest auction per tenor")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reports = analyze_series(load_csv(args.csv), lookback=args.lookback)
    if args.latest_only:
        latest = {}
        for report in reports:
            latest[report.tenor] = report
        reports = list(latest.values())
    reports = sorted(reports, key=lambda report: report.stress_score, reverse=True)

    if args.format == "json":
        print(json.dumps([report.as_dict() for report in reports], indent=2))
    else:
        print(_markdown(reports))
    return 0


def _markdown(reports) -> str:
    lines = [
        "# Bond Auction Tail Monitor Report",
        "",
        "| Date | Tenor | Tail bp | Bid/Cover | Indirect % | Dealer % | Score | Regime | Drivers |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for report in reports:
        lines.append(
            f"| {report.date} | {report.tenor} | {report.tail_bp:.2f} | "
            f"{report.bid_to_cover:.2f} | {report.indirect_pct:.1f} | {report.dealer_pct:.1f} | "
            f"{report.stress_score} | {report.regime} | {', '.join(report.drivers)} |"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
