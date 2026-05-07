import json
import subprocess
import sys
from pathlib import Path


def test_cli_writes_markdown_and_json(tmp_path):
    data = {
        "positions": [
            {"name": "A", "weight": 0.45, "factor": "Mega-cap AI", "returns": [0.02, 0.01, -0.02, 0.03]},
            {"name": "B", "weight": 0.35, "factor": "Mega-cap AI", "returns": [0.019, 0.011, -0.021, 0.028]},
            {"name": "C", "weight": 0.20, "factor": "Quality", "returns": [-0.001, 0.002, 0.001, 0.0]},
        ]
    }
    input_path = tmp_path / "book.json"
    output_path = tmp_path / "report.md"
    input_path.write_text(json.dumps(data), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "factor_crowding_radar",
            "analyze",
            str(input_path),
            "--shock-bps",
            "500",
            "--format",
            "markdown",
            "--output",
            str(output_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env={"PYTHONPATH": "src"},
        text=True,
        capture_output=True,
        check=True,
    )

    assert "High" in completed.stdout
    report = output_path.read_text(encoding="utf-8")
    assert "# Factor Crowding Radar Report" in report
    assert "Mega-cap AI" in report
    assert "Unwind stress loss" in report


def test_json_stdout_is_one_document_and_summary_goes_to_stderr():
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, '-m', 'factor_crowding_radar', 'analyze',
         str(root / 'examples' / 'sample_portfolio.json'), '--format', 'json'],
        cwd=root, env={'PYTHONPATH': 'src'}, text=True, capture_output=True, check=True,
    )
    assert json.loads(completed.stdout)['top_factor'] == 'AI Infrastructure'
    assert 'crowding risk' in completed.stderr
