from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from . import analyze_messages, render_markdown, report_to_json


def load_messages(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    if isinstance(payload, dict) and "messages" in payload:
        payload = payload["messages"]
    if not isinstance(payload, list):
        raise ValueError("input must be a JSON list of messages or an object with a 'messages' list")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="promptfirewall-lab",
        description="Offline prompt-injection risk scoring for LLM app conversations.",
    )
    parser.add_argument("input", type=Path, help="JSON file: list of messages or {'messages': [...]}")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown", help="Output format")
    parser.add_argument("--output", type=Path, help="Optional output file; stdout is always a one-line summary for markdown")
    parser.add_argument("--fail-on", choices=["low", "medium", "high", "critical"], help="Exit non-zero at or above severity")
    parser.add_argument(
        "--trusted-message-index", type=int, action="append", default=[],
        help="Exclude a verified trusted context message from scoring by zero-based index; repeatable. Evidence is retained.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = analyze_messages(
            load_messages(args.input), trusted_message_indices=args.trusted_message_index
        )
    except Exception as exc:  # pragma: no cover - CLI boundary
        parser.error(str(exc))

    rendered = report_to_json(report) if args.format == "json" else render_markdown(report)
    if args.output:
        args.output.write_text(rendered + "\n")
        print(f"{report.severity.upper()} risk ({report.score}/100): wrote {args.output}")
    else:
        print(rendered)

    if args.fail_on:
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        if order[report.severity] >= order[args.fail_on]:
            return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
