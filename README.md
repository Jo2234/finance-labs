# finance-labs

A systematic toolkit of small, offline, test-covered risk and market-structure diagnostics.

## Labs

Every lab is an independent Python project with its own package metadata, source package, tests, examples, and README. Commands below run from the repository root without installing the package.

| Lab | What it answers | Run it |
| --- | --- | --- |
| [Prompt Firewall](labs/prompt-firewall/) | Does an LLM transcript contain instruction overrides, secret-exfiltration requests, encoded payloads, untrusted endpoints, or tool-abuse attempts? | `PYTHONPATH=labs/prompt-firewall/src python3 -m promptfirewall_lab labs/prompt-firewall/examples/adversarial_conversation.json --format markdown` |
| [ETF Liquidity](labs/etf-liquidity/) | Can stressed underlying liquidity and AP capacity absorb an ETF redemption, and what NAV discount could the gap imply? | `PYTHONPATH=labs/etf-liquidity/src python3 -m etf_liquidity_stress_lab stress labs/etf-liquidity/examples/sample_holdings.csv --aum 2500000000 --redemption-pct 0.12 --ap-capacity 160000000 --market-depth 0.70` |
| [Margin Cascade](labs/margin-cascade/) | Does an initial asset shock trigger margin calls, forced sales, price impact, and secondary fund stress? | `PYTHONPATH=labs/margin-cascade/src python3 -m margin_cascade_lab --book labs/margin-cascade/examples/sample_book.csv --shock ALPHA=-0.22 --shock GAMMA=-0.08 --format markdown` |
| [Factor Crowding](labs/factor-crowding/) | Where is a portfolio concentrated by factor, co-movement, and estimated crowded-unwind loss? | `PYTHONPATH=labs/factor-crowding/src python3 -m factor_crowding_radar analyze labs/factor-crowding/examples/sample_portfolio.json --shock-bps 425 --format markdown` |
| [Bond Auction Tail](labs/bond-auction-tail/) | Does a Treasury auction's tail, bid-to-cover, indirect participation, and dealer takedown indicate demand stress? | `PYTHONPATH=labs/bond-auction-tail/src python3 -m bond_auction_tail_monitor labs/bond-auction-tail/examples/sample_auctions.csv --latest-only` |
| [Options Skew](labs/options-skew/) | How steep are the put and call wings, and does their term structure indicate elevated tail-hedging demand? | `PYTHONPATH=labs/options-skew/src python3 -m options_skew_sentinel analyze labs/options-skew/examples/spy_option_chain_sample.csv` |
| [Covenant Headroom](labs/covenant-headroom/) | How close is a borrower to leverage, coverage, or liquidity breaches under explicit downside scenarios? | `PYTHONPATH=labs/covenant-headroom/src python3 -m covenant_headroom_lab analyze labs/covenant-headroom/examples/sample_financials.csv --max-net-leverage 4.5 --min-interest-coverage 2.0 --min-liquidity 25 --scenario hard-landing:-20:15:-10` |
| [Guidance Drift](labs/guidance-drift/) | Where does optimistic earnings commentary diverge from weakening growth, margins, or guidance revisions? | `PYTHONPATH=labs/guidance-drift/src python3 -m guidance_drift_lab analyze labs/guidance-drift/examples/sample_guidance.csv --format markdown` |
| [Microstructure Stress](labs/microstructure-stress/) | Do spread, volume shock, Amihud illiquidity, and order-book imbalance point to stressed execution conditions? | `PYTHONPATH=labs/microstructure-stress/src python3 -m microstress labs/microstructure-stress/examples/stressed_tape.csv --format markdown` |
| [Central Bank Path](labs/central-bank-path/) | What policy path do rate futures imply per meeting, and does the macro picture support it? | `PYTHONPATH=labs/central-bank-path/src python3 -m cbpathlab analyze labs/central-bank-path/data/sample_path.csv --current-rate 5.35 --neutral-rate 3.25` |

## Testing

Install `pytest`, then run a lab from its directory so its local `pyproject.toml` controls test discovery:

```bash
cd labs/margin-cascade
PYTHONPATH=src python3 -m pytest -q
```

The shared GitHub Actions workflow runs this pattern for every lab on Python 3.10 and 3.12.

## License

MIT

