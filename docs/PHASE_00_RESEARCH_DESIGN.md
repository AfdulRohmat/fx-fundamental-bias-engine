# Phase 00 - Research Design

Status: prepared for review; no empirical model result

## Outcome

The Fundamental Bias Engine now has an independent repository and a candidate
frozen contract. It is not a continuation branch of the completed USDJPY
employment-event study.

The design incorporates both supplied video methods:

1. compare G10 inflation and labour regimes through each central bank;
2. distinguish actual policy actions from what markets expected beforehand;
3. measure the future policy path, not only the current policy rate;
4. test relative expected repricing before any technical-entry research.

## Core decision

The engine does not use `+1/+2` arithmetic scoring. It preserves three distinct
objects:

```text
structural_policy_change_6m_bp
market_implied_policy_change_6m_bp
expected_repricing_1m_bp
```

The first is learned from macro-to-policy history. The second is observed from
a qualified rates-market source. The third is learned from macro and
rates-market history without reading FX outcomes.

Only the base-minus-quote difference in expected repricing reaches the FX
research stage.

## Important correction introduced by video 2

A high inflation/labour score is not automatically bullish for a currency. If
the market already prices the same hawkish policy path, the remaining repricing
signal can be near zero. Likewise, a rate cut can coexist with positive
repricing when the cut was fully expected and subsequent guidance moves the
future path upward.

## Research layers

| Layer | Target | Unit | May use FX outcomes? |
|---|---|---:|---|
| Structural reaction | future six-month realized policy change | bp | No |
| Expected repricing | next-month change in six-month market-implied path | bp | No |
| Currency divergence | expected repricing base minus quote | bp | Read-only input to FX test |
| FX validation | next non-overlapping monthly return | percent/log return | Yes, evaluation only |

## Main risk

Free, historical, point-in-time policy-expectation coverage across all G10
currencies may not exist in one consistent source. Phase 01 must test OIS or
short-rate futures first. Sovereign yields may be evaluated only as an explicit
proxy because they also contain term, credit, and liquidity premia.

If no common source qualifies, the full expectation-aware hypothesis is
`NOT_TESTED`. The project will not silently substitute future realized policy
rates and claim that it measured what markets expected.

## Phase 00 artifacts

- `FUNDAMENTAL_BIAS_ENGINE_PRD.md`
- `docs/TECHNICAL_PLAN.md`
- `docs/DATA_SOURCE_PLAN.md`
- `docs/RESEARCH_BACKBONE.md`
- `docs/VIDEO_METHOD_REVIEW.md`
- `references/README.md`

## Next gate

After the contract is reviewed and accepted, Phase 01 performs source POCs
only. It does not fit weights or inspect the registered FX outcomes.
