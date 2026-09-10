# Microstructure Stress Lab

Microstructure Stress Lab is a small, explainable Python CLI for turning an offline OHLCV + quote/depth tape into a liquidity-risk report. It is designed for portfolio managers, execution desks, and market-structure researchers who want a fast sanity check before sending orders into a stressed tape.

## Why it matters

Price charts often hide the real execution problem: spreads widen, one side of the book becomes crowded, and volume arrives in bursts. This project packages four transparent microstructure signals into a bounded 0-100 stress score so a desk can quickly decide whether to slow down execution, review news, or keep normal routing.

No paid APIs, credentials, or live scraping are required. The included sample data is synthetic and fully offline, making the project safe to run in CI and easy to adapt to proprietary internal tapes.

## Features

- Computes quoted spread in basis points from bid/ask quotes.
- Computes signed top-of-book depth imbalance from bid/ask sizes.
- Computes Amihud-style `|return| / dollar volume` illiquidity.
- Detects latest-bar volume shock versus the prior tape average.
- Produces JSON for automation or Markdown for human-readable desk notes.
- Includes tests, packaging metadata, and GitHub Actions CI.

## Quickstart

```bash
git clone https://github.com/Jo2234/finance-labs.git
cd finance-labs/labs/microstructure-stress
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Run the demo report:

```bash
microstress examples/stressed_tape.csv --format markdown --title "Opening Auction Liquidity Stress"
```

Example output:

```markdown
# Opening Auction Liquidity Stress

Source: `examples/stressed_tape.csv`
Latest timestamp: **2026-01-02T09:34:00**

## Stress snapshot

- Stress score: **47.30/100** (`watch`)
- Latest close: **98.9500**
- Quoted spread: **30.32 bps**
- Volume shock: **3.22x** prior average
- Order-book imbalance: **0.55** (-1 ask-heavy, +1 bid-heavy)
- Amihud illiquidity: **1.495e-08**

## Desk actions

- Route orders with tighter participation caps; quoted spread is wide versus normal liquid conditions.
- Check news and auction calendars; latest volume is materially above the prior tape average.
- Monitor bid-side depth concentration; book pressure is meaningfully one-sided.
```

JSON mode is useful for pipelines:

```bash
microstress examples/stressed_tape.csv --format json
```

```json
{
  "amihud_illiquidity": 1.495155171218192e-08,
  "latest_close": 98.95,
  "latest_spread_bps": 30.318342597271066,
  "latest_timestamp": "2026-01-02T09:34:00",
  "observations": 5,
  "order_book_imbalance": 0.55,
  "recommendations": [
    "Route orders with tighter participation caps; quoted spread is wide versus normal liquid conditions.",
    "Check news and auction calendars; latest volume is materially above the prior tape average.",
    "Monitor bid-side depth concentration; book pressure is meaningfully one-sided."
  ],
  "source": "examples/stressed_tape.csv",
  "stress_label": "watch",
  "stress_score": 47.3,
  "volume_shock": 3.2248062015503876
}
```

## Input schema

CSV files must include these columns:

| Column | Meaning |
| --- | --- |
| `timestamp` | Bar timestamp or event label |
| `close` | Last/close price for the interval |
| `volume` | Interval traded volume |
| `bid` / `ask` | Latest top-of-book quote |
| `bid_size` / `ask_size` | Top-of-book depth on each side |

## Input validation

All numeric CSV fields must be finite. `NaN` and infinity in any row are data errors, including historical quote/depth fields; the CLI fails instead of assigning a stress label. The public metric and scoring functions also reject non-finite inputs.

## Methodology

The score is deliberately simple and auditable:

- **Spread component:** up to 30 points, saturating at 60 bps.
- **Volume shock component:** up to 25 points, saturating at 4x prior average volume.
- **Amihud component:** up to 25 points, saturating at `1e-7` absolute return per dollar traded.
- **Book imbalance component:** up to 15 points from absolute signed depth imbalance.

Labels are assigned from the final 0-100 score:

| Score | Label |
| --- | --- |
| `< 30` | `calm` |
| `30-54.99` | `watch` |
| `55-79.99` | `elevated` |
| `>= 80` | `severe` |

This is not a prediction model or investment recommendation. It is a triage tool for execution-risk monitoring.

## Development

```bash
python -m pip install -e . pytest build
python -m pytest tests -q
python -m build
```

The test suite covers metric reference values, invalid quotes, CSV analysis, Markdown rendering, and CLI smoke tests.

## License

MIT
