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

## Interpretation flags

- market prices aggressive easing while unemployment is already elevated
- terminal expected rate remains materially above neutral
- easing path conflicts with still-sticky core inflation
- weak new orders make the path look like a growth-shock hedge

## Methodology

Fed Funds futures-style prices are converted as `100 - price`. Adjacent expected rates are compared meeting by meeting, and the expected bps move is divided by a 25 bp policy step to infer transparent one-step cut/hold/hike odds. The regime label combines the priced path with simple macro context; it is a diagnostic, not investment advice.
