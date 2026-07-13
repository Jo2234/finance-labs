import json
import subprocess
import sys
from pathlib import Path


def test_cli_generates_json_and_markdown_reports(tmp_path):
    sample = Path(__file__).parents[1] / "examples" / "spy_option_chain_sample.csv"
    json_out = tmp_path / "report.json"
    md_out = tmp_path / "report.md"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "options_skew_sentinel",
            "analyze",
            str(sample),
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(md_out),
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    assert "SPY options skew" in result.stdout
    payload = json.loads(json_out.read_text())
    assert payload["symbol"] == "SPY"
    assert payload["alert_level"] in {"normal", "watch", "elevated", "extreme"}
    assert "Risk reversal" in md_out.read_text()
