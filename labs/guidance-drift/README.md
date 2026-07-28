# Guidance Drift Lab

Guidance Drift Lab is an offline Python CLI for detecting **language/fundamental divergence** in earnings-call commentary. It ranks quarters where management sounds unusually optimistic while revenue growth, margin change, or guidance revisions are deteriorating.

The project is intentionally lightweight: no paid APIs, no scraping, no model keys, and no black-box LLM dependency. It is a reproducible research triage tool that can be run against a simple CSV exported from analyst notes, transcripts, or public filings.

## Why it matters

Market narratives often move before numbers, but sometimes the words and the numbers conflict. A quarter with upbeat language and weakening fundamentals may deserve extra analyst attention: management may be framing a temporary trough, or the market may be underpricing deteriorating guidance quality.

This repo demonstrates a practical finance/AI workflow:

- turn unstructured management language into a transparent tone score,
- combine it with numeric operating signals,
- rank the highest-drift quarters,
- export analyst-friendly JSON or Markdown reports,
- test the scoring and CLI paths end-to-end.

## Install

```bash
git clone https://github.com/Jo2234/finance-labs.git
cd finance-labs/labs/guidance-drift
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Input format

CSV columns:

| column | meaning |
| --- | --- |
| `company` | company name |
| `quarter` | period label such as `2026-Q2` |
| `revenue_growth` | decimal revenue growth, e.g. `-0.12` for -12% |
| `margin_change_bps` | margin change in basis points |
| `guidance_change` | decimal guidance revision, e.g. `-0.07` |
| `transcript` | management commentary text |

A fully offline example is included at `examples/sample_guidance.csv`.

## Usage

Markdown report:

```bash
python -m guidance_drift_lab analyze examples/sample_guidance.csv --format markdown
```

Output:

```markdown
# Guidance Drift Report: Northstar Semis

Northstar Semis shows high positive-language drift in 2026-Q2 (drift=0.688), making it the quarter most worth analyst review.

| Quarter | Drift | Label | Tone | Fundamentals |
| --- | ---: | --- | ---: | ---: |
| 2026-Q2 | 0.688 | high positive-language drift | 0.571 | -0.804 |
| 2026-Q1 | 0.022 | low drift | 0.400 | 0.357 |
| 2026-Q3 | 0.003 | low drift | 0.000 | -0.007 |
```

JSON for downstream tools:

```bash
python -m guidance_drift_lab analyze examples/sample_guidance.csv --format json
```

Write a report file:

```bash
guidance-drift analyze examples/sample_guidance.csv --format markdown --output report.md
```

## Input validation

Each input file must contain exactly one company, and every row must supply its nonempty company name. Surrounding whitespace is trimmed; names otherwise must match exactly. Split multi-company exports before analysis so one issuer’s quarters cannot be attributed to another.

## Methodology

Guidance Drift Lab computes:

1. **Sentiment score** from a small transparent finance-oriented lexicon.
2. **Fundamental score** from revenue growth, margin change in basis points, and guidance revision.
3. **Drift score** as the positive gap between language and fundamentals, normalized to `[0, 1]`.

High drift means positive language is materially ahead of deteriorating fundamentals. This does **not** mean a stock is a short or a buy; it means the quarter is worth closer review.

## Development

```bash
pytest -q
python -m build
python -m guidance_drift_lab analyze examples/sample_guidance.csv --format json
```

## Project status

- ✅ Offline sample dataset
- ✅ Tested scoring logic and CLI behavior
- ✅ GitHub Actions CI
- ✅ No secrets, paid APIs, or live scraping

## Disclaimer

Not investment advice. This is a research and engineering demo for analyst triage.
