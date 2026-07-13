import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
os.environ["PYTHONPATH"] = str(SRC) + os.pathsep + os.environ.get("PYTHONPATH", "")


def test_cli_outputs_json_report_for_sample_csv(tmp_path):
    sample = ROOT / "examples" / "sample_holdings.csv"
    output = tmp_path / "report.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "etf_liquidity_stress_lab",
            "stress",
            str(sample),
            "--aum",
            "2500000000",
            "--redemption-pct",
            "0.12",
            "--ap-capacity",
            "160000000",
            "--market-depth",
            "0.70",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    output.write_text(result.stdout)

    data = json.loads(output.read_text())
    assert data["risk_level"] in {"elevated", "severe"}
    assert data["redemption_usd"] == 300000000
    assert data["liquidity_gap_usd"] > 0
    assert data["methodology"]["discount_model"]
