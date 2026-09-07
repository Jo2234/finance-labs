# Factor Crowding Radar Report

## Executive summary

- **Risk level:** High
- **Crowding score:** 85/100
- **Top factor:** AI Infrastructure (56.0%)
- **Top-factor dollar-pair correlation:** 1.00
- **Factor concentration HHI:** 0.36
- **Unwind stress loss:** -4.74%

## Factor exposures

| Factor | Portfolio weight |
| --- | ---: |
| AI Infrastructure | 56.0% |
| Rates Hedge | 13.0% |
| Defensive Value | 12.0% |
| Quality Growth | 11.0% |
| Cash | 8.0% |

## Alerts

- AI Infrastructure holds 56.0% of portfolio weight; single-factor exit liquidity may dominate risk.
- Top-factor dollar-pair correlation is 1.00; the sleeve has concentrated co-movement.
- Correlation breadth is 48.7%; this share of dollar pairs shares a factor or correlated return paths.
- Modeled unwind stress loss is -4.74%, large enough to merit desk-level review.

## Methodology

- Aggregates gross portfolio weight by declared factor bucket.
- Computes normalized factor HHI to quantify concentration.
- Measures correlation between two independently sampled dollars within the top factor, including self-pairs; zero-variance returns contribute zero correlation.
- Breadth is the probability that two independently sampled portfolio dollars share a factor or return correlation of at least 0.65; it is bounded by 1 and unchanged by splitting identical exposure into rows.
- Applies a basis-point unwind shock to the top factor sleeve with correlation amplification.

> This is an offline research/risk-screening tool, not investment advice. Validate inputs and assumptions before using it in production.
