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


def test_insolvency_renders_strict_json_and_explicit_markdown():
    from margin_cascade_lab.engine import Position, run_cascade
    from margin_cascade_lab.cli import result_to_dict, render_markdown
    result = run_cascade([Position('F', 'A', 0, 100, debt=10)])
    payload = json.loads(json.dumps(result_to_dict(result), allow_nan=False))
    assert payload['fund_summaries']['F']['leverage'] is None
    assert payload['fund_summaries']['F']['margin_ratio'] is None
    assert payload['fund_summaries']['F']['equity'] == -10
    assert 'insolvent' in render_markdown(result)
    assert 'N/A' in render_markdown(result)
