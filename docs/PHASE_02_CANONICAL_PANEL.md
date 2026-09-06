# Phase 02 - Canonical point-in-time panel

Status: `REVIEW_REQUIRED`

Phase 02 built 950 country-month rows from February 2015 through December
2022. Of these, 708 pass all macro, policy-label, and lagged-proxy checks. The
registered 2021-2022 evaluation window contains 232 complete rows out of 240.

## What is real and point-in-time

- Each macro row uses the exact ALFRED month-end vintage requested for that
  research snapshot.
- Old observations are standardized only against earlier reference periods in
  that same vintage; at least 36 observations are required.
- BIS month-end central-bank policy rates supply the six-month policy label.
- Each EIOPA one-year RFR curve becomes visible one month after its reference
  month, as frozen in Amendment 001.
- Source instrument identifiers remain visible. Across the complete panel the
  workbooks include SWP, OIS, and GVT curves; this is a proxy, not a clean OIS
  expectation series.
- Phase 02 does not parse or inspect the ECB FX file.

## Why it is not a clean pass

Eight of 240 registered evaluation rows fail closed. ALFRED's retired OECD
series do not expose a sufficiently recent observation in the relevant
vintage: NOK labour has four missing months, CHF labour two, and JPY inflation
two. They are not forward-filled or replaced after seeing outcomes.

This does not stop the engineering loop. Phase 03 may estimate only eligible
folds, but Phase 05 must treat incomplete G10 coverage as a mandatory quality
failure unless a future, separately registered data-source amendment repairs
it.

## Reproduction

```powershell
.\.venv\Scripts\fbias.exe phase02-fetch `
  --config config\research_proxy_v0_2.json `
  --raw-root data\raw\phase02

.\.venv\Scripts\fbias.exe phase02-build `
  --config config\research_proxy_v0_2.json `
  --raw-root data\raw\phase02 `
  --output artifacts\phase02\run_002
```

The full panel and immutable manifest are generated under ignored `artifacts/`.
The compact audit result is committed under `evidence/phase02/`.
