# Video Method Review

The project was motivated by two educational videos and user-provided
transcripts. Videos are context, not empirical authority. Research claims are
anchored separately in `RESEARCH_BACKBONE.md`.

## Video 1 - inflation/labour divergence

Source: https://youtu.be/PhtzbUzUEyA

Useful method:

- interpret inflation and labour through the relevant central bank;
- use a recent multi-month trend rather than one isolated release;
- compare countries and pair a relatively hawkish currency with a relatively
  dovish one;
- use fundamentals for directional context and technicals later for timing.

Contract translation:

- effective-dated, bank-specific macro profiles;
- four-component inflation/labour vector;
- G10 cross-sectional ranking and base-minus-quote signal;
- technical timing excluded through the Fundamental Bias gate.

## Video 2 - expectations and what comes next

Source: https://youtu.be/QWytduPpCcY

Useful method:

- markets respond to changes relative to prior expectations;
- an expected rate action can already be reflected in price;
- the statement and forward path can dominate the announced target action;
- pre-event repricing and post-event expectation changes must be separated.

Contract translation:

```text
macro state
    -> structural policy estimate
    -> compare with market-implied path
    -> predict expectation repricing
    -> test relative repricing against FX
```

The 50 bp cut example is represented as separate fields for actual action,
expected action, target surprise, and path repricing. A cut with hawkish
guidance may therefore produce positive path repricing without receiving a
subjective `hawkish +2` score.

## Claims not accepted literally

- â€œMarkets do not care what happenedâ€ is too absolute. Unexpected actions and
  information revealed by the central bank can matter.
- â€œBuy the rumor, sell the newsâ€ is not a universal direction rule.
- Price movement before an event does not prove one identifiable expectation
  caused it.
- Forward guidance cannot be reconstructed reliably from hindsight summaries.

The initial engine captures guidance through observed market-path repricing.
Text classification is deferred until official historical documents and a
frozen, reproducible classifier can be qualified.

## Resulting research boundary

The videos together imply that a raw macro score is incomplete. The actual
candidate edge is not simply â€œhigh inflation means buy the currency.â€ It is:

> Does point-in-time macro evidence identify a future policy path that differs
> from what was already priced, and does the subsequent relative repricing
> predict medium-horizon FX direction?
