# Release notes

## v0.1.0 — 2026-09-11

First versioned release of the ten-lab collection: Prompt Firewall, ETF Liquidity, Margin Cascade, Factor Crowding, Bond Auction Tail, Options Skew, Covenant Headroom, Guidance Drift, Microstructure Stress, and Central Bank Path.

- Each lab has an independently installable Python 3.10+ wheel and source distribution. Runtime dependencies are empty; no API keys or network services are required.
- Bundled synthetic inputs and documented CLI commands make the output reproducible. Release validation runs all lab tests and executes all ten examples against installed wheels.
- Distributions carry the MIT license; source distributions include their example inputs. The release includes captured validation output and SHA-256 checksums.

This version names the current toolkit snapshot; it does not introduce new financial models or claim measured investment performance. Heuristic scores and scenario assumptions are explained in each lab's README. The Prompt Firewall is a diagnostic heuristic, not a security boundary. The toolkit has no graphical interface or unified root package.
