# Margin Cascade Lab

**Margin Cascade Lab** is an offline Python CLI that stress-tests leveraged portfolios for margin-call feedback loops: initial shocks reduce asset values, weak funds are forced to liquidate, sales move market prices through a transparent depth model, and those price moves can stress other funds.

It is built for risk research, portfolio demos, and interview-ready quant engineering examples where the methodology should be easy to inspect and reproduce without paid APIs or live market credentials.

## Why it matters

Risk often becomes systemic through mechanics rather than narratives: leverage, margin thresholds, crowded holdings, and market depth. A single mark-to-market shock can become a cascade when funds sell the same assets into thin liquidity. This project turns that mechanism into a small, testable simulator that can be run from a CSV file.

## Features

- Dependency-free Python package with a console script: `margin-cascade`
- CSV portfolio book input: fund, asset, units, price, debt, market depth
- Repeatable asset shocks such as `ALPHA=-0.22`
- Pro-rata forced liquidation when a fund breaches maintenance margin
- Price impact based on sale value versus asset market depth
- JSON and Markdown reports
- Systemic risk score, most-stressed fund, final fund health, final prices, liquidation tape
- Unit and CLI tests plus GitHub Actions CI across Python 3.10, 3.11, and 3.12

## Quickstart

```bash
git clone https://github.com/Jo2234/margin-cascade-lab.git
cd margin-cascade-lab
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
margin-cascade --book examples/sample_book.csv \
  --shock ALPHA=-0.22 \
  --shock GAMMA=-0.08 \
  --format markdown
```

## Example output

The included sample book models four funds with shared exposures to ALPHA, BETA, GAMMA, and DELTA. A 22% shock to ALPHA and 8% shock to GAMMA produces a forced sale from the most levered fund and secondary price impact in shared assets:

```text
# Margin Cascade Report

- Rounds simulated: **2**
- Total forced liquidation: **$7,142**
- Systemic risk score: **41.35/100**
- Most stressed fund: **Beacon**

## Final fund health

| Fund | Assets | Debt | Equity | Margin | Leverage |
|---|---:|---:|---:|---:|---:|
| Atlas | $6,838 | $0 | $6,838 | 100.0% | 1.00x |
| Beacon | $7,031 | $5,058 | $1,974 | 28.1% | 3.56x |
| Meridian | $11,034 | $6,500 | $4,534 | 41.1% | 2.43x |
| Northstar | $11,258 | $7,800 | $3,458 | 30.7% | 3.26x |

## Final prices

| Asset | Initial | Final | Move |
|---|---:|---:|---:|
| ALPHA | 100.00 | 73.53 | -26.5% |
| BETA | 58.00 | 55.12 | -5.0% |
| GAMMA | 35.00 | 32.20 | -8.0% |
| DELTA | 25.00 | 25.00 | 0.0% |

## Liquidation tape

| Round | Fund | Asset | Sale value | Impact |
|---:|---|---|---:|---:|
| 1 | Beacon | ALPHA | $4,585 | 5.73% |
| 1 | Beacon | BETA | $2,557 | 4.97% |
```

## CSV schema

```csv
fund,asset,units,price,debt,market_depth
Beacon,ALPHA,120,100,12200,28000
Beacon,BETA,90,58,0,18000
```

- `fund`: portfolio or fund name
- `asset`: shared asset identifier
- `units`: long units held by the fund
- `price`: starting asset price
- `debt`: fund-level debt; if repeated on multiple rows for a fund, the simulator uses the largest value to avoid double-counting
- `market_depth`: approximate sale value needed for a 1 / impact_coefficient proportional impact unit; lower values make an asset more fragile

## Methodology

For each simulation:

1. Apply exogenous shocks to starting prices.
2. Compute each fund's gross asset value, debt, equity, margin ratio, and leverage.
3. If `equity / gross_assets` falls below the maintenance margin, sell a pro-rata slice of the fund's remaining assets.
4. Use sale proceeds to repay debt.
5. Aggregate forced sale value per asset and reduce prices using:

```text
price_impact = impact_coefficient * forced_sale_value / market_depth
new_price = old_price * (1 - price_impact)
```

6. Repeat until no fund breaches maintenance margin or `max_rounds` is reached.

This is a deliberately transparent stress model, not an execution-quality market simulator. It is meant to make assumptions visible and scenario comparisons repeatable.

## JSON output

```bash
margin-cascade --book examples/sample_book.csv \
  --shock ALPHA=-0.22 \
  --shock GAMMA=-0.08 \
  --format json \
  --output report.json
```

The JSON includes `scenario`, `rounds`, `final_prices`, `fund_summaries`, `events`, `total_liquidated_value`, `systemic_risk_score`, and `most_stressed_fund`.

## Development

```bash
python -m pip install -e . pytest build
pytest -q
python -m build
```

The project was developed test-first around the core engine behavior and CLI report path.

## License

MIT
