import csv
import subprocess
import sys

import pytest

from guidance_drift_lab.scoring import analyze_company


def row(company, quarter="Q1"):
    return dict(company=company, quarter=quarter, transcript="strong confident excited",
                revenue_growth=-0.2, margin_change_bps=-300, guidance_change=-0.2)


def test_mixed_company_export_cannot_attribute_first_issuers_risk_to_last(tmp_path):
    rows = [row("A"), row("B", "Q2")]
    with pytest.raises(ValueError, match="same company"):
        analyze_company(iter(rows))
    path = tmp_path / "guidance.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = subprocess.run(
        [sys.executable, "-m", "guidance_drift_lab", "analyze", str(path), "--format", "json"],
        text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert "same company" in result.stderr
    assert not result.stdout


@pytest.mark.parametrize("company", [None, "", "  ", 123])
def test_each_quarter_requires_a_real_company_name(company):
    with pytest.raises(ValueError, match="nonempty company"):
        analyze_company([row("A"), row(company, "Q2")])


def test_whitespace_is_trimmed_without_merging_distinct_names():
    report = analyze_company([row(" A "), row("A", "Q2")])
    assert report.company == "A"
    assert len(report.quarters) == 2
    with pytest.raises(ValueError, match="same company"):
        analyze_company([row("A"), row("a", "Q2")])
