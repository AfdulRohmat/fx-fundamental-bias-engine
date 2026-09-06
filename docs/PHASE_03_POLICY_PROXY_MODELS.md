# Phase 03 - Policy and proxy-repricing models

Status: `REVIEW_REQUIRED`

Registered hypotheses:

- `FB_H1_POLICY_SKILL_P1Y`: `NOT_TESTED`
- `FB_H2_PROXY_REPRICING_SKILL_P1Y`: `NOT_TESTED`

The status is not a synonym for no computation. Every eligible fold was fit,
purged, and persisted; the registered claims cannot be adjudicated because the
Phase 02 full-coverage gate failed and the primary repricing model never
reached 36 months per currency / 360 pooled rows.

## Structural-policy diagnostic

Across 182 eligible rows and 19 evaluation months, the constrained macro model
had MAE 74.53 bp versus 107.09 bp for no change and 96.32 bp for the
equal-weight macro benchmark. The paired block-bootstrap improvement intervals
were wholly positive: 10.99 to 55.51 bp versus no change and 7.02 to 38.09 bp
versus equal weight.

This is promising evidence that inflation and labour variables can describe
the subsequent six-month policy path. It is not promoted to `SUPPORTED`
because the registered source/sample contract did not pass.

## One-year proxy-repricing diagnostic

The primary model produced zero predictions because its minimum sample was not
reached. Amendment 002, frozen before parsing returns, allowed a low-history
diagnostic with 212 rows and 22 months:

- model MAE: 19.59 bp;
- no-change MAE: 18.64 bp;
- trailing-momentum MAE: 27.51 bp;
- improvement interval versus no change: -2.73 to 0.85 bp;
- improvement interval versus momentum: 2.18 to 13.71 bp.

Thus the exploratory model clearly beat a poor momentum benchmark but did not
beat the stronger no-change benchmark. The repricing mechanism needed for a
tradeable fundamental bias is not supported by this diagnostic.

## Leakage controls

- Six-month policy labels enter training only after the full horizon elapsed.
- One-month proxy labels enter only after the next snapshot.
- Penalties are selected inside the past training window.
- Macro slopes are constrained non-negative; unconstrained coefficients are
  retained as diagnostics.
- Phase 03 reads no FX outcome and leaves 2025 onward sealed.
