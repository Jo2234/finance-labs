# Covenant Headroom Lab

Covenant Headroom Lab is an offline Python CLI for credit analysts, founders, and finance teams who want to pressure-test debt covenant cushion before a lender update, downside planning session, or portfolio review.

It turns a simple quarterly CSV into:

- base-case covenant pass/breach diagnostics;
- net leverage, interest coverage, and liquidity headroom;
- repeatable downside stress scenarios;
- JSON output for automation; and
- a Markdown credit memo suitable for a diligence folder.

## Why it matters

Public equity screens are everywhere, but private credit covenant monitoring is often still spreadsheet-heavy and hard to reproduce. This project demonstrates a compact, test-covered workflow for asking: **"How close is this borrower to tripping covenants if EBITDA falls, debt increases, or liquidity burns down?"**

It is intentionally offline: no paid API keys, no scraping, and no confidential borrower data required.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .

covenant-headroom analyze examples/sample_financials.csv \
  --max-net-leverage 4.5 \
  --min-interest-coverage 2.0 \
  --min-liquidity 25 \
  --scenario hard-landing:-20:15:-10 \
  --markdown-out covenant-report.md
```

The scenario format is:

```text
name:ebitda_shock_pct:net_debt_delta:liquidity_delta
```

For example, `hard-landing:-20:15:-10` means EBITDA falls 20%, net debt rises by $15m, and liquidity falls by $10m.

## Example output

```json
{
  "summary": {
    "base_breaches": 2,
    "periods": 4,
    "scenarios": 2,
    "tightest_headroom_period": "2026-Q4",
    "tightest_headroom_scenario": "hard-landing",
    "total_breaches": 6,
    "worst_net_leverage": 8.6184,
    "worst_net_leverage_period": "2026-Q4",
    "worst_net_leverage_scenario": "hard-landing"
  }
}
```

The Markdown report includes a covenant package summary, executive summary, methodology, and a period/scenario detail table.

## Input schema

CSV files must include these columns:

| Column | Meaning |
|---|---|
| `period` | Reporting period label, e.g. `2026-Q1` |
| `revenue` | Revenue in millions; carried for context |
| `adjusted_ebitda` | Covenant EBITDA in millions |
| `net_debt` | Debt minus cash in millions |
| `cash_interest` | Cash interest expense in millions |
| `liquidity` | Cash plus available revolver capacity in millions |

## Methodology

The core formulas are deliberately transparent:

- **Net leverage** = net debt / adjusted EBITDA. Breach if above maximum leverage.
- **Interest coverage** = adjusted EBITDA / cash interest. Breach if below minimum coverage.
- **Liquidity headroom** = liquidity - minimum liquidity. Breach if negative.
- **Headroom percentage** = absolute headroom divided by the relevant covenant threshold.

This is a screening model, not a substitute for reading the actual credit agreement. Real-world agreements can include cure rights, baskets, add-backs, step-downs, springing covenants, and issuer-specific definitions.

## Development

```bash
python -m pip install -e . pytest
pytest -q
python -m covenant_headroom_lab analyze examples/sample_financials.csv \
  --max-net-leverage 4.5 \
  --min-interest-coverage 2.0 \
  --min-liquidity 25 \
  --scenario hard-landing:-20:15:-10 \
  --markdown-out /tmp/covenant-report.md
```

## Project structure

```text
src/covenant_headroom_lab/  core analytics and CLI
tests/                       unit and CLI smoke tests
examples/sample_financials.csv sample offline borrower data
.github/workflows/ci.yml      GitHub Actions matrix CI
```

## Disclaimer

For educational and research use only. Not investment, accounting, legal, or lending advice.
