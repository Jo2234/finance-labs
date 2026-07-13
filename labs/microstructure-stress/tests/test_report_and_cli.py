import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from microstress.report import analyze_csv, render_markdown


def write_sample(path: Path) -> None:
    rows = [
        ["timestamp", "close", "volume", "bid", "ask", "bid_size", "ask_size"],
        ["2026-01-01T09:30:00", "100.00", "1000", "99.98", "100.02", "900", "1100"],
        ["2026-01-01T09:31:00", "100.40", "1300", "100.36", "100.44", "1000", "1000"],
        ["2026-01-01T09:32:00", "99.10", "4200", "99.00", "99.20", "2300", "700"],
    ]
    path.write_text("\n".join(",".join(row) for row in rows) + "\n")


def test_analyze_csv_returns_actionable_stress_summary(tmp_path):
    sample = tmp_path / "bars.csv"
    write_sample(sample)

    summary = analyze_csv(sample)

    assert summary["observations"] == 3
    assert summary["latest_timestamp"] == "2026-01-01T09:32:00"
    assert summary["latest_spread_bps"] == pytest.approx(20.18163471241194)
    assert summary["order_book_imbalance"] == 0.5333333333333333
    assert summary["stress_label"] in {"calm", "watch", "elevated", "severe"}
    assert summary["recommendations"]


def test_render_markdown_includes_methodology_and_recommendations(tmp_path):
    sample = tmp_path / "bars.csv"
    write_sample(sample)
    markdown = render_markdown(analyze_csv(sample), title="Test Desk")

    assert "# Test Desk" in markdown
    assert "## Methodology" in markdown
    assert "## Desk actions" in markdown
    assert "Stress score" in markdown


def test_cli_emits_json_and_markdown(tmp_path):
    sample = tmp_path / "bars.csv"
    write_sample(sample)

    env = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}
    json_run = subprocess.run(
        [sys.executable, "-m", "microstress", str(sample), "--format", "json"],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    payload = json.loads(json_run.stdout)
    assert payload["observations"] == 3
    assert "stress_score" in payload

    md_run = subprocess.run(
        [sys.executable, "-m", "microstress", str(sample), "--format", "markdown", "--title", "Liquidity Tape"],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    assert "# Liquidity Tape" in md_run.stdout
    assert "Desk actions" in md_run.stdout
