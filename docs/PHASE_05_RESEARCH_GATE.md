# Phase 05 - Fundamental Bias research gate

Decision: `DO_NOT_PROCEED_WITH_P1Y_PROXY_SPECIFICATION`

Only 2 of 8 mandatory gates passed. Phase 05 aggregates frozen outputs; it
does not refit a model, read a new outcome, change a sign, or relax a threshold.

## Gate result

| Gate | Result | Evidence |
|---|---|---|
| Point-in-time and provenance quality | Fail | Phase 02 `REVIEW_REQUIRED` |
| Full G10 evaluation coverage | Fail | 232/240 rows complete |
| `FB_H1_POLICY_SKILL_P1Y` | Fail closed | `NOT_TESTED` |
| `FB_H2_PROXY_REPRICING_SKILL_P1Y` | Fail closed | `NOT_TESTED` |
| At least two of H3-H5, including H3/H4 | Fail closed | all `NOT_TESTED` |
| `FB_H6_STABILITY_P1Y` | Fail closed | `NOT_TESTED` |
| FX limitations and no profit claim | Pass | non-executable marks declared |
| 2025+ remains sealed | Pass | no sealed access in Phases 02-04 |

## What the research actually learned

The project did not validate a deployable Fundamental Bias Engine. It did find
a narrower result worth preserving: the point-in-time inflation/labour model
described the next six-month policy path better than no change and an
equal-weight macro benchmark in the eligible diagnostic sample. Both paired
improvement intervals were positive.

The next bridge did not work. The low-history one-year-proxy model had higher
MAE than no change (19.59 versus 18.64 bp), and its improvement interval crossed
zero. When its frozen predictions were compared with next-month FX returns,
the pair slope, rank IC, and top-minus-bottom spread were all negative; every
interval crossed zero. These outputs are exploratory because the registered
sample minimum was not met.

Therefore the defensible conclusion is:

1. macro fundamentals show information about central-bank reaction;
2. this mixed-instrument EIOPA one-year curve is not a validated substitute for
   a market six-month policy-expectations series;
3. no evidence here supports using the resulting score as a next-month FX bias;
4. the negative diagnostic must not be inverted into a contrarian strategy.

## Research continuation boundary

Do not proceed to technical-entry or PnL work with this P1Y specification. A
future experiment needs a new contract and should first solve the measurement
problem: true point-in-time OIS/futures policy expectations, consistent G10
macro-release coverage, and enough history to satisfy the original training
minimum. After that, re-test repricing before opening FX outcomes.

The original registered Tier A six-month specification remains `NOT_TESTED`;
this proxy result does not reject it.
