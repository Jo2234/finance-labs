from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

POSITIVE_WORDS = {
    "accelerate",
    "acceleration",
    "confident",
    "constructive",
    "exceptional",
    "excited",
    "healthy",
    "improvement",
    "momentum",
    "reacceleration",
    "resilient",
    "strong",
    "upside",
}

NEGATIVE_WORDS = {
    "cautious",
    "decline",
    "digestion",
    "headwind",
    "normalization",
    "pressure",
    "risk",
    "soft",
    "softness",
    "weak",
}

METHODOLOGY = (
    "Guidance Drift Lab compares earnings-call tone with three simple fundamentals: "
    "revenue growth, margin change in basis points, and guidance revision. Positive "
    "language paired with deteriorating fundamentals receives a higher drift score."
)


@dataclass(frozen=True)
class QuarterScore:
    quarter: str
    sentiment_score: float
    fundamental_score: float
    drift_score: float
    label: str
    explanation: str


@dataclass(frozen=True)
class CompanyReport:
    company: str
    quarters: list[QuarterScore]
    summary: str
    methodology: str = METHODOLOGY

    def to_dict(self) -> dict:
        return {
            "company": self.company,
            "summary": self.summary,
            "methodology": self.methodology,
            "quarters": [asdict(q) for q in self.quarters],
        }


def score_transcript(
    transcript: str,
    *,
    revenue_growth: float,
    margin_change_bps: float,
    guidance_change: float,
    quarter: str = "unlabeled",
) -> QuarterScore:
    """Score management-language drift for one earnings period."""
    if not transcript or not transcript.strip():
        raise ValueError("transcript must contain text")

    tokens = re.findall(r"[a-zA-Z]+", transcript.lower())
    positives = sum(token in POSITIVE_WORDS for token in tokens)
    negatives = sum(token in NEGATIVE_WORDS for token in tokens)
    sentiment_score = _clamp((positives - negatives) / max(positives + negatives + 1, 1), -1.0, 1.0)

    raw_fundamentals = revenue_growth * 4.0 + (margin_change_bps / 600.0) + guidance_change * 4.0
    fundamental_score = math.tanh(raw_fundamentals)

    drift_score = _clamp((sentiment_score - fundamental_score) / 2.0, 0.0, 1.0)
    label = _label(drift_score)
    explanation = _explain(drift_score, sentiment_score, fundamental_score)

    return QuarterScore(
        quarter=quarter,
        sentiment_score=round(sentiment_score, 3),
        fundamental_score=round(fundamental_score, 3),
        drift_score=round(drift_score, 3),
        label=label,
        explanation=explanation,
    )


def analyze_company(rows: Iterable[Mapping[str, object]]) -> CompanyReport:
    scores: list[QuarterScore] = []
    company: str | None = None
    for row in rows:
        row_company = row.get("company")
        if not isinstance(row_company, str) or not row_company.strip():
            raise ValueError("every row must contain a nonempty company name")
        row_company = row_company.strip()
        if company is not None and row_company != company:
            raise ValueError("all rows must belong to the same company")
        company = row_company
        scores.append(
            score_transcript(
                str(row["transcript"]),
                revenue_growth=float(row["revenue_growth"]),
                margin_change_bps=float(row["margin_change_bps"]),
                guidance_change=float(row["guidance_change"]),
                quarter=str(row["quarter"]),
            )
        )

    if not scores:
        raise ValueError("at least one row is required")

    scores.sort(key=lambda item: item.drift_score, reverse=True)
    top = scores[0]
    summary = (
        f"{company} shows {top.label} in {top.quarter} "
        f"(drift={top.drift_score:.3f}), making it the quarter most worth analyst review."
    )
    return CompanyReport(company=company, quarters=scores, summary=summary)


def _label(drift_score: float) -> str:
    if drift_score >= 0.68:
        return "high positive-language drift"
    if drift_score >= 0.40:
        return "moderate language drift"
    return "low drift"


def _explain(drift_score: float, sentiment_score: float, fundamental_score: float) -> str:
    if drift_score >= 0.68:
        return "Optimistic tone conflicts with weak fundamentals; review guidance quality and risk disclosures."
    if sentiment_score > 0 and fundamental_score < 0:
        return "Positive language is directionally ahead of fundamentals."
    return "Tone and fundamentals are broadly aligned."


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
