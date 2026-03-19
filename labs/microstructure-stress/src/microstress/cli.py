from __future__ import annotations

import argparse
import json
from pathlib import Path

from .report import analyze_csv, render_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="microstress",
        description="Analyze an OHLCV + quote/depth CSV for market microstructure stress.",
    )
    parser.add_argument("csv", type=Path, help="CSV with timestamp, close, volume, bid, ask, bid_size, ask_size")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")
    parser.add_argument("--title", default="Microstructure Stress Report", help="Markdown report title")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = analyze_csv(args.csv)
    if args.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(render_markdown(summary, title=args.title), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
