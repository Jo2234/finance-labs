import json
import subprocess
import sys
from pathlib import Path


def test_cli_outputs_ranked_json_for_sample_dataset():
    sample = Path(__file__).parents[1] / "examples" / "sample_guidance.csv"
    completed = subprocess.run(
        [sys.executable, "-m", "guidance_drift_lab", "analyze", str(sample), "--format", "json"],
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["company"] == "Northstar Semis"
    assert payload["quarters"][0]["quarter"] == "2026-Q2"
    assert payload["quarters"][0]["label"] == "high positive-language drift"
    assert "methodology" in payload


def test_cli_writes_markdown_report(tmp_path):
    sample = Path(__file__).parents[1] / "examples" / "sample_guidance.csv"
    output = tmp_path / "report.md"

    subprocess.run(
        [sys.executable, "-m", "guidance_drift_lab", "analyze", str(sample), "--format", "markdown", "--output", str(output)],
        check=True,
        text=True,
        capture_output=True,
    )

    text = output.read_text()
    assert "# Guidance Drift Report: Northstar Semis" in text
    assert "2026-Q2" in text
    assert "Not investment advice" in text
