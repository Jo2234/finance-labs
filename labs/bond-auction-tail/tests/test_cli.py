import json
import subprocess
import sys
from pathlib import Path


def test_cli_emits_ranked_json_report(tmp_path):
    csv_path = tmp_path / "auctions.csv"
    csv_path.write_text(
        "date,tenor,high_yield,when_issued_yield,bid_to_cover,indirect_pct,direct_pct,dealer_pct\n"
        "2026-01-10,10Y,4.005,4.000,2.60,70,15,15\n"
        "2026-02-10,10Y,4.106,4.100,2.55,68,16,16\n"
        "2026-03-10,10Y,4.204,4.200,2.58,69,16,15\n"
        "2026-04-10,10Y,4.455,4.420,2.05,54,14,32\n"
    )

    result = subprocess.run(
        [sys.executable, "-m", "bond_auction_tail_monitor", str(csv_path), "--format", "json"],
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload[0]["tenor"] == "10Y"
    assert payload[0]["regime"] == "strained"
    assert payload[0]["stress_score"] >= 75
