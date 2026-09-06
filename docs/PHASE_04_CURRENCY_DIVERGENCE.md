# Phase 04 - Currency divergence

Status: `NOT_TESTED`

`FB_H3` through `FB_H6` cannot be registered tests because Phase 03 produced no
primary repricing pressure. The fixed FX transform was nevertheless run on the
pre-FX Amendment 002 low-history predictions as a non-gating diagnostic.

## Exploratory result

| Diagnostic | Estimate | 95% month-block interval |
|---|---:|---:|
| Pair-return slope per pressure bp | -0.000219 | -0.000586 to 0.000105 |
| Mean monthly G10 rank IC | -0.105 | -0.248 to 0.050 |
| Top-two minus bottom-two return | -41.6 bp/month | -158.1 to 56.6 bp |

The pair analysis contains 920 one-orientation pair-month rows over 22 months.
Only 16 months contain all ten currencies for the rank and extreme-spread
diagnostics. Every interval crosses zero, and all three point estimates have
the opposite sign from the hypothesis.

Sign stability also fails. Pair slope and rank IC are negative in both 2021
and 2022; the extreme spread is positive in 2021 but negative in 2022. Every
leave-one-currency-out pair slope, rank IC, and extreme-spread estimate is
negative.

## Interpretation boundary

This result does not prove that macro fundamentals are irrelevant to FX. It
shows that this specific chain—point-in-time macro state, a six-month policy
reaction estimate, and change in a mixed-instrument one-year EIOPA proxy—does
not deliver the expected next-month cross-sectional direction in the small
eligible sample.

ECB reference rates are synchronized month-end research marks. They are not
bid/ask quotes; no spread, slippage, financing, entry rule, position sizing, or
PnL is calculated.
