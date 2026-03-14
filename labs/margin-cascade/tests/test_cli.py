import json
import subprocess
import sys
from pathlib import Path


def test_cli_emits_json_report_for_sample_book(tmp_path):
    sample = Path(__file__).resolve().parents[1] / "examples" / "sample_book.csv"
    output = tmp_path / "report.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "margin_cascade_lab",
            "--book",
            str(sample),
            "--shock",
            "ALPHA=-0.22",
            "--shock",
            "GAMMA=-0.08",
            "--format",
            "json",
            "--output",
            str(output),
        ],
        check=True,
        text=True,
        capture_output=True,
        env={"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
    )

    assert "wrote" in completed.stdout.lower()
    report = json.loads(output.read_text())
    assert report["scenario"]["shocks"]["ALPHA"] == -0.22
    assert report["total_liquidated_value"] > 0
    assert report["systemic_risk_score"] > 0
    assert "most_stressed_fund" in report
