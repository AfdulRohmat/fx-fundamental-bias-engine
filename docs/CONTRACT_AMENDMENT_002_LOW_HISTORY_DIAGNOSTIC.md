# Contract Amendment 002 - Low-history diagnostic

Status: frozen before Phase 04 FX outcome parsing
Frozen on: 2026-09-06
Reason: Phase 03 sample flow only; no ECB return was calculated or inspected

The primary 36-month/360-row proxy-repricing threshold remains unchanged.
Phase 03 showed that the free panel provides only 323 eligible training rows by
the last origin, so the primary repricing model is `NOT_TESTED`.

To avoid ending the engineering exercise without learning anything about the
downstream mechanism, an explicitly exploratory model may use the already
registered structural warm-up thresholds: 12 months per currency and 120
pooled rows. It uses the same predictors, ridge grid, purging, and penalty
selection as the primary model.

Outputs are named `proxy_prediction_exploratory_bp`. Phase 04 may calculate
descriptive FX diagnostics from them, but `FB_H2` through `FB_H6` remain
`NOT_TESTED`; this amendment cannot satisfy or weaken any Phase 05 gate.
