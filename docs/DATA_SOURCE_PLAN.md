# Free Data Source Plan

Status: Phase 00 candidates; no source is primary until Phase 01 passes its POC

## Source principles

- Prefer central banks, national statistical offices, ECB, BIS, OECD, and
  ALFRED/FRED over aggregators.
- A historical value without historical availability or vintage semantics is
  not automatically point-in-time safe.
- Store provider payloads immutably with URL, retrieval timestamp, content
  type, and SHA-256.
- Record licensing/redistribution status independently from accessibility.
- Free access is required for the initial program.

## Candidate hierarchy

| Data family | Preferred candidate | Role | Main risk to test |
|---|---|---|---|
| Inflation and unemployment vintages | ALFRED-hosted national/OECD series | reconstruct values available at each snapshot | G10 series and vintage coverage differ |
| Official macro fallback | national statistical-office releases/APIs | validate values and publication dates | ten bespoke adapters and archive depth |
| Harmonized macro comparison | OECD SDMX | consistent cross-country series and metadata | current history may include revisions |
| Policy rates | central-bank histories, with BIS as cross-check | six-month structural-policy target | effective versus announcement timestamp |
| Policy expectations Tier A | free historical OIS or short-rate futures | already-priced six-month path and repricing | broad G10 history is often proprietary |
| Policy expectations Tier B | official one/two-year sovereign yields minus current policy rate | explicitly labelled path proxy | term, credit, and liquidity premia |
| Published policy paths | central-bank projections where available | validation/challenger only | not uniformly published across G10 |
| Policy targets/mandates | versioned official central-bank documents | bank-specific target mapping | historical mandate changes require manual audit |
| Daily FX research marks | ECB euro foreign-exchange reference rates | derive all G10 crosses at daily/monthly horizons | indicative, non-executable marks |
| FX validation fallback | Dukascopy daily aggregation | sensitivity and later cost work | volume and close convention |

Tier B cannot be described as OIS or a pure expectations measure. Phase 01 must
choose one common expectation definition before any downstream outcome is
inspected. If neither tier qualifies for all G10 currencies, the full bias
claim is `NOT_TESTED`.

## Required Phase 01 POCs

### Macro vintage POC

For every G10 currency, retrieve at least:

- official-target inflation measure or closest eligible series;
- preferred underlying inflation index;
- seasonally adjusted unemployment rate;
- complete vintage/release metadata for selected sample dates.

Audit at least one later revision per revisable series. A parser passing against
today's observations does not prove historical point-in-time eligibility.

### Policy-rate POC

For every central bank, prove rate units, effective dates, treatment of target
ranges/corridors/negative rates, and deterministic conversion to one comparable
scalar policy rate.

### Policy-expectation POC

For every currency, prove:

- the market instrument and exact six-month path conversion;
- observation and publication timestamps;
- historical coverage and missing-day behavior;
- expiry, roll, and meeting-date conventions;
- whether the value contains term, credit, or liquidity premia;
- a hand-calculated implied-change example;
- whether redistribution permits cached raw payloads.

This is the highest-risk source gate introduced by the forward-looking video
context. Realized future rate changes are not an acceptable silent substitute.

### Central-bank profile POC

Create effective-dated profiles for target definitions and measure choices.
Every manual mapping requires an official URL and a reviewer-visible note.

### FX reference-rate POC

Demonstrate that EUR-based source legs derive USDJPY and all other unordered
G10 crosses exactly. Audit provider timestamp, holidays, missing days, inverse
orientation, and a hand-calculated cross.

## Prohibited shortcuts

- attaching a release date equal to the observation month-end;
- treating retrieval time as historical publication time;
- using final revised history as if it were available in the past;
- calling a government yield a market-implied policy rate;
- treating an announced rate move as a surprise without its pre-event price;
- copying a third-party hawkish/dovish label as a feature;
- selecting different macro series after viewing their FX performance;
- filling a missing country from another definition without a versioned
  profile and sensitivity label.

## Source-gate output

Phase 01 produces one row per currency and required variable:

```text
currency
feature
provider
series_id
coverage_start
coverage_end
publication_time_status
vintage_status
expectation_kind
license_status
missing_rate
decision
limitation
```

The full G10 primary panel proceeds only when every required row is `PASS`.
`REVIEW_REQUIRED` may support adapter development but cannot be silently
promoted into the primary research sample.
