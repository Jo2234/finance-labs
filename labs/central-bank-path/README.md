# Central Bank Path Lab

Central Bank Path Lab is an offline Python CLI for auditing the policy path implied by interest-rate futures curves. It turns a simple meeting-date CSV into a transparent cut/hold/hike probability table, macro consistency flags, and a concise markdown or JSON report.

The project is intentionally small, reproducible, and credential-free: it ships with a sample Fed Funds-style path and does not call paid APIs or scrape live exchanges.

## Why it matters

Rate-cut narratives often compress several different questions into one headline: how much easing is priced, whether the terminal rate is still restrictive, and whether the macro story actually supports the curve. This tool separates those pieces:

- **Curve math:** converts futures-style prices (`100 - price`) and adjacent expected rates into meeting-level expected bps changes.
- **Decision odds:** maps each expected bps change to a transparent one-step 25 bp cut/hold/hike approximation.
- **Macro sanity checks:** flags cases where aggressive easing coexists with sticky inflation, elevated unemployment, weak orders, or a terminal rate still above neutral.
- **Portfolio workflow:** outputs markdown for research notes and JSON for downstream dashboards or agents.

## Quickstart

```bash
git clone https://github.com/Jo2234/finance-labs.git
cd finance-labs/labs/central-bank-path
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
cbpathlab analyze data/sample_path.csv --current-rate 5.35 --neutral-rate 3.25
```

## Example output

```markdown
# Central Bank Path Lab Report

**Regime:** hard-landing hedge
**Terminal expected rate:** 4.48%
**Total path change:** -87 bps
**Terminal gap to neutral:** 123 bps

## Meeting-implied path

| Meeting | Contract | Expected rate | Step change | Cut odds | Hold odds | Hike odds |
|---|---:|---:|---:|---:|---:|---:|
| 2026-03-18 | ZQH6 | 5.10% | -25 bps | 100% | 0% | 0% |
| 2026-05-06 | ZQK6 | 4.86% | -24 bps | 96% | 4% | 0% |
| 2026-06-17 | ZQM6 | 4.59% | -27 bps | 100% | 0% | 0% |
| 2026-07-29 | ZQN6 | 4.48% | -11 bps | 44% | 56% | 0% |
```

JSON is also available:

```bash
cbpathlab analyze data/sample_path.csv --current-rate 5.35 --neutral-rate 3.25 --format json
```

## Input format

The CSV needs one row per policy meeting:

```csv
date,contract,futures_price,expected_rate,core_pce_yoy,unemployment_rate,ism_new_orders
2026-03-18,ZQH6,94.90,5.10,3.1,4.8,46.0
2026-05-06,ZQK6,95.14,4.86,3.1,4.8,46.0
```

Columns:

- `date` — ISO date of the policy meeting, sorted chronologically.
- `contract` — optional futures contract label.
- `futures_price` — optional CME-style price; converted as `100 - price` when `expected_rate` is absent.
- `expected_rate` — market-implied expected policy rate after the meeting.
- `core_pce_yoy`, `unemployment_rate`, `ism_new_orders` — optional macro context used for interpretation flags.

## Input validation

All supplied rates and macro values must be finite numbers. Missing optional macro values may be left blank; `NaN` and infinity are rejected before odds or regime labels are calculated. Futures-only CSV rows use the same price validation as the Python conversion API.

## Methodology

1. Validate that meeting rows are chronological.
2. Convert futures-style prices to rates when needed: `implied_rate = 100 - futures_price`.
3. Calculate the adjacent expected policy-rate change for each meeting.
4. Divide the expected bps change by the policy step size, defaulting to 25 bps, to estimate one-step cut/hike odds. Odds are capped at 100% because the tool is a transparent diagnostic rather than a full options-implied distribution model.
5. Compare the terminal expected rate with a user-supplied neutral-rate estimate.
6. Add rule-based macro flags for path/story inconsistency.

This is not investment advice. It is a reproducible research aid for thinking about rates scenarios.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e . pytest build
python -m pytest -q
python -m build
```

CI runs the test suite, a CLI smoke test, and a package build on Python 3.10, 3.11, and 3.12.

## Repository layout

```text
src/cbpathlab/        Python package and CLI
tests/                Unit and CLI tests
data/sample_path.csv  Offline sample input
examples/             Generated sample markdown report
.github/workflows/    GitHub Actions CI
```

## License

MIT License. See [LICENSE](LICENSE).
