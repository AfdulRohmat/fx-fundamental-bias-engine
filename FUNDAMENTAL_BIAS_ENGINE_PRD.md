# PRD - G10 Fundamental Bias Engine

Version: 0.1
Status: Phase 00 research-design baseline
Product type: point-in-time macro research engine, not a trading strategy

## 1. Purpose

Build a pair-agnostic engine that measures relative macro and central-bank
pressure across G10 currencies. The engine tests whether inflation and labour
conditions predict the future policy path and whether the resulting policy
divergence predicts medium-horizon FX direction.

This is a new research program. It does not repair, overwrite, or reinterpret
the completed USDJPY Employment Situation event study. That program remains a
negative baseline for its registered short-horizon hypotheses.

## 2. Research thesis

The thesis is a three-layer causal chain:

```text
publicly available inflation and labour state
    -> model-implied central-bank policy path
    -> gap versus the policy path already priced by markets
    -> expected policy-path repricing
    -> relative repricing pressure between two currencies
    -> medium-horizon FX bias
```

Fundamentals determine a directional context. Technical analysis, if studied
later, determines timing. Technical entry rules are excluded until this bias
engine passes its own frozen research gate.

## 3. Primary questions

1. Can a small, economically motivated macro state explain the next six months
   of central-bank policy changes out of sample?
2. Does its disagreement with the policy path already priced by markets predict
   subsequent policy-expectation repricing?
3. Does base-minus-quote expected repricing explain the next non-overlapping
   monthly FX return?
4. Do the strongest and weakest currencies identified from a G10 ranking
   separate in the expected direction?
5. Is the relationship stable across predeclared chronological windows and not
   concentrated in one country or crisis episode?

## 4. Explicit non-goals

- no manual `-2` through `+2` arithmetic score;
- no direct optimization of macro weights against FX returns;
- no LLM-generated macro values, policy labels, or historical decisions;
- no intraday announcement strategy;
- no entry, stop, take-profit, leverage, position sizing, or portfolio PnL;
- no use of data published after a historical decision timestamp;
- no opening of 2025-and-later data before a later holdout contract is frozen.
- no claim that an announced hike or cut is new information without measuring
  what the market had already priced.

## 5. Currency universe

The target universe is the ten G10 currencies:

```text
USD EUR JPY GBP CHF CAD AUD NZD NOK SEK
```

USDJPY remains a required readable case study, but it is not the primary unit
of model selection. Currency and pair mappings must be configuration-driven.

## 6. Decision clock

The engine creates weekly observable states for operational inspection. The
primary research sample uses one deterministic month-end snapshot per currency
to avoid treating highly overlapping weekly states as independent evidence.

The exact timestamp and holiday fallback are frozen after the source POCs and
before any FX-return model is run. Every input must satisfy:

```text
source_available_at <= snapshot_as_of
```

## 7. Country macro state

Each country state contains four signed components:

```text
inflation_gap
inflation_momentum
labour_tightness
labour_momentum
```

Positive values always mean more hawkish policy pressure.

- `inflation_gap` compares the bank-specific target measure with the target in
  force at that timestamp.
- `inflation_momentum` measures the annualized three-month movement in the
  bank-specific underlying inflation index relative to its twelve-month pace.
- `labour_tightness` is the negative, past-only standardized unemployment
  level, so lower unemployment is more hawkish.
- `labour_momentum` is the negative three-month unemployment change, so falling
  unemployment is more hawkish.

Each central-bank profile versions its target, target measure, underlying
inflation measure, labour measure, and effective dates. A generic `core CPI`
cannot silently stand in for every bank's policy framework.

All standardization is expanding, country-local, past-only, and excludes the
current observation from its historical mean and standard deviation.

## 8. Expectations and forward-guidance context

An observed policy action is not automatically a signal. The engine separates:

```text
actual policy action
expected target action
expected future policy path
change in the expected path
```

The first implementation represents forward guidance through changes in a
market-implied policy-path series. That is preferable to assigning subjective
hawkish/dovish scores to statements: prices aggregate the action, statement,
press conference, and prior expectations into one observable repricing.

Central-bank text/NLP is a future challenger only. If added later, it requires
immutable official documents, exact publication timestamps, a frozen model and
prompt/version, and an independent test against policy-path repricing.

## 9. Weighting method

### Primary model

The structural weighting layer is a pooled G10 central-bank reaction function:

```text
future_policy_change_6m_bp[c,t]
    = country_intercept[c]
    + policy_smoothing_terms[c,t]
    + beta_1 * inflation_gap_z[c,t]
    + beta_2 * inflation_momentum_z[c,t]
    + beta_3 * labour_tightness_z[c,t]
    + beta_4 * labour_momentum_z[c,t]
```

The coefficients are fitted with ridge shrinkage using policy outcomes only.
The primary slopes are common across G10 after country-local normalization;
country intercepts absorb persistent level differences. An explicitly labelled
challenger may add shrunk country-specific slope deviations.

Economically signed inputs and non-negative macro coefficients ensure that a
higher inflation or labour-pressure feature cannot mechanically create a more
dovish score. An unconstrained fit remains visible as a diagnostic.

The output is a model-implied policy change in basis points, not an ordinal
score.

### Primary expectation-aware signal

The structural estimate must be compared with the market-implied path:

```text
pricing_gap_6m[c,t]
    = model_implied_policy_change_6m[c,t]
    - market_implied_policy_change_6m[c,t]
```

A second, policy-market-only walk-forward model tests whether the macro state,
pricing gap, and lagged path movement predict the next month's change in the
six-month market-implied path. Its output is `expected_repricing_bp`.

This means that high inflation does not automatically create a long-currency
bias. If an equally hawkish path is already priced, expected repricing can be
near zero. A lower-than-expected rate cut accompanied by hawkish guidance can
produce positive repricing even though the observed action was a cut.

Qualified point-in-time expectation data is mandatory for the full claim. If
free G10 OIS/futures data cannot be qualified, the structural model may still
be researched, but expectation-aware bias and the final gate remain
`NOT_TESTED`; a government yield proxy cannot be silently called OIS.

### Hyperparameters and walk-forward fitting

- ridge penalty is selected using nested expanding-window validation;
- validation loss is policy-path error only, never an FX return;
- a historical fit uses only rows whose full forward label was already known;
- all transforms are re-estimated inside each walk-forward fold;
- selected penalties, coefficients, training membership, and predictions are
  persisted for every forecast origin.

### Frozen benchmarks

1. no-policy-change forecast;
2. policy-rate momentum/smoothing forecast;
3. equal-weight normalized macro pressure;
4. fixed Taylor-style inflation/labour rule;
5. no-weight dominance regime, where inflation and labour must agree.

Equal weights and fixed Taylor weights are benchmarks, not the primary claim.

## 10. Currency and pair bias

For currency `c` at time `t`:

```text
currency_pressure[c,t] = expected policy-path repricing in basis points
```

For an FX pair:

```text
pair_bias[base/quote,t]
    = currency_pressure[base,t] - currency_pressure[quote,t]
```

Dashboard labels are derived from rank and uncertainty, not arithmetic points:

- `STRONG_HAWKISH`: top G10 quintile and interval above zero;
- `HAWKISH`: positive pressure without strong classification;
- `MIXED`: uncertainty spans zero or inflation/labour conflict materially;
- `DOVISH`: negative pressure without strong classification;
- `STRONG_DOVISH`: bottom G10 quintile and interval below zero.

Labels are categorical presentation. They are never treated as `+2`, `+1`,
`0`, `-1`, and `-2` in research regressions.

## 11. Research evaluation

### Stage 1 - policy-path validity

Test whether the learned reaction function improves truly out-of-sample
six-month policy-path forecasts relative to frozen naive and equal-weight
benchmarks. Three-month policy change is secondary.

Then test whether `pricing_gap_6m` and the frozen macro state predict subsequent
one-month repricing of the market-implied six-month policy path. This stage is
trained and evaluated only on macro, policy, and rates-market data.

### Stage 2 - FX-bias validity

Without refitting either policy model on FX outcomes, test:

- next non-overlapping monthly pair returns;
- monthly cross-sectional Spearman rank information coefficient;
- equal-weight top-two minus bottom-two G10 currency return;
- USDJPY as a prespecified readable case study;
- chronological and leave-one-currency-out stability.

Five- and ten-business-day returns are secondary. Technical timing is a future
program conditional on passing the Fundamental Bias research gate.

## 12. Initial sample policy

- source-search target: 2005 through 2024;
- expected model-development history: no later than 2010 through 2018;
- frozen out-of-sample research evaluation: 2019 through 2024;
- sealed holdout: 2025 onward.

Phase 01 may move the start date later only through a deterministic common-data
coverage rule and before inspecting any Phase 03 or Phase 04 result. It cannot
move the 2019 evaluation boundary or open the holdout. Insufficient coverage is
a source-gate failure, not permission to weaken the point-in-time contract.

## 13. Required outputs

- versioned central-bank policy profiles;
- immutable raw snapshots and source manifest;
- canonical macro observation and policy-rate tables;
- point-in-time monthly and weekly state panels;
- fold-level coefficients, penalties, memberships, and policy predictions;
- point-in-time market-implied policy paths, pricing gaps, and repricing
  predictions;
- pair-bias and G10-rank panels;
- benchmark comparisons and uncertainty estimates;
- sample flow, exclusions, concentration diagnostics, and limitations;
- machine-readable hypothesis registry and research-gate decision;
- readable reports that distinguish policy prediction, FX association, and
  any later strategy claim.

## 14. Success boundary

The strongest allowed successful conclusion is:

```text
PROCEED_TO_TECHNICAL_TIMING_RESEARCH
```

It does not mean that a profitable strategy exists. Failure means that the
current Fundamental Bias specification must not be converted into trading
rules. It does not prove that all fundamental analysis is useless.

## 15. Delivery roadmap

| Phase | Scope | Decision boundary |
|---|---|---|
| 00 | freeze PRD, video implications, literature, and technical contract | no data modelling |
| 01 | qualify free G10 macro, policy-expectation, policy-rate, and FX sources | pass/fail source gate |
| 02 | build canonical point-in-time macro, policy, expectations, and FX panel | pass/fail data gate |
| 03 | estimate structural-policy and expected-repricing models | pass/fail policy/expectations stage |
| 04 | test currency/pair divergence against FX returns | pass/fail FX stage |
| 05 | aggregate the frozen Fundamental Bias research gate | proceed/do not proceed |
| 06+ | technical timing and execution research | only if Phase 05 proceeds |
