import pytest

from guidance_drift_lab.scoring import analyze_company, score_transcript


def test_score_transcript_flags_upbeat_language_with_negative_numbers():
    transcript = """
    We are excited by resilient demand and strong enterprise momentum.
    Management is confident in a reacceleration next quarter.
    """
    result = score_transcript(
        transcript,
        revenue_growth=-0.08,
        margin_change_bps=-220,
        guidance_change=-0.06,
    )

    assert result.sentiment_score > 0
    assert result.fundamental_score < 0
    assert result.drift_score == pytest.approx(0.79, abs=0.02)
    assert result.label == "high positive-language drift"
    assert "optimistic tone conflicts" in result.explanation.lower()


def test_analyze_company_sorts_quarters_by_drift_descending():
    rows = [
        {
            "company": "Acme Cloud",
            "quarter": "2026-Q1",
            "transcript": "stable cautious execution with some softness",
            "revenue_growth": "0.02",
            "margin_change_bps": "30",
            "guidance_change": "0.01",
        },
        {
            "company": "Acme Cloud",
            "quarter": "2026-Q2",
            "transcript": "exceptional confident acceleration and strong demand",
            "revenue_growth": "-0.11",
            "margin_change_bps": "-180",
            "guidance_change": "-0.04",
        },
    ]

    report = analyze_company(rows)

    assert report.company == "Acme Cloud"
    assert [item.quarter for item in report.quarters] == ["2026-Q2", "2026-Q1"]
    assert report.quarters[0].drift_score > report.quarters[1].drift_score
    assert report.summary.startswith("Acme Cloud shows")


def test_score_transcript_rejects_empty_transcript():
    with pytest.raises(ValueError, match="transcript"):
        score_transcript("   ", revenue_growth=0.01, margin_change_bps=0, guidance_change=0)
