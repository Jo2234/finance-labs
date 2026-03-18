from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .scoring import CompanyReport, analyze_company


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guidance-drift",
        description="Detect mismatch between earnings-call language and numeric guidance trends.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze = subparsers.add_parser("analyze", help="Analyze a CSV of quarterly guidance/transcript rows")
    analyze.add_argument("csv_path", type=Path)
    analyze.add_argument("--format", choices=("json", "markdown"), default="markdown")
    analyze.add_argument("--output", type=Path, help="Write report to this path instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "analyze":
        rows = _read_rows(args.csv_path)
        report = analyze_company(rows)
        rendered = render_json(report) if args.format == "json" else render_markdown(report)
        if args.output:
            args.output.write_text(rendered)
        else:
            print(rendered)
        return 0
    raise AssertionError(f"unhandled command: {args.command}")


def render_json(report: CompanyReport) -> str:
    return json.dumps(report.to_dict(), indent=2) + "\n"


def render_markdown(report: CompanyReport) -> str:
    lines = [
        f"# Guidance Drift Report: {report.company}",
        "",
        report.summary,
        "",
        "| Quarter | Drift | Label | Tone | Fundamentals |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    for quarter in report.quarters:
        lines.append(
            f"| {quarter.quarter} | {quarter.drift_score:.3f} | {quarter.label} | "
            f"{quarter.sentiment_score:.3f} | {quarter.fundamental_score:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Methodology",
            "",
            report.methodology,
            "",
            "## Analyst note",
            "",
            report.quarters[0].explanation,
            "",
            "_Not investment advice. Use as a research triage tool, not as a trading signal._",
            "",
        ]
    )
    return "\n".join(lines)


def _read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    raise SystemExit(main())
