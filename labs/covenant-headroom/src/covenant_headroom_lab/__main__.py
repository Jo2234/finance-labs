from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import CovenantResult, CovenantSpec, analyze_period, load_periods_csv, run_scenario, summarize_results


def _parse_scenario(value: str) -> tuple[str, float, float, float]:
    """Parse name:ebitda_shock_pct:net_debt_delta:liquidity_delta."""
    parts = value.split(":")
    if len(parts) != 4 or not parts[0]:
        raise argparse.ArgumentTypeError(
            "scenario must be name:ebitda_shock_pct:net_debt_delta:liquidity_delta"
        )
    try:
        return parts[0], float(parts[1]), float(parts[2]), float(parts[3])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("scenario shock values must be numeric") from exc


def _round_nested(obj):
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, dict):
        return {k: _round_nested(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round_nested(v) for v in obj]
    return obj


def _markdown_table(results: list[CovenantResult]) -> str:
    lines = [
        "| Period | Scenario | Status | Net leverage | Interest coverage | Liquidity | Breaches |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for result in results:
        breaches = ", ".join(result.breaches) if result.breaches else "—"
        lines.append(
            "| {period} | {scenario} | {status} | {nl:.2f}x | {ic:.2f}x | ${liq:.1f}m | {breaches} |".format(
                period=result.period,
                scenario=result.scenario,
                status=result.status.upper(),
                nl=result.metrics["net_leverage"],
                ic=result.metrics["interest_coverage"],
                liq=result.metrics["liquidity"],
                breaches=breaches,
            )
        )
    return "\n".join(lines)


def render_markdown(results: list[CovenantResult], spec: CovenantSpec) -> str:
    summary = summarize_results(results)
    return "\n".join(
        [
            "# Covenant Headroom Report",
            "",
            "This report estimates credit-agreement cushion under base and downside cases.",
            "",
            "## Covenant package",
            "",
            f"- Maximum net leverage: {spec.max_net_leverage:.2f}x",
            f"- Minimum interest coverage: {spec.min_interest_coverage:.2f}x",
            f"- Minimum liquidity: ${spec.min_liquidity:.1f}m",
            "",
            "## Executive summary",
            "",
            f"- Base periods analyzed: {summary['periods']}",
            f"- Base breaches: {summary['base_breaches']}",
            f"- Total breached period/scenario combinations: {summary['total_breaches']}",
            f"- Worst net leverage: {summary['worst_net_leverage']:.2f}x ({summary['worst_net_leverage_period']}, {summary['worst_net_leverage_scenario']})",
            f"- Tightest covenant cushion: {summary['tightest_headroom_period']} / {summary['tightest_headroom_scenario']}",
            "",
            "## Period detail",
            "",
            _markdown_table(results),
            "",
            "## Methodology",
            "",
            "Net leverage is net debt divided by adjusted EBITDA; interest coverage is adjusted EBITDA divided by cash interest. Headroom is measured in absolute covenant units, with negative headroom marked as a breach. Scenario syntax is `name:ebitda_shock_pct:net_debt_delta:liquidity_delta`.",
            "",
            "Not investment advice. Use as an offline credit-screening aid before deeper legal and financial review.",
        ]
    )


def analyze_command(args: argparse.Namespace) -> int:
    spec = CovenantSpec(
        max_net_leverage=args.max_net_leverage,
        min_interest_coverage=args.min_interest_coverage,
        min_liquidity=args.min_liquidity,
    )
    periods = load_periods_csv(args.csv)
    results: list[CovenantResult] = [analyze_period(period, spec) for period in periods]
    for scenario_name, ebitda_shock, net_debt_delta, liquidity_delta in args.scenario:
        for period in periods:
            results.append(
                run_scenario(
                    period,
                    spec,
                    name=scenario_name,
                    ebitda_shock_pct=ebitda_shock,
                    net_debt_delta=net_debt_delta,
                    liquidity_delta=liquidity_delta,
                )
            )

    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(results, spec))

    payload = {
        "summary": summarize_results(results),
        "results": [result.to_dict() for result in results],
    }
    print(json.dumps(_round_nested(payload), indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="covenant-headroom",
        description="Offline covenant headroom and downside stress analyzer for credit portfolios.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze = subparsers.add_parser("analyze", help="Analyze a CSV of period financials")
    analyze.add_argument("csv", help="CSV with period,revenue,adjusted_ebitda,net_debt,cash_interest,liquidity")
    analyze.add_argument("--max-net-leverage", type=float, required=True)
    analyze.add_argument("--min-interest-coverage", type=float, required=True)
    analyze.add_argument("--min-liquidity", type=float, required=True)
    analyze.add_argument(
        "--scenario",
        action="append",
        type=_parse_scenario,
        default=[],
        help="Downside case as name:ebitda_shock_pct:net_debt_delta:liquidity_delta. Repeatable.",
    )
    analyze.add_argument("--markdown-out", help="Optional path for a Markdown credit memo")
    analyze.set_defaults(func=analyze_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
