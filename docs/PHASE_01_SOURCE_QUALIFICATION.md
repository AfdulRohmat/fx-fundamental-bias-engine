# Phase 01 - Free G10 Source Qualification

Status: POC complete - `REVIEW_REQUIRED`

## Readable result

The free-data route is partly viable, but the exact engine registered in Phase
00 cannot proceed to a primary panel yet. We can reconstruct research FX marks,
obtain a comparable G10 policy-rate history, and retrieve point-in-time vintages
for most macro candidates. We did **not** qualify a free six-month OIS or
short-rate-futures history for every G10 currency.

This is a source-contract result, not a failed alpha test. Phase 01 did not load
registered FX outcomes, fit weights, rank currencies, or calculate returns.

## What passed

### ECB FX reference rates

The official ECB API sample contained AUD, CAD, CHF, GBP, JPY, NOK, NZD, SEK,
and USD per EUR on 20 common business dates in December 2024. EUR is an identity
leg. The audited cross calculation on 2024-12-31 was:

```text
USDJPY = JPY_per_EUR / USD_per_EUR
       = 156.9544710751757
```

The parser enforces orientation and positive finite values. These remain
indicative reference marks, not executable quotes.

### BIS scalar policy-rate history

The official BIS API v2 sample contained daily values for all ten G10 areas.
It also exposes important effective-dated compilation changes, including the
US target-range midpoint, the 2024 ECB switch to the deposit facility rate, and
periods in Japan without a single conventional policy-rate target.

The scalar history mechanism passes, while the mandatory bank profiles remain
`REVIEW_REQUIRED` for exact announcement availability and historical corridor
interpretation.

### ALFRED point-in-time mechanism

The common request asked each of 30 candidate headline-inflation,
underlying-inflation, and unemployment series for the 2018-12-31 and 2024-12-31
vintages.

- 24 returned valid ZIP/CSV vintage tables.
- 6 returned HTML rather than a data package under the identical request:
  `CPALTT01JPM659N`, `CPALTT01NZQ659N`, `CPGRLE01JPM659N`,
  `CPHPTT01EZM659N`, `LMUNRRTTCHM156S`, and `LRHUTTTTEZM156S`.
- In the US headline-CPI sample, 44 of 58 cells visible in both vintages changed,
  proving that current-history substitution would create look-ahead risk.
- Australian and New Zealand inflation candidates are quarterly; New Zealand
  harmonised unemployment is quarterly; Swiss monthly registered unemployment
  is not the same definition as quarterly harmonised unemployment.

Therefore ALFRED is a valid vintage mechanism, but the proposed series set is
not yet a qualified homogeneous G10 macro panel.

## What did not pass

### Registered six-month policy expectation

No candidate qualified as a credential-free, point-in-time six-month policy
path for every G10 currency. Public CME and ICE material establishes the
relevant futures products, but not a common free historical settlement archive
meeting our sample and replay contract.

The Phase 00 rule applies: realized future policy moves cannot replace the
missing pre-priced expectation, and a government yield cannot be renamed OIS.

### EIOPA challenger

Two official EIOPA monthly archives were downloaded and parsed by workbook
sheet name rather than hard-coded file positions. Both contained all ten G10
curves at the one-year maturity:

| Reference date | Instrument metadata | G10 coverage |
|---|---|---:|
| 2018-12-31 | all `SWP` | 10/10 |
| 2024-12-31 | AUD/EUR/NOK/NZD/SEK `SWP`; CAD/CHF/GBP/JPY/USD `OIS` | 10/10 |

This is useful as a one-year risk-free-curve proxy, but it fails the registered
primary field for four reasons:

1. the minimum workbook tenor is one year, not six months;
2. it is an annual zero-coupon RFR curve, not a raw meeting-dated policy path;
3. the source instrument is not homogeneous across currencies or time;
4. the archive publication date can be later than the curve reference date, so
   a point-in-time selector must lag it until actually available.

With monthly archives beginning around late 2015, a 60-month training minimum
also conflicts with a 2019 evaluation start. Using this proxy would require a
prospective contract amendment and likely a later evaluation start.

## Frozen Phase 01 mechanics

- Primary snapshot: 17:00 `Europe/Brussels` on the last ECB publication day of
  each calendar month.
- Weekly diagnostic: the same time on Friday with earlier-only holiday fallback.
- Bootstrap: circular moving blocks of 3 calendar months, 10,000 resamples,
  seed `20260906`; all rows from one month remain clustered.
- Publication time, observation time, vintage time, and retrieval time remain
  separate.
- Data from 2025 onward remains sealed from model and outcome commands.

## Decision and available paths

The Phase 01 decision is `REVIEW_REQUIRED`; it is not permission to start the
registered Phase 02 panel unchanged.

1. **Strict Tier A path:** obtain a qualifying historical OIS/futures source,
   potentially paid, and keep the six-month hypotheses unchanged.
2. **Free proxy path:** amend the contract before outcome inspection to a
   one-year `EIOPA_RFR_PROXY` claim, explicitly model its publication lag and
   mixed input instruments, recalculate the feasible evaluation start, and give
   every proxy hypothesis a new identifier.
3. **Structural-only path:** build macro-to-realized-policy research without the
   repricing claim. It cannot pass the full Fundamental Bias gate defined in
   Phase 00.

For the current free-data constraint, path 2 is the most practical experiment,
but it answers a weaker question than the original six-month OIS design.

## Reproducible evidence

- `evidence/phase01/poc_evidence.json`: derived facts and raw-file hashes.
- `evidence/phase01/source_matrix.csv`: all 70 required rows.
- `evidence/phase01/source_gate_summary.json`: counts and fail-closed decision.
- `config/phase01_sources.json`: candidate identifiers and visible limitations.

Raw downloads stay under ignored `data/raw/phase01_poc/`; they are not
redistributed by this repository.

## Official source pages

- ALFRED download/vintage semantics:
  https://alfred.stlouisfed.org/help/downloaddata
- BIS Central Bank Policy Rates:
  https://data.bis.org/topics/CBPOL?m=237
- BIS API v2 documentation:
  https://stats.bis.org/api-doc/v2/
- ECB data API examples:
  https://data.ecb.europa.eu/help/api/data-examples
- ECB reference-rate overview:
  https://data.ecb.europa.eu/key-figures/ecb-interest-rates-and-exchange-rates/exchange-rates
- EIOPA RFR archive:
  https://www.eiopa.europa.eu/tools-and-data/risk-free-interest-rate-term-structures/risk-free-rate-previous-releases-and-preparatory-phase_en
