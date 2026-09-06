# Research Backbone

Status: Phase 00 literature contract

## Why weights must not be manual points

An ordinal label such as `hawkish +2` and `slightly hawkish +1` does not prove
that the first state has twice the economic effect of the second. Adding such
labels also assumes comparability across indicators and central banks without
estimating it.

This project separates:

1. unweighted categorical agreement for a transparent baseline;
2. policy-outcome-trained coefficients for structural policy pressure;
3. market-expectation-trained coefficients for expected repricing;
4. FX returns as an independent downstream test.

## Structural policy lineage

| Research | Contract implication |
|---|---|
| Taylor (1993), *Discretion versus Policy Rules in Practice* | inflation and real-activity gaps provide an economic policy-rule foundation; fixed coefficients are a benchmark, not universal G10 weights |
| Clarida, Gali & Gertler (1998), *Monetary Policy Rules in Practice* | reaction coefficients can be estimated, forward-looking, smoothed, and heterogeneous across central banks |
| Orphanides (2001), *Monetary Policy Rules Based on Real-Time Data* | revised ex-post data can misdescribe historical policy; point-in-time inputs are mandatory |
| Molodtsova & Papell (2009), *Out-of-Sample Exchange Rate Predictability with Taylor Rule Fundamentals* | cross-country policy-rule differences provide a defensible bridge to FX, but still require out-of-sample validation |
| Gonzalez-Astudillo & Tanvir (2023), *Hawkish or Dovish Fed?* | reaction coefficients may change over time; time variation belongs in a challenger/stability test |

## Expectations, surprise, and guidance lineage

| Research | Contract implication |
|---|---|
| Kuttner (2001), *Monetary Policy Surprises and Interest Rates* | separate anticipated actions from unexpected actions using pre-decision market pricing |
| Gurkaynak, Sack & Swanson (2005), *Do Actions Speak Louder Than Words?* | one target-rate factor is insufficient; a distinct future-policy-path factor captures statement/guidance information |
| Stavrakeva & Tang (2015), *Exchange Rates and Monetary Policy* | expected future policy and monetary-policy surprises are directly relevant to developed-market currencies |
| Jarocinski & Karadi (2020), *Deconstructing Monetary Policy Surprises* | central-bank announcements also reveal information about the economic outlook; a hawkish/dovish interpretation is not always a pure policy shock |

These results support an expectation-aware engine, but they do not validate the
video's stronger rhetorical claims as universal laws. Expected announcements
can still matter through guidance and information effects; `buy the rumor,
sell the news` is a hypothesis, not a deterministic trading rule.

## Secondary methodological lineage

Stock and Watson's diffusion-index work supports PCA/dynamic factors when many
macro indicators must be compressed. PCA is not primary because it maximizes
predictor variance, not policy relevance.

Wright's Bayesian model averaging supports combining uncertain FX forecasts.
It remains a future challenger because this program first tests one compact,
interpretable causal chain.

## Links

- Taylor (1993): https://web.stanford.edu/~johntayl/Papers/Discretion.PDF
- Clarida, Gali & Gertler (1998): https://www.fedinprint.org/item/fedfpr/28523
- Orphanides (2001): https://doi.org/10.1257/aer.91.4.964
- Molodtsova & Papell (2009): https://doi.org/10.1016/j.jinteco.2008.11.001
- Gonzalez-Astudillo & Tanvir (2023): https://doi.org/10.17016/FEDS.2023.070
- Kuttner (2001): https://www.newyorkfed.org/research/staff_reports/sr99.html
- Gurkaynak, Sack & Swanson (2005): https://www.federalreserve.gov/pubs/feds/2004/200466/200466pap.pdf
- Stavrakeva & Tang (2015): https://www.bostonfed.org/publications/research-department-working-paper/2015/exchange-rates-and-monetary-policy.aspx
- Jarocinski & Karadi (2020): https://doi.org/10.1257/mac.20180090
- Stock & Watson (2002): https://www.princeton.edu/~mwatson/papers/Stock_Watson_JBES_2002.pdf
- Wright (2008): https://www.federalreserve.gov/Pubs/Ifdp/2003/779/

## Interpretation boundary

These papers justify the mechanism and candidate estimation methods. They do
not establish that this repository's exact features, sample, expectation proxy,
or G10 ranking has an FX edge. That claim exists only if the frozen Phase 03-05
tests pass.
