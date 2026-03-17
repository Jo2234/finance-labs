from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .analysis import SkewReport, analyze_chain


def load_csv(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def render_markdown(report: SkewReport) -> str:
    lines = [
        f"# {report.symbol} Options Skew Sentinel Report",
        "",
        f"**Headline:** {report.headline}",
        "",
        f"- Spot: `{report.spot:.2f}`",
        f"- Alert level: `{report.alert_level}`",
        f"- Average risk reversal: `{report.average_risk_reversal:.2%}`",
        f"- Put-wing term slope: `{report.term_structure_slope:.2%}`",
        "",
        "| Expiry | DTE | Put strike | Put wing IV | Call strike | Call wing IV | Risk reversal | Skew ratio |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for expiry in report.expiries:
        lines.append(
            "| {expiry} | {dte:.0f} | {put_strike:.2f} | {put_iv:.2%} | {call_strike:.2f} | {call_iv:.2%} | {rr:.2%} | {ratio:.2f} |".format(
                expiry=expiry.expiry,
                dte=expiry.days_to_expiry,
                put_strike=expiry.put_strike,
                put_iv=expiry.put_wing_iv,
                call_strike=expiry.call_strike,
                call_iv=expiry.call_wing_iv,
                rr=expiry.risk_reversal,
                ratio=expiry.skew_ratio,
            )
        )
    lines.extend(["", "## Methodology", "", report.methodology, ""])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect left-tail option skew from a simple option-chain CSV.")
    sub = parser.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze", help="Analyze option-chain wing skew")
    analyze.add_argument("csv_path", type=Path, help="CSV with symbol, expiry, option_type, strike, mid, spot, rate, days_to_expiry")
    analyze.add_argument("--json-out", type=Path, help="Write machine-readable report JSON")
    analyze.add_argument("--markdown-out", type=Path, help="Write human-readable markdown report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "analyze":
        report = analyze_chain(load_csv(args.csv_path))
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(report.to_dict(), indent=2) + "\n")
        if args.markdown_out:
            args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
            args.markdown_out.write_text(render_markdown(report))
        print(f"{report.symbol} options skew: {report.alert_level.upper()} — {report.headline}")
        for expiry in report.expiries:
            print(
                f"  {expiry.expiry}: put IV {expiry.put_wing_iv:.1%}, call IV {expiry.call_wing_iv:.1%}, "
                f"Risk reversal {expiry.risk_reversal:.1%}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
