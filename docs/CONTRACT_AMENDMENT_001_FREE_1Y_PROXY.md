# Contract Amendment 001 - Free One-Year RFR Proxy

Status: frozen before Phase 02 outcome access
Frozen on: 2026-09-06
Reason: Phase 01 source availability only; no registered FX outcome was read

## Preserved result

The Phase 00 six-month Tier A expectation specification remains registered and
is `NOT_TESTED`. This amendment does not relabel an EIOPA curve as OIS, futures,
or a pure market expectation.

## New research namespace

All amended hypotheses use suffix `_P1Y` and the expectation kind
`EIOPA_RFR_1Y_PROXY`. They answer whether relative macro pressure and changes in
a published one-year regulatory risk-free curve have policy and FX information.

The amended causal chain is:

```text
point-in-time macro state
    -> six-month realized-policy reaction model
    -> compare predicted policy change with one-year EIOPA RFR minus policy rate
    -> predict next-month change in that one-year proxy gap
    -> freeze currency pressure
    -> evaluate next-month FX direction
```

## Source-driven sample change

- Macro panel snapshots: 2015-02 through 2022-12.
- Proxy observations: 2016-01 through 2022-12 after the publication lag.
- Training-only warm-up: 2015-02 through 2020-12.
- Pseudo-out-of-sample evaluation: 2021-01 through 2022-12.
- Label support may read policy/proxy data through 2023-06 only.
- Registered 2019-2024 Tier A evaluation remains untouched and `NOT_TESTED`.
- Data from 2025 onward remains sealed.

The later start is required by the EIOPA archive and the free macro vintages.
The earlier end avoids silently bridging the retired Euro-area OECD vintage
series with current revised history. This leaves only 24 primary evaluation
months and materially limits statistical power.

## Proxy definitions

For currency `c` and month-end snapshot `t`:

```text
proxy_path_1y_bp[c,t]
    = 100 * (EIOPA_RFR_1Y_percent[c,t] - policy_rate_percent[c,t])

pricing_gap_proxy_bp[c,t]
    = structural_policy_change_6m_bp[c,t] - proxy_path_1y_bp[c,t]

proxy_repricing_1m_bp[c,t]
    = proxy_path_1y_bp[c,t+1m] - proxy_path_1y_bp[c,t]
```

An EIOPA curve becomes eligible only at the next monthly snapshot after its
reference month. This conservative one-month lag prevents migrated archive
metadata or same-date assumptions from creating look-ahead.

The source instrument (`OIS`, `SWP`, or other workbook identifier) remains a
visible field. Mixed instrument types are a mandatory robustness flag.

## Macro amendment

Some free cross-country sources publish inflation rates rather than consistent
seasonally adjusted price indices. The amended, declared momentum is:

```text
underlying_momentum_raw = underlying_yoy_t - underlying_yoy_t_minus_3_months
```

For quarterly Australia/New Zealand underlying series, the lag is one release.
For index sources, year-over-year inflation is calculated from the point-in-time
index values first. No series definition may change after inspecting outcomes.

At each snapshot, standardization uses the historical reference-period feature
values visible in that selected vintage, never a later vintage. At least 36
earlier reference-period values are required. This permits a valid state at the
first archived vintage when that vintage already contains a long past history;
it does not manufacture forecasts dated before the archive existed.

The free-data namespace reduces the primary model minimum from the original 60
to 36 eligible months per currency and from 600 to 360 pooled rows. A 12-month,
120-row warm-up fit may produce the upstream structural feature needed to train
the proxy model, but warm-up predictions never enter `FB_H1` evaluation. This
change is source-driven, frozen before outcomes, and weakens the evidence.

## Amended hypothesis IDs

- `FB_H1_POLICY_SKILL_P1Y`: unchanged realized-policy target and original gate.
- `FB_H2_PROXY_REPRICING_SKILL_P1Y`: beats no-change and proxy-momentum
  benchmarks in MAE with positive 95% paired block-bootstrap improvements.
- `FB_H3_PAIR_DIRECTION_P1Y`: positive pair-return coefficient with a wholly
  positive 95% month-block interval.
- `FB_H4_RANK_IC_P1Y`: positive mean monthly rank IC with a wholly positive
  95% interval.
- `FB_H5_EXTREME_SPREAD_P1Y`: positive top-two minus bottom-two return with a
  wholly positive 95% interval.
- `FB_H6_STABILITY_P1Y`: expected positive signs in 2021 and 2022 separately
  and in every leave-one-currency-out run.

The model families, label purging, past-only fitting, non-negative structural
macro slopes, FX isolation through Phase 03, block length 3, 10,000 bootstrap
resamples, and seed `20260906` remain unchanged.

## Amended Phase 05 gate

The strongest possible decision in this free-proxy namespace is
`PROCEED_TO_TECHNICAL_TIMING_RESEARCH_P1Y_PROXY`, never the original Tier A
decision. It requires all amended H1-H6 conditions, point-in-time/provenance
quality, full G10 coverage, and explicit non-executable FX marks.

Any mandatory `FAIL`, `NOT_SUPPORTED`, or `NOT_TESTED` produces
`DO_NOT_PROCEED_WITH_P1Y_PROXY_SPECIFICATION`.
