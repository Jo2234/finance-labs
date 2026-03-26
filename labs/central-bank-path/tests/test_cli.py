import json
import subprocess
import sys
from pathlib import Path


SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample_path.csv"


def test_cli_json_outputs_regime_and_policy_steps():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cbpathlab",
            "analyze",
            str(SAMPLE),
            "--current-rate",
            "5.35",
            "--neutral-rate",
            "3.25",
            "--format",
            "json",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(result.stdout)
    assert payload["regime"] == "hard-landing hedge"
    assert payload["terminal_expected_rate"] == 4.48
    assert len(payload["steps"]) == 4
    assert payload["steps"][0]["contract"] == "ZQH6"


def test_cli_markdown_prints_decision_table():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cbpathlab",
            "analyze",
            str(SAMPLE),
            "--current-rate",
            "5.35",
            "--neutral-rate",
            "3.25",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "# Central Bank Path Lab Report" in result.stdout
    assert "| 2026-03-18 | ZQH6 | 5.10% | -25 bps | 100% |" in result.stdout
    assert "hard-landing hedge" in result.stdout
