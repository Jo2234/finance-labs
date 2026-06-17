# ETF Liquidity Stress Lab

A small offline research CLI for testing **ETF liquidity illusion**: the gap between an ETF's easy-to-trade secondary-market wrapper and the stressed liquidity of its underlying basket.

The tool takes a holdings CSV, applies tiered ADV haircuts, compares the result with authorized participant (AP) creation/redemption capacity, and estimates whether a redemption shock is likely to create a material NAV discount.

## Why this matters

ETF liquidity is often quoted from the ETF's own trading volume, but in a real stress event the binding constraint can be:

- underlying constituent ADV after liquidity haircuts,
- AP balance-sheet capacity,
- wide spreads in thin basket names,
- multi-day liquidation pressure, and
- tracking buffers needed to compensate APs for inventory and execution risk.

This repo turns that intuition into a transparent, testable stress model that runs fully offline with no paid data or credentials.

## Features

- CSV-driven ETF basket stress tests
- Liquidity tier ADV haircuts: liquid, moderate, thin
- AP capacity vs underlying-capacity bottleneck analysis
- Estimated discount in basis points
- Risk labels: `contained`, `elevated`, `severe`
- Markdown and JSON output modes
- Tests for core math, validation, and CLI smoke path
- GitHub Actions CI

## Quickstart

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .

etf-liquidity-stress stress examples/sample_holdings.csv \
  --aum 2500000000 \
  --redemption-pct 0.12 \
  --ap-capacity 160000000 \
  --market-depth 0.70
```

Example output:

```markdown
# ETF Liquidity Stress Report

**Risk level:** SEVERE

| Metric | Value |
|---|---:|
| Redemption shock | $300.0M |
| Stressed underlying liquidity | $856.9M |
| AP daily capacity | $160.0M |
| Liquidity gap | $140.0M |
| Estimated discount | 369.8 bps |
| Liquidation days | 1.88 |
| Weighted spread | 31.9 bps |
| Thin-basket weight | 44.0% |
```

JSON mode is useful for pipelines:

```bash
etf-liquidity-stress stress examples/sample_holdings.csv \
  --aum 2500000000 --redemption-pct 0.12 --ap-capacity 160000000 \
  --market-depth 0.70 --json
```

## Holdings CSV format

```csv
ticker,weight,adv_usd,spread_bps,liquidity_tier
MEGACAP,0.22,2500000000,2.5,liquid
HY_BOND,0.20,75000000,55.0,thin
```

Columns:

- `ticker`: constituent symbol or instrument label
- `weight`: portfolio weight; all rows must sum to approximately 1.0
- `adv_usd`: average daily dollar volume of the constituent
- `spread_bps`: representative bid/ask spread in basis points
- `liquidity_tier`: `liquid`, `moderate`, or `thin`

## Methodology

1. **Underlying basket capacity**
   - Liquid constituents: 35% of ADV usable in a stress day
   - Moderate constituents: 20% of ADV usable
   - Thin constituents: 6% of ADV usable
   - The basket capacity is multiplied by the stress `--market-depth` parameter.

2. **Practical redemption capacity**
   - The daily redemption capacity is the smaller of stressed underlying basket liquidity and AP daily capacity.

3. **Discount estimate**
   - The model combines weighted spread, tracking buffer, liquidity gap ratio, thin-basket penalty, and liquidation-days penalty.
   - This is a transparent diagnostic estimate, not a market forecast.

4. **Risk classification**
   - `contained`: small/no capacity gap and modest expected discount
   - `elevated`: meaningful gap, thin-basket exposure, or wide discount
   - `severe`: large gap, multi-day liquidation pressure, or discount above 180 bps

## Development

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e . pytest
pytest -q
```

## Disclaimer

This is an educational research tool. It is not investment advice, a valuation model, or a substitute for live market/liquidity data and professional risk systems.
