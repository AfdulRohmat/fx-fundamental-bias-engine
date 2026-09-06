# FX Fundamental Bias Engine

A separate, pair-agnostic G10 research project for testing whether relative
inflation, labour conditions, and policy-expectation repricing provide a useful
medium-horizon FX directional bias.

The project is intentionally separate from
`fx-fundamental-analysis`, whose registered USDJPY employment-event program
ended with `DO_NOT_PROCEED`. This repository asks a different question and does
not reinterpret that result.

## Current status

Phase 00 and Phase 01 are complete. Amendment 001 created a separate,
explicitly weaker EIOPA one-year RFR proxy namespace; it does not replace the
original untested Tier A six-month expectation claim. Phase 02 built the real
point-in-time G10 panel and is `REVIEW_REQUIRED`: 232/240 evaluation rows are
complete, with eight retired-series gaps failed closed. Phase 03 is also
`REVIEW_REQUIRED`: the structural-policy diagnostic is promising, but the
registered repricing test is under-sampled and its low-history diagnostic fails
to beat no change. Phase 04 registered FX hypotheses are therefore `NOT_TESTED`;
its non-gating low-history diagnostics have negative point estimates and wide
intervals. No strategy or profitability claim exists, and 2025 onward remains
sealed.

## Research architecture

```text
point-in-time inflation and labour state
    -> model-implied central-bank policy path
    -> compare with the path already priced by markets
    -> expected policy-path repricing
    -> base-minus-quote currency divergence
    -> non-overlapping medium-horizon FX research
    -> technical timing only after a successful research gate
```

## Why there is no `+1/+2` score

The continuous output is measured in expected basis points. Structural macro
weights are learned against central-bank policy outcomes; repricing weights are
learned against policy-expectation changes. Neither layer sees FX returns while
its weights are selected.

Transparent no-weight dominance, equal-weight, and fixed Taylor-style rules are
retained only as frozen benchmarks.

## Planned phases

| Phase | Scope | Status |
|---|---|---|
| 00 | PRD, video review, literature backbone, technical contract | Complete |
| 01 | free G10 data-source qualification | POC complete - `REVIEW_REQUIRED` |
| 02 | canonical point-in-time macro/policy/proxy panel | Complete - `REVIEW_REQUIRED` (232/240 evaluation rows) |
| 03 | structural reaction and expected-repricing models | Complete - hypotheses `NOT_TESTED`; diagnostics retained |
| 04 | G10 currency and pair-divergence research | Complete - registered tests `NOT_TESTED`; exploratory signs negative |
| 05 | aggregate Fundamental Bias research gate | Gated by Phase 04 |
| 06+ | technical timing and execution research | Only after Phase 05 proceeds |

## Documentation

- [Product requirements](FUNDAMENTAL_BIAS_ENGINE_PRD.md)
- [Technical plan and frozen contract](docs/TECHNICAL_PLAN.md)
- [Free-data source plan](docs/DATA_SOURCE_PLAN.md)
- [Research backbone](docs/RESEARCH_BACKBONE.md)
- [Video-method review](docs/VIDEO_METHOD_REVIEW.md)
- [Phase 00 design result](docs/PHASE_00_RESEARCH_DESIGN.md)
- [Phase 01 readable source result](docs/PHASE_01_SOURCE_QUALIFICATION.md)
- [Phase 02 canonical-panel result](docs/PHASE_02_CANONICAL_PANEL.md)
- [Phase 03 model result](docs/PHASE_03_POLICY_PROXY_MODELS.md)
- [Phase 04 currency-divergence result](docs/PHASE_04_CURRENCY_DIVERGENCE.md)
- [Machine-readable Phase 01 POC evidence](evidence/phase01/poc_evidence.json)
- [Complete 70-row source matrix](evidence/phase01/source_matrix.csv)

## Reproduce Phase 01 without network access

After placing the immutable provider payloads under the ignored `data/` tree:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\mypy.exe src
```

The parsers fail closed on missing G10 curves, malformed vintage columns,
non-finite values, unexpected FX orientation, duplicate rows, and incomplete
source matrices. Raw provider files remain untracked; committed evidence stores
their SHA-256 hashes and derived audit facts.

## Research safeguards

- point-in-time values and availability timestamps only;
- revisions remain separate vintages;
- one non-overlapping primary monthly research clock;
- explicit separation of actual action, expected action, and future path;
- no substitution of government yields for OIS without a visible proxy label;
- no FX-return-driven fitting of macro or repricing weights;
- no LLM-generated historical facts or primary policy labels;
- no strategy/PnL claim before the final research gate;
- 2025 onward remains sealed.

## Branch workflow

`main` is the stable baseline. Each implementation phase uses:

```text
phase/<number>-<short-description>
```

Phase branches must update their contract/result document and pass all
network-free checks before merge.
