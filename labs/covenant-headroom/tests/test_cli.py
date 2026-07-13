import json
import subprocess
import sys
from pathlib import Path


def test_cli_generates_json_and_markdown_reports(tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "period,revenue,adjusted_ebitda,net_debt,cash_interest,liquidity\n"
        "2026-Q1,120,30,105,10,40\n"
        "2026-Q2,100,20,100,12,18\n"
    )
    markdown_path = tmp_path / "report.md"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "covenant_headroom_lab",
            "analyze",
            str(csv_path),
            "--max-net-leverage",
            "4.0",
            "--min-interest-coverage",
            "2.0",
            "--min-liquidity",
            "25",
            "--scenario",
            "downside:-15:10:-5",
            "--markdown-out",
            str(markdown_path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(result.stdout)
    assert payload["summary"]["periods"] == 2
    assert payload["summary"]["base_breaches"] == 1
    assert payload["summary"]["worst_net_leverage"] > 5.0
    assert "2026-Q2" in markdown_path.read_text()
    assert "downside" in markdown_path.read_text()
