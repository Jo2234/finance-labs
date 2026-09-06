import subprocess
import sys
from dataclasses import replace

import pytest

from cbpathlab import Meeting, PathInputs, analyze_path, infer_step_probabilities
from cbpathlab.cli import load_csv


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("field", ["current_rate", "neutral_rate", "expected_rate", "core_pce_yoy"])
def test_nonfinite_curve_or_context_cannot_produce_decision_odds(field, invalid):
    inputs = PathInputs(5, 3, [Meeting("2026-09-16", 4.75)])
    if field == "expected_rate":
        inputs = replace(inputs, meetings=[Meeting("2026-09-16", invalid)])
    elif field == "core_pce_yoy":
        inputs = replace(inputs, macro={field: invalid})
    else:
        inputs = replace(inputs, **{field: invalid})
    with pytest.raises(ValueError, match=f"{field} must be finite"):
        analyze_path(inputs)


def test_direct_probability_api_rejects_nan_step_size():
    with pytest.raises(ValueError, match="step_bps must be finite"):
        infer_step_probabilities(5, [Meeting("2026-09-16", 4.75)], float("nan"))


def test_csv_conversion_uses_futures_price_validation(tmp_path):
    path = tmp_path / "curve.csv"
    path.write_text("date,futures_price\n2026-09-16,-1\n")
    with pytest.raises(ValueError, match="futures price"):
        load_csv(path)
    path.write_text("date,futures_price\n2026-09-16,95.25\n")
    assert load_csv(path).meetings[0].expected_rate == 4.75


def test_nan_csv_cli_fails_without_a_hold_report(tmp_path):
    path = tmp_path / "curve.csv"
    path.write_text("date,expected_rate\n2026-09-16,nan\n")
    result = subprocess.run(
        [sys.executable, "-m", "cbpathlab", "analyze", str(path),
         "--current-rate", "5", "--neutral-rate", "3", "--format", "json"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "expected_rate must be finite" in result.stderr
    assert not result.stdout


def test_later_macro_value_cannot_hide_an_invalid_earlier_row(tmp_path):
    path = tmp_path / "curve.csv"
    path.write_text("date,expected_rate,core_pce_yoy\n2026-09-16,4.75,nan\n2026-10-16,4.50,2.5\n")
    with pytest.raises(ValueError, match="core_pce_yoy must be finite"):
        load_csv(path)
