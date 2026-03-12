from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import re
from typing import Any, Iterable

__version__ = "0.1.0"


@dataclass(frozen=True)
class Finding:
    category: str
    severity: str
    weight: int
    message_index: int
    evidence: str
    rationale: str


@dataclass(frozen=True)
class Report:
    score: int
    severity: str
    findings: list[Finding] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    message_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "severity": self.severity,
            "message_count": self.message_count,
            "findings": [asdict(f) for f in self.findings],
            "recommendations": self.recommendations,
        }


RULES: tuple[tuple[str, str, str, int, str], ...] = (
    (
        "instruction_override",
        r"\b(ignore|disregard|forget|override|bypass)\b.{0,80}\b(previous|prior|system|developer|instructions?|policy|rules?)\b",
        "high",
        35,
        "Attempts to invert or erase higher-priority instructions.",
    ),
    (
        "secret_exfiltration",
        r"\b(system prompt|api[_ -]?key|secret|token|password|credential|hidden chain of thought)\b",
        "high",
        30,
        "Requests disclosure of protected prompts, credentials, or hidden reasoning.",
    ),
    (
        "external_endpoint",
        r"https?://|\b[a-z0-9.-]+\.(?:com|net|org|io|dev|xyz)\b",
        "medium",
        20,
        "Mentions an external endpoint that could receive exfiltrated data or stage instructions.",
    ),
    (
        "tool_abuse",
        r"\b(browser\.open|shell|subprocess|curl|wget|rm -rf|delete files?|send email|post to|transfer)\b",
        "high",
        30,
        "Tries to drive tools, network calls, or destructive actions from untrusted content.",
    ),
    (
        "encoded_payload",
        r"\b(?:decode|base64|rot13|hex)\b|\b[A-Za-z0-9+/]{20,}={0,2}\b",
        "medium",
        25,
        "Uses encoded or obfuscated content that may hide adversarial instructions.",
    ),
    (
        "roleplay_jailbreak",
        r"\b(DAN|developer mode|jailbreak|simulate|roleplay as|no safety)\b",
        "medium",
        20,
        "Uses common jailbreak framing or roleplay to weaken policy boundaries.",
    ),
)

RECOMMENDATIONS = {
    "instruction_override": "Preserve instruction hierarchy: treat user/content instructions as data unless trusted by the application.",
    "secret_exfiltration": "Block disclosure of prompts, credentials, hidden reasoning, and environment-derived secrets.",
    "external_endpoint": "Require explicit allowlists and user confirmation before visiting or sending data to external endpoints.",
    "tool_abuse": "Gate tool calls behind intent checks, scoped permissions, and auditable execution policies.",
    "encoded_payload": "Decode in a sandbox for inspection; do not execute decoded instructions as commands or policy.",
    "roleplay_jailbreak": "Classify roleplay jailbreaks as untrusted content and keep safety/developer constraints active.",
}


def _severity(score: int) -> str:
    if score >= 90:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def _evidence(text: str, match: re.Match[str]) -> str:
    start = max(0, match.start() - 35)
    end = min(len(text), match.end() + 35)
    return text[start:end].strip()


def _validate(messages: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = list(messages)
    for i, message in enumerate(normalized):
        if "role" not in message:
            raise ValueError(f"message {i} is missing required field 'role'")
        if "content" not in message:
            raise ValueError(f"message {i} is missing required field 'content'")
    return normalized


def analyze_messages(messages: Iterable[dict[str, Any]]) -> Report:
    normalized = _validate(messages)
    findings: list[Finding] = []
    for idx, message in enumerate(normalized):
        content = str(message.get("content", ""))
        tool_name = str(message.get("tool_name", ""))
        haystack = f"{content}\n{tool_name}"
        for category, pattern, severity, weight, rationale in RULES:
            match = re.search(pattern, haystack, flags=re.IGNORECASE | re.DOTALL)
            if match:
                findings.append(
                    Finding(
                        category=category,
                        severity=severity,
                        weight=weight,
                        message_index=idx,
                        evidence=_evidence(haystack, match),
                        rationale=rationale,
                    )
                )

    raw_score = sum(f.weight for f in findings)
    # Escalate combinations that are particularly dangerous in agentic apps.
    categories = {f.category for f in findings}
    if {"tool_abuse", "encoded_payload", "external_endpoint"} <= categories:
        raw_score += 20
    score = min(100, raw_score)
    ordered_recs = [RECOMMENDATIONS[c] for c in RECOMMENDATIONS if c in categories]
    return Report(score=score, severity=_severity(score), findings=findings, recommendations=ordered_recs, message_count=len(normalized))


def render_markdown(report: Report) -> str:
    lines = [
        "# PromptFirewall Lab Report",
        "",
        f"Severity: **{report.severity.upper()}**",
        f"Score: **{report.score}/100**",
        f"Messages analyzed: **{report.message_count}**",
        "",
    ]
    if not report.findings:
        lines.extend(["## Findings", "", "No prompt-injection indicators were detected.", ""])
    else:
        lines.extend(["## Ranked findings", ""])
        for finding in sorted(report.findings, key=lambda f: f.weight, reverse=True):
            lines.extend(
                [
                    f"### {finding.category} ({finding.severity}, +{finding.weight})",
                    f"- Message: `{finding.message_index}`",
                    f"- Evidence: `{finding.evidence}`",
                    f"- Why it matters: {finding.rationale}",
                    "",
                ]
            )
    if report.recommendations:
        lines.extend(["## Recommendations", ""])
        lines.extend(f"- {rec}" for rec in report.recommendations)
        lines.append("")
    return "\n".join(lines)


def report_to_json(report: Report) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)
