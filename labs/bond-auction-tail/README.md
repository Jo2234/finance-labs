# Bond Auction Tail Monitor

A small, offline Python CLI for reading Treasury auction results and ranking auctions by **tail risk** and demand quality. It turns auction result CSVs into an analyst-friendly stress report using the same signals fixed-income desks watch after supply events: high-yield tail versus when-issued, bid-to-cover, indirect bidder participation, and dealer takedown.

## Why it matters

Treasury auctions are one of the cleanest real-time windows into duration demand. A large positive tail, weak bid-to-cover ratio, falling indirect demand, and elevated dealer takedown can suggest that investors required a concession to absorb supply. This project packages those micro-signals into a repeatable monitor that works fully offline with documented CSV inputs.

## Features

- Computes auction tail in basis points: `high_yield - when_issued_yield`.
- Builds per-tenor z-scores against recent history.
- Scores auctions from 0–100 and labels regimes as `orderly`, `watch`, or `strained`.
- Explains each score with human-readable drivers.
- Emits Markdown tables for research notes or JSON for downstream automation.
- Includes a synthetic sample dataset, tests, packaging, and GitHub Actions CI.

## Quickstart

```bash
git clone https://github.com/Jo2234/finance-labs.git
cd finance-labs/labs/bond-auction-tail
python -m venv .venv
source .venv/bin/activate
pip install -e .

bond-auction-tail-monitor examples/sample_auctions.csv --latest-only
```

Example output:

```markdown
# Bond Auction Tail Monitor Report

| Date | Tenor | Tail bp | Bid/Cover | Indirect % | Dealer % | Score | Regime | Drivers |
|---|---:|---:|---:|---:|---:|---:|---|---|
| 2026-04-10 | 10Y | 3.50 | 2.05 | 54.0 | 32.0 | 100 | strained | large positive tail, soft bid-to-cover, weak indirect demand, elevated dealer takedown |
| 2026-04-05 | 5Y | 0.20 | 2.47 | 66.0 | 16.0 | 10 | orderly | near-normal auction versus tenor history |
| 2026-04-15 | 30Y | -0.50 | 2.55 | 70.0 | 13.0 | 0 | orderly | firm bid-to-cover, strong indirect demand |
```

JSON output is available for automation:

```bash
bond-auction-tail-monitor examples/sample_auctions.csv --latest-only --format json
```

## CSV schema

The input CSV must include:

| Column | Meaning |
|---|---|
| `date` | Auction date, sortable as `YYYY-MM-DD` |
| `tenor` | Tenor bucket such as `2Y`, `5Y`, `10Y`, `30Y` |
| `high_yield` | Auction high yield in percent, e.g. `4.315` |
| `when_issued_yield` | When-issued yield in percent before the auction |
| `bid_to_cover` | Bid-to-cover ratio |
| `indirect_pct` | Indirect bidder allocation percentage |
| `direct_pct` | Direct bidder allocation percentage |
| `dealer_pct` | Dealer allocation percentage |

## Methodology

For each tenor, the tool compares the current auction with that tenor's trailing history:

1. **Tail pressure**: positive tails and high tail z-scores increase stress.
2. **Coverage**: low bid-to-cover ratios or weak z-scores increase stress.
3. **End-investor demand**: low indirect participation increases stress.
4. **Dealer absorption**: unusually high dealer takedown increases stress.
5. The final score is clipped to `0..100` and mapped to:
   - `0–39`: `orderly`
   - `40–69`: `watch`
   - `70–100`: `strained`

The sample data is synthetic and intentionally offline-friendly. It is not investment advice.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . pytest build
pytest -q
python -m build
```

## License

MIT
