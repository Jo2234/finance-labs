# Factor Crowding Radar

Offline Python CLI for spotting crowded factor trades before the unwind becomes obvious.

A portfolio can look diversified by ticker count while still being one consensus trade in disguise: same AI infrastructure beta, same liquidity window, same de-risking trigger. **Factor Crowding Radar** turns a simple JSON position file into a reproducible crowding report with factor exposure, concentration, co-movement, and stress-loss estimates.

## Why it matters

Crowding risk is rarely visible from headline weights alone. This project gives risk managers, PMs, and research analysts a lightweight way to answer:

- Which factor sleeve dominates the book?
- Are positions moving together strongly enough to create exit-liquidity risk?
- How large is the modeled loss if the top factor suffers a fast unwind?
- What alerts should be reviewed before adding more exposure?

It is intentionally offline and uses no paid APIs, secrets, or scraping. Bring your own clean portfolio/return history and keep the analysis reproducible.

## Features

- **Factor exposure aggregation** from a JSON portfolio file.
- **HHI concentration score** for factor-level crowding.
- **Exposure-weighted correlation** across the top factor sleeve.
- **Correlation breadth** to highlight positions with shared return paths.
- **Unwind stress model** that applies a configurable basis-point shock to the top factor.
- **JSON or Markdown reports** for CI artifacts, notebooks, risk memos, or pull requests.
- **Strict local tests and GitHub Actions CI**.

## Quickstart

```bash
git clone https://github.com/Jo2234/finance-labs.git
cd finance-labs/labs/factor-crowding
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

factor-crowding-radar analyze examples/sample_portfolio.json --shock-bps 425 --format markdown --output report.md
```

Expected summary:

```text
High crowding risk | score=85/100 | top_factor=AI Infrastructure (56.0%) | unwind_loss=-4.74%
```

## Example report excerpt

```markdown
# Factor Crowding Radar Report

## Executive summary

- **Risk level:** High
- **Crowding score:** 85/100
- **Top factor:** AI Infrastructure (56.0%)
- **Top-factor dollar-pair correlation:** 1.00
- **Factor concentration HHI:** 0.36
- **Unwind stress loss:** -4.74%
```

Full sample output lives at [`examples/sample_report.md`](examples/sample_report.md).

## Input format

```json
{
  "positions": [
    {
      "name": "NVDA proxy",
      "weight": 0.22,
      "factor": "AI Infrastructure",
      "returns": [0.018, 0.025, -0.021, 0.030]
    }
  ]
}
```

Rules:

- weights must be non-negative and sum to approximately `1.0`;
- every position needs the same number of return observations;
- returns should be decimal returns (`0.01` = 1%);
- factors are analyst-defined buckets, not inferred labels.

## Methodology

The crowding score is designed as a transparent risk screen rather than a black-box model:

1. Aggregate gross portfolio weight by declared factor.
2. Compute factor HHI to capture concentration.
3. Identify the top factor sleeve and compute the average correlation of two independently sampled dollars within it. Sampling is with replacement: self-pairs are included, with zero correlation for zero-variance returns. Pair weights are products of normalized position weights.
4. Breadth is the probability that two independently sampled portfolio dollars share a factor or have return correlation at least 0.65. It includes self-pairs, ranges from zero to one, and counts exposure through dollar-pair probabilities rather than adding the same position weight repeatedly.
5. Apply a configurable shock to the top factor and amplify it when correlations/breadth are high.
6. Convert the components into a 0-100 score and qualitative risk level.

Both correlation and breadth are unchanged when a position is split into rows with the same factor and return history. Weights accepted within the input tolerance are normalized before calculating metrics. For two uncorrelated factor sleeves weighted 60%/40%, breadth is `0.6² + 0.4² = 0.52`; for a completely shared factor it is one regardless of row count. A singleton top factor has correlation one with itself unless its returns are constant, so this measure describes exposure co-movement rather than independent evidence from multiple names.

The score retains contributions of 45 × top-factor weight, 35 × factor HHI, 35 × nonnegative top-factor correlation, and 25 × breadth, capped at 100. Low/Moderate/Elevated/High boundaries remain 30/50/75; these are screening heuristics, not calibrated probabilities. Bounding breadth limits its contribution to 25 points and caps correlation amplification at 2.25×. The included sample now scores 85/100 with a 4.74% modeled loss under a 425 bp shock.

This is not investment advice. The output should be treated as a triage layer for deeper portfolio review.

## CLI reference

```bash
factor-crowding-radar analyze INPUT.json \
  --shock-bps 350 \
  --format json \
  --output report.json
```

Options:

- `--shock-bps`: top-factor shock in basis points, default `350`.
- `--format`: `json` or `markdown`, default `json`.
- `--output`: optional path to write the full report. A one-line summary is printed to stdout when writing a file. Without `--output`, JSON mode reserves stdout for the JSON document and prints the summary to stderr.

You can also run without installing by setting `PYTHONPATH=src`:

```bash
PYTHONPATH=src python -m factor_crowding_radar analyze examples/sample_portfolio.json --format json
```

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e . pytest build
pytest tests -q
python -m build
```

## Project structure

```text
src/factor_crowding_radar/   core analytics and CLI
tests/                       TDD coverage for math, validation, and CLI smoke path
examples/                    offline sample portfolio and generated report
.github/workflows/ci.yml     GitHub Actions test matrix
```

## License

MIT
