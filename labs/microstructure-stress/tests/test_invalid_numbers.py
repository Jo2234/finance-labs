import subprocess
import sys

import pytest

from microstress.metrics import (
    Bar, OrderBookSnapshot, amihud_illiquidity, classify_stress,
    order_book_imbalance, spread_bps, stress_score, volume_shock,
)
from microstress.report import analyze_csv


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), float("-inf")])
def test_public_metrics_reject_nonfinite_inputs(invalid):
    checks = [
        lambda: spread_bps(bid=invalid, ask=101),
        lambda: order_book_imbalance(OrderBookSnapshot(100, invalid)),
        lambda: amihud_illiquidity([Bar("a", invalid, 100), Bar("b", 101, 100)]),
        lambda: volume_shock([Bar("a", 100, invalid), Bar("b", 101, 100)]),
        lambda: classify_stress(invalid),
    ]
    for check in checks:
        with pytest.raises(ValueError, match="finite"):
            check()


@pytest.mark.parametrize("field", ["spread_bps", "volume_shock", "amihud", "abs_imbalance"])
def test_nan_component_cannot_produce_a_severe_label(field):
    inputs = dict(spread_bps=1, volume_shock=1, amihud=0, abs_imbalance=0)
    inputs[field] = float("nan")
    with pytest.raises(ValueError, match=f"{field} must be finite"):
        stress_score(**inputs)


@pytest.mark.parametrize("invalid_row", [0, 1])
def test_nonfinite_quote_in_any_csv_row_is_rejected(tmp_path, invalid_row):
    rows = ["a,100,100,99,101,100,100", "b,101,100,100,102,100,100"]
    fields = rows[invalid_row].split(",")
    fields[3] = "nan"
    rows[invalid_row] = ",".join(fields)
    path = tmp_path / "tape.csv"
    path.write_text("timestamp,close,volume,bid,ask,bid_size,ask_size\n" + "\n".join(rows))
    with pytest.raises(ValueError, match=f"CSV row {invalid_row + 2}: bid must be finite"):
        analyze_csv(path)
    result = subprocess.run(
        [sys.executable, "-m", "microstress", str(path), "--format", "json"],
        text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert not result.stdout
