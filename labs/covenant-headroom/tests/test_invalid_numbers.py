import subprocess
import sys
from dataclasses import replace

import pytest

from covenant_headroom_lab import CovenantSpec, PeriodFinancials, analyze_period, run_scenario


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("field", ["revenue", "adjusted_ebitda", "net_debt", "cash_interest", "liquidity"])
def test_nonfinite_financials_cannot_receive_a_covenant_pass(field, invalid):
    period = replace(PeriodFinancials("Q1", 100, 30, 100, 10, 30), **{field: invalid})
    with pytest.raises(ValueError, match=f"{field} must be finite"):
        analyze_period(period, CovenantSpec(4, 2, 25))


@pytest.mark.parametrize("field", ["max_net_leverage", "min_interest_coverage", "min_liquidity"])
def test_nonfinite_threshold_cannot_disable_a_covenant(field):
    spec = replace(CovenantSpec(4, 2, 25), **{field: float("nan")})
    with pytest.raises(ValueError, match=f"{field} must be finite"):
        analyze_period(PeriodFinancials("Q1", 100, 30, 100, 10, 30), spec)


def test_nonfinite_scenario_is_rejected():
    with pytest.raises(ValueError, match="adjusted_ebitda must be finite"):
        run_scenario(PeriodFinancials("Q1", 100, 30, 100, 10, 30), CovenantSpec(4, 2, 25),
                     name="invalid", ebitda_shock_pct=float("nan"))


def test_nan_ebitda_csv_does_not_emit_a_passing_report(tmp_path):
    path = tmp_path / "periods.csv"
    path.write_text("period,revenue,adjusted_ebitda,net_debt,cash_interest,liquidity\nQ1,100,nan,100,10,30\n")
    result = subprocess.run(
        [sys.executable, "-m", "covenant_headroom_lab", "analyze", str(path),
         "--max-net-leverage", "4", "--min-interest-coverage", "2", "--min-liquidity", "25"],
        text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert "adjusted_ebitda must be finite" in result.stderr
    assert not result.stdout
