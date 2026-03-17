# Options Skew Sentinel

Options Skew Sentinel is a small, auditable Python CLI for turning an option-chain CSV into a practical implied-volatility skew report. It estimates Black-Scholes implied volatility for put and call wings, compares the wings through a risk-reversal lens, and flags whether the chain is showing normal, watch, elevated, or extreme tail-hedging pressure.

This is designed as a portfolio-quality quant tooling project: no paid APIs, no hidden data, no black-box service dependency, and enough tests to make the analytics trustworthy.

## Why it matters

Index and single-name option skew often changes before the narrative does. A steep put wing can indicate demand for crash protection; a rising put-wing term structure can show that hedging demand is persistent rather than just a one-expiry artifact. This tool compresses those signals into a reproducible report that can be checked into research notes or CI-generated market dashboards.

## Features

- Black-Scholes call/put pricing implemented with the Python standard library.
- Robust bisection implied-volatility solver with intrinsic-value validation.
- Option-chain CSV analyzer grouped by expiry.
- Put-wing vs call-wing risk reversal metrics.
- Term-structure slope from near to far put-wing IV.
- Human-readable markdown report and machine-readable JSON export.
- CLI entry point (`skew-sentinel`) plus `python -m options_skew_sentinel` support.
- Meaningful pytest suite and GitHub Actions CI.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . pytest
pytest -q

skew-sentinel analyze examples/spy_option_chain_sample.csv \
  --json-out reports/spy_skew.json \
  --markdown-out reports/spy_skew.md
```

You can also run without installing the console script:

```bash
PYTHONPATH=src python -m options_skew_sentinel analyze examples/spy_option_chain_sample.csv
```

Example output:

```text
SPY options skew: ELEVATED — SPY options skew is elevated: left-tail hedge demand, with implied volatility rising across expiries.
  2026-08-21: put IV 27.3%, call IV 19.9%, Risk reversal -7.4%
  2026-09-18: put IV 29.4%, call IV 18.8%, Risk reversal -10.6%
  2026-10-16: put IV 32.9%, call IV 19.8%, Risk reversal -13.1%
```

## CSV input format

Required columns:

| Column | Meaning |
|---|---|
| `symbol` | Underlying ticker or instrument label |
| `expiry` | Expiry date or label |
| `option_type` | `call` or `put` |
| `strike` | Option strike |
| `mid` | Option mid price |
| `spot` | Underlying spot price |
| `rate` | Annualized risk-free rate, e.g. `0.04` |
| `days_to_expiry` | Calendar days until expiry |

The included file `examples/spy_option_chain_sample.csv` is synthetic demonstration data, intentionally committed so the project runs offline.

## Methodology

For each expiry, the analyzer selects a put wing near 93% moneyness and a call wing near 107% moneyness when available. It then solves implied volatility from the observed mid price using Black-Scholes and computes:

- **Risk reversal** = call-wing IV minus put-wing IV. Negative values indicate stronger left-tail hedge demand.
- **Skew ratio** = put-wing IV divided by call-wing IV.
- **Term-structure slope** = far-expiry put-wing IV minus near-expiry put-wing IV.
- **Alert level** from the combined magnitude of average risk reversal and positive term slope.

The model is intentionally simple and transparent. It is not a trading recommendation, an American-options pricer, or a replacement for market microstructure checks.

## Example markdown report

Running the quickstart writes a report like:

```markdown
# SPY Options Skew Sentinel Report

**Headline:** SPY options skew is elevated: left-tail hedge demand, with implied volatility rising across expiries.

| Expiry | DTE | Put strike | Put wing IV | Call strike | Call wing IV | Risk reversal | Skew ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-21 | 45 | 390.00 | 27.30% | 450.00 | 19.91% | -7.39% | 1.37 |
```

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . pytest
pytest -q
python -m options_skew_sentinel analyze examples/spy_option_chain_sample.csv
```

## Disclaimer

This repository is for research and education. It uses simplified European option assumptions and synthetic sample data. It does not provide financial advice.
