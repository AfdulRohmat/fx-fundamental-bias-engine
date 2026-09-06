# Technical Plan and Contract - Phase 00 through Phase 05

Status: Phase 00 baseline frozen; Phase 01 source decision pending
PRD: `FUNDAMENTAL_BIAS_ENGINE_PRD.md` v0.1

## 1. Separation from the completed event study

The Phase 01-11 artifacts and `DO_NOT_PROCEED` decision remain unchanged. This
contract registers a different question, sample unit, horizon, and mechanism.
No result from the old program is relabelled as evidence for this program.

The new namespace is `fundamental_bias`. New configuration, storage, artifacts,
modules, and hypothesis identifiers must not silently reuse event-study fields.

## 2. Shared invariants

- The target universe is USD, EUR, JPY, GBP, CHF, CAD, AUD, NZD, NOK, and SEK.
- All historical decisions are point-in-time and fail closed when
  `available_at` is missing or later than `as_of`.
- Observation period, publication time, retrieval time, and vintage time are
  separate fields.
- Revisions never overwrite earlier vintages.
- The primary research clock is one non-overlapping month-end snapshot.
- Weekly states are operational/secondary and cannot inflate primary N.
- Every standardizer and fitted model is trained on past data only.
- A six-month label is usable for a training origin only after the entire
  label horizon has elapsed.
- Structural macro weights are selected using policy outcomes only. Repricing
  weights are selected using policy-expectation outcomes only. Phase 04 cannot
  refit, select, or sign-flip either model using FX returns.
- An observed rate action is not treated as a surprise without a pre-action
  market expectation.
- 2019-2024 is the registered pseudo-out-of-sample evaluation window.
- Data from 2025 onward remains sealed.
- No phase through Phase 05 produces a trading strategy or PnL claim.

## 3. Canonical entities

### 3.1 `central_bank_profile`

Required fields:

```text
currency
country_code
central_bank_code
effective_from
effective_to
target_measure_id
underlying_inflation_measure_id
labour_measure_id
inflation_target_lower
inflation_target_midpoint
inflation_target_upper
mandate_notes
source_url
source_published_at
retrieved_at
source_sha256
```

Profile intervals must not overlap for one currency. A profile change is a new
row, never an overwrite.

### 3.2 `macro_vintage_observation`

Required fields:

```text
currency
country_code
indicator_id
reference_period
value
unit
seasonal_adjustment
available_at
vintage_at
retrieved_at
provider
source_url
source_sha256
```

Uniqueness is `(country_code, indicator_id, reference_period, vintage_at)`.

### 3.3 `policy_rate_observation`

Required fields:

```text
currency
central_bank_code
effective_at
available_at
rate_percent
provider
source_url
source_sha256
```

Policy decisions are non-revisable observations. Corrections remain separate
source records with provenance.

### 3.4 `fx_reference_rate`

Required fields:

```text
currency
quote_currency
observation_at
available_at
rate
provider
source_url
source_sha256
```

All derived crosses record both source-leg hashes and the exact algebra used.
Reference rates are research marks, not executable quotes.

### 3.5 `policy_expectation_observation`

Required fields:

```text
currency
central_bank_code
instrument_id
observation_at
available_at
horizon_months
implied_rate_percent
current_policy_rate_percent
implied_change_bp
expectation_kind
provider
source_url
source_sha256
```

`expectation_kind` distinguishes OIS/futures-implied paths from government-yield
proxies and published central-bank paths. Only an expectation kind qualified in
Phase 01 may enter the primary signal. A proxy must retain its proxy label in
every downstream artifact.

## 4. Source eligibility contract

A primary source passes only if Phase 01 demonstrates:

1. credential-free historical retrieval or a documented free registration;
2. stable identifiers and units;
3. sufficient G10 and historical coverage;
4. publication timing that can be reconstructed without future information;
5. revision/vintage behavior that is known and represented;
6. terms compatible with local research snapshots;
7. deterministic cached replay with SHA-256 provenance.

Current-value-only macro histories are ineligible for the primary panel when
the indicator is revised. They may be retained as a labelled sensitivity.

## 5. Snapshot contract

The primary snapshot is 17:00 `Europe/Brussels` on the final day in each month
for which the ECB publishes all required G10 reference-rate legs. This is a
conservative post-publication clock. The secondary weekly snapshot uses the
same local time on Friday, falling back only to the newest earlier observation
already published; it never reaches forward to Monday. Canonical storage uses
the corresponding timezone-aware UTC timestamp.

An observation labelled for month `m` but published after that snapshot is not
available in `m`. This applies to EIOPA curves and macro releases as well as FX
marks. There is no month-end-date imputation of publication time.

At snapshot `t`, the selector chooses the newest eligible vintage satisfying:

```text
available_at <= t
vintage_at <= t
reference_period <= t
```

No backfill, interpolation, or nearest-future observation is allowed. Missing
features make the corresponding country state incomplete.

The final common sample start remains unresolved because Phase 01 did not
qualify the registered six-month expectation source. The previously registered
2019 evaluation start cannot be moved until a versioned amendment explains the
source-driven reason without inspecting FX outcomes.

## 6. Feature definitions

For country `c` and snapshot `t`:

```text
inflation_gap_raw
    = target_measure_yoy - inflation_target_midpoint

inflation_momentum_raw
    = annualized_3m_underlying_inflation - underlying_inflation_yoy

labour_tightness_raw
    = -unemployment_rate

labour_momentum_raw
    = -(unemployment_rate_t - unemployment_rate_t_minus_3_releases)
```

Three-month annualized inflation uses log index changes when an index is
available:

```text
1200 * (log(index_t) - log(index_t_minus_3)) / 3
```

If the provider supplies only rates, any alternative computation must be
declared by indicator profile and cannot mix definitions within a currency.

Each raw feature becomes a country-local expanding z-score using only earlier
eligible snapshots. Minimum history is 36 monthly observations; sample
standard deviation uses `ddof=1`. Zero variance or insufficient history yields
missing, never zero.

## 7. State representations

### 7.1 Foundation: raw vector

The four-component vector and all raw inputs always remain visible.

### 7.2 Primary nonparametric benchmark: dominance

Inflation pressure is positive only when inflation gap and momentum are both
positive, and negative only when both are negative. Labour pressure follows
the same rule. A directional currency regime exists only when the inflation
and labour blocks agree. Conflicts produce `MIXED`.

No arithmetic magnitude is assigned to the labels.

### 7.3 Structural learned representation: policy pressure

The target is:

```text
y_6m[c,t] = 100 * (policy_rate[c,t+6m] - policy_rate[c,t])
```

in basis points. The three-month equivalent is secondary. The effective policy
rate at or before each endpoint is used; future meeting dates are not assumed.

Predictors are the four state z-scores plus frozen policy-smoothing terms. The
first implementation uses the current policy rate and trailing three-month
change as smoothing terms.

The primary estimator is pooled ridge regression with:

- one intercept per central bank;
- common G10 slopes for the four macro features;
- non-negative constraints on macro slopes;
- unpenalized country intercepts;
- a deterministic grid of ridge penalties;
- nested expanding-window selection by mean absolute policy-path error.

An unconstrained ridge fit is mandatory diagnostic output. A challenger with
shrunk country-specific slope deviations is allowed only if specified before
its outputs are inspected and cannot replace the primary result.

### 7.4 Primary learned representation: expected repricing

At each snapshot, define:

```text
pricing_gap_6m[c,t]
    = structural_policy_change_6m[c,t]
    - market_implied_policy_change_6m[c,t]

repricing_1m[c,t]
    = market_implied_policy_change_6m[c,t+1m]
    - market_implied_policy_change_6m[c,t]
```

The primary currency pressure is a walk-forward prediction of
`repricing_1m`. Predictors are the frozen four-component macro state,
`pricing_gap_6m`, current implied path, and trailing one-month path change. The
estimator is ridge with the same nested expanding-window discipline. Its
penalty is selected using repricing error only; FX prices remain unread.

The expected-repricing model is not allowed to infer forward guidance from
today's final policy action. New guidance is represented by its observable
effect on the policy-expectation path. Text-derived guidance is outside the
primary Phase 00-05 contract.

If no qualified free expectations source covers all G10 currencies, this layer
is `NOT_TESTED`. The actual-policy structural layer remains a reduced-scope
research result but cannot be promoted to the final bias claim.

## 8. Walk-forward and label-purge contract

For forecast origin `t` and horizon `h`, a row from origin `s` is trainable only
when:

```text
s + h <= t
```

The exact policy-rate endpoint must already be observable at `t`. Scaling,
missingness decisions, penalty selection, and coefficients are recomputed
inside the training window. Tests must prove that mutating any post-origin
input or label cannot change an earlier prediction.

Minimum primary training history is 60 eligible monthly observations per
included currency and 600 pooled country-month rows. Phase 03 reports a
prediction only when every G10 currency passes its per-currency minimum.

## 9. Phase 03 policy and expectations hypotheses

`FB_H1_POLICY_SKILL` is `SUPPORTED` only when, over 2019-2024:

- primary reaction-function MAE is below the no-change forecast MAE;
- primary MAE is below the equal-weight benchmark MAE; and
- the 95% date-block bootstrap interval for both paired MAE improvements is
  entirely positive when expressed as `benchmark_mae - model_mae`.

`FB_H1_POLICY_SKILL` is `NOT_SUPPORTED` if estimable but any condition fails,
and `NOT_TESTED` if the source/sample contract fails.

Secondary diagnostics include RMSE, direction accuracy conditional on a
nonzero rate change, calibration slope, per-bank loss, coefficient paths, and
three-month outcomes. They cannot replace the primary test.

`FB_H2_REPRICING_SKILL` is `SUPPORTED` only when, over 2019-2024:

- expected-repricing MAE is below a no-change-in-path forecast;
- expected-repricing MAE is below a path-momentum-only forecast; and
- the 95% date-block bootstrap interval for both paired MAE improvements is
  entirely positive when expressed as `benchmark_mae - model_mae`.

Directional accuracy, RMSE, calibration, and per-bank losses are secondary.
Missing qualified market expectations produces `NOT_TESTED`, not a fallback
claim based on realized policy rates.

## 10. Frozen Phase 04 FX transform

Structural and expected-repricing fold predictions are read-only inputs from
Phase 03.

Currency pressure is predicted one-month change in the market-implied
six-month policy path. Pair pressure is:

```text
pressure_pair[base/quote,t]
    = pressure_base[t] - pressure_quote[t]
```

FX returns are oriented so a positive return means base appreciation. Derived
currency basket returns use one fixed algebra across the sample. The primary
return runs from one month-end research mark to the next month-end research
mark and does not overlap.

Primary G10 ranking uses the top two and bottom two currencies by policy
pressure. Ties use currency code ascending only for deterministic reporting;
tied boundary members invalidate that month's extreme portfolio rather than
silently choosing a winner.

## 11. Phase 04 FX hypotheses

All intervals use a circular moving-block bootstrap over calendar-month date
clusters with block length 3, 10,000 resamples, and random seed `20260906`.
Currency or pair rows sharing a month stay in the same resampled cluster. These
parameters were frozen in Phase 01 before any registered FX outcome was read.

### `FB_H3_PAIR_DIRECTION`

Supported only when the pooled coefficient of next-month pair return on
base-minus-quote policy pressure is positive and its 95% interval is entirely
positive. One orientation per unordered pair is stored; inverse duplicates are
forbidden.

### `FB_H4_RANK_IC`

Supported only when the mean monthly Spearman rank correlation between G10
policy pressure and subsequent currency-basket return is positive and its 95%
interval is entirely positive.

### `FB_H5_EXTREME_SPREAD`

Supported only when the equal-weight top-two minus bottom-two next-month gross
return is positive and its 95% interval is entirely positive.

USDJPY estimates, five- and ten-business-day returns, dominance regimes, fixed
Taylor weights, and equal-weight signals are prespecified secondary results.

## 12. Robustness contract

The following are diagnostics and cannot replace the full evaluation:

1. fixed windows 2019-2021 and 2022-2024;
2. leave-one-currency-out estimates;
3. pandemic exclusion from 2020-03 through 2021-06;
4. current-vintage versus point-in-time sensitivity where both exist;
5. common-slope versus prespecified heterogeneous-slope challenger;
6. feature-block ablation: inflation only and labour only.

`FB_H6_STABILITY` is supported only when the primary H3 coefficient, H4 mean
IC, and H5 extreme-spread point estimates retain their expected positive sign
in both fixed chronological windows and every leave-one-currency-out run. This
is a sign-stability condition, not permission to ignore wide uncertainty.

## 13. Phase contracts

### Phase 00 - research reset and contract

- add the new PRD and technical contract;
- record literature implications and counter-evidence;
- add the candidate free-source plan;
- review the inflation/labour and expectations/forward-guidance video methods;
- initialize the independent repository and its documentation baseline.

No macro panel, model, or FX result is generated.

### Phase 01 - source qualification

- POC all candidate macro, market-expectation, policy-rate, mandate, and FX
  sources;
- audit coverage for every currency and feature;
- prove publication/vintage timestamp behavior;
- freeze snapshot clock, final common start date, and bootstrap parameters;
- emit `PASS`, `FAIL`, or `REVIEW_REQUIRED` for every source family.

No learned weighting model is fitted.

### Phase 02 - canonical G10 panel

- implement canonical schemas and adapters;
- build point-in-time selectors for macro, policy expectations, and features;
- emit weekly and primary monthly state panels;
- prove past-only invariance and sample flow;
- keep 2025 onward inaccessible to normal commands.

### Phase 03 - policy and repricing models

- implement frozen benchmarks, structural ridge, and expected-repricing ridge;
- emit every walk-forward fold and prediction;
- evaluate `FB_H1_POLICY_SKILL` and `FB_H2_REPRICING_SKILL` without reading FX
  outcomes;
- freeze the Phase 03 artifact consumed by Phase 04.

### Phase 04 - currency divergence

- derive G10 pressure ranks and pair differentials without refitting;
- evaluate `FB_H3` through `FB_H6`;
- report research marks separately from executable-price evidence;
- emit no entry/exit rule or PnL backtest.

### Phase 05 - Fundamental Bias research gate

Phase 05 aggregates rather than refits. It emits
`PROCEED_TO_TECHNICAL_TIMING_RESEARCH` only when:

1. point-in-time/provenance gate passes;
2. all ten currencies pass the primary sample contract;
3. `FB_H1_POLICY_SKILL` is `SUPPORTED`;
4. `FB_H2_REPRICING_SKILL` is `SUPPORTED`;
5. at least two of `FB_H3`, `FB_H4`, and `FB_H5` are `SUPPORTED`, including
   at least one of `FB_H3` or `FB_H4`;
6. `FB_H6_STABILITY` is `SUPPORTED`;
7. FX reference-rate limitations are explicit and no profitability claim is
   made;
8. 2025 onward remains sealed and the next contract is not outcome-tuned.

Any `FAIL`, `NOT_SUPPORTED`, or `NOT_TESTED` in a mandatory condition produces
`DO_NOT_PROCEED_WITH_FUNDAMENTAL_BIAS_SPECIFICATION`.

## 14. Artifact contract

Every phase writes an immutable run directory containing:

```text
config_snapshot.yaml
source_manifest.json
sample_flow.json
issues.jsonl
summary.json
REPORT.md
manifest.json
```

Model phases additionally persist feature names/order, training membership,
fold boundaries, selected penalties, coefficients, predictions, residuals,
benchmark losses, bootstrap settings, random seed, software version, and input
hashes.

## 15. Change control

After Phase 00 acceptance, changes to a primary feature, target, model,
horizon, sample split, hypothesis, or gate require:

1. a new versioned contract amendment;
2. a written reason independent of observed FX results;
3. a new hypothesis identifier;
4. preservation of the original result;
5. no retroactive claim that the amendment was preregistered.
