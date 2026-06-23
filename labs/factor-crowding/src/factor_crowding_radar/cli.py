from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from . import __version__
from .core import CrowdingInputError, CrowdingReport, analyze_crowding


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    if args.command == "analyze":
        return _run_analyze(args)
    parser.print_help()
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="factor-crowding-radar",
        description="Detect crowded factor exposures and unwind risk from an offline portfolio JSON file.",
    )
    parser.add_argument("--version", action="store_true", help="Print package version and exit.")
    subparsers = parser.add_subparsers(dest="command")
    analyze = subparsers.add_parser("analyze", help="Analyze a portfolio JSON file.")
    analyze.add_argument("input", type=Path, help="Path to JSON with a top-level 'positions' array.")
    analyze.add_argument("--shock-bps", type=float, default=350, help="Top-factor unwind shock in basis points (default: 350).")
    analyze.add_argument("--format", choices=["json", "markdown"], default="json", help="Output format.")
    analyze.add_argument("--output", type=Path, help="Optional path to write the full report.")
    return parser


def _run_analyze(args: argparse.Namespace) -> int:
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        positions = payload["positions"] if isinstance(payload, dict) else payload
        report = analyze_crowding(positions, shock_bps=args.shock_bps)
    except (OSError, json.JSONDecodeError, KeyError, CrowdingInputError) as exc:
        raise SystemExit(f"factor-crowding-radar: {exc}") from exc

    body = render_markdown(report) if args.format == "markdown" else json.dumps(report.to_dict(), indent=2)
    if args.output:
        args.output.write_text(body + "\n", encoding="utf-8")
    print(_summary_line(report))
    if not args.output:
        print(body)
    return 0


def _summary_line(report: CrowdingReport) -> str:
    return (
        f"{report.risk_level} crowding risk | score={report.crowding_score}/100 | "
        f"top_factor={report.top_factor} ({report.top_factor_weight:.1%}) | "
        f"unwind_loss={report.unwind_loss_pct:.2f}%"
    )


def render_markdown(report: CrowdingReport) -> str:
    exposure_rows = "\n".join(
        f"| {factor} | {weight:.1%} |" for factor, weight in sorted(report.factor_exposures.items(), key=lambda item: item[1], reverse=True)
    )
    alerts = "\n".join(f"- {alert}" for alert in report.alerts)
    methodology = "\n".join(f"- {step}" for step in report.methodology)
    return f"""# Factor Crowding Radar Report

## Executive summary

- **Risk level:** {report.risk_level}
- **Crowding score:** {report.crowding_score}/100
- **Top factor:** {report.top_factor} ({report.top_factor_weight:.1%})
- **Average pairwise correlation:** {report.average_pairwise_correlation:.2f}
- **Factor concentration HHI:** {report.concentration_hhi:.2f}
- **Unwind stress loss:** {report.unwind_loss_pct:.2f}%

## Factor exposures

| Factor | Portfolio weight |
| --- | ---: |
{exposure_rows}

## Alerts

{alerts}

## Methodology

{methodology}

> This is an offline research/risk-screening tool, not investment advice. Validate inputs and assumptions before using it in production.
"""


if __name__ == "__main__":
    raise SystemExit(main())
