from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cbpathlab import __version__
from cbpathlab.core import Meeting, PathAnalysis, PathInputs, analyze_path


def load_csv(path: Path) -> PathInputs:
    rows = list(csv.DictReader(path.read_text().splitlines()))
    if not rows:
        raise ValueError("CSV must contain at least one meeting row")

    meetings: list[Meeting] = []
    macro: dict[str, float] = {}
    for row in rows:
        expected_rate = float(row["expected_rate"]) if row.get("expected_rate") else 100.0 - float(row["futures_price"])
        meetings.append(
            Meeting(
                date=row["date"],
                contract=row.get("contract") or None,
                futures_price=float(row["futures_price"]) if row.get("futures_price") else None,
                expected_rate=round(expected_rate, 6),
            )
        )
        for field in ("core_pce_yoy", "unemployment_rate", "ism_new_orders"):
            if row.get(field) not in (None, ""):
                macro[field] = float(row[field])

    return PathInputs(current_rate=0.0, neutral_rate=0.0, meetings=meetings, macro=macro)


def analysis_to_dict(analysis: PathAnalysis, meetings: list[Meeting]) -> dict[str, Any]:
    steps = []
    by_date = {m.date: m for m in meetings}
    for step in analysis.steps:
        meeting = by_date[step.meeting_date]
        item = asdict(step)
        item["contract"] = meeting.contract
        item["futures_price"] = meeting.futures_price
        steps.append(item)

    return {
        "current_rate": analysis.current_rate,
        "terminal_expected_rate": analysis.terminal_expected_rate,
        "total_easing_bps": analysis.total_easing_bps,
        "neutral_gap_bps": analysis.neutral_gap_bps,
        "regime": analysis.regime,
        "flags": analysis.flags,
        "macro": dict(analysis.macro),
        "steps": steps,
    }


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def render_markdown(analysis: PathAnalysis, meetings: list[Meeting]) -> str:
    data = analysis_to_dict(analysis, meetings)
    lines = [
        "# Central Bank Path Lab Report",
        "",
        f"**Regime:** {analysis.regime}",
        f"**Terminal expected rate:** {analysis.terminal_expected_rate:.2f}%",
        f"**Total path change:** {analysis.total_easing_bps:.0f} bps",
        f"**Terminal gap to neutral:** {analysis.neutral_gap_bps:.0f} bps",
        "",
        "## Meeting-implied path",
        "",
        "| Meeting | Contract | Expected rate | Step change | Cut odds | Hold odds | Hike odds |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for step in data["steps"]:
        lines.append(
            "| {meeting_date} | {contract} | {rate:.2f}% | {change:.0f} bps | {cut} | {hold} | {hike} |".format(
                meeting_date=step["meeting_date"],
                contract=step["contract"] or "—",
                rate=step["cumulative_expected_rate"],
                change=step["expected_change_bps"],
                cut=_pct(step["cut_probability"]),
                hold=_pct(step["hold_probability"]),
                hike=_pct(step["hike_probability"]),
            )
        )
    lines.extend(["", "## Interpretation flags", ""])
    if analysis.flags:
        lines.extend(f"- {flag}" for flag in analysis.flags)
    else:
        lines.append("- No major path/story inconsistencies detected.")
    lines.extend(
        [
            "",
            "## Methodology",
            "",
            "Fed Funds futures-style prices are converted as `100 - price`. Adjacent expected rates are compared meeting by meeting, and the expected bps move is divided by a 25 bp policy step to infer transparent one-step cut/hold/hike odds. The regime label combines the priced path with simple macro context; it is a diagnostic, not investment advice.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit central-bank policy paths implied by futures curves.")
    parser.add_argument("--version", action="version", version=f"cbpathlab {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze = subparsers.add_parser("analyze", help="Analyze a CSV of meeting dates and implied rates")
    analyze.add_argument("csv_path", type=Path)
    analyze.add_argument("--current-rate", type=float, required=True)
    analyze.add_argument("--neutral-rate", type=float, required=True)
    analyze.add_argument("--step-bps", type=int, default=25)
    analyze.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    loaded = load_csv(args.csv_path)
    inputs = PathInputs(
        current_rate=args.current_rate,
        neutral_rate=args.neutral_rate,
        meetings=loaded.meetings,
        macro=loaded.macro,
        step_bps=args.step_bps,
    )
    analysis = analyze_path(inputs)
    if args.format == "json":
        print(json.dumps(analysis_to_dict(analysis, loaded.meetings), indent=2, sort_keys=True))
    else:
        print(render_markdown(analysis, loaded.meetings), end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
