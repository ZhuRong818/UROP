# EventX Research Progress Report

> This is the 3 September 2026 report, preserved as a historical snapshot. The
> latest market–news research report is [7 October 2026](MARKET_NEWS_RESEARCH_PROGRESS_20261007.md).

**Student:** Zhu Rong
**Supervisor:** Lu Yao
**Reporting date:** 3 September 2026
**Project:** EventX — Incremental Information in Prediction-Market Repricing  
**Completed primary protocol:** `eventx-v3.1-historical-primary-20260902`
**Active confirmatory protocol:** `eventx-v4-confirmatory-polymarket-20260902`
**Secondary prospective protocol:** `eventx-v2.3-news-availability-clarifications-20260817`
**V5 development proposal:** sparse residual-news architecture; not yet frozen

## 1. Executive summary

EventX studies whether external information contains incremental, point-in-time
predictive information about prediction-market repricing. The completed historical
primary experiment tested the prerequisite comparison:

```text
B0: market-history features
B1: market-history features plus market-relevant news
```

The answer under the frozen design is negative. On 1,460,454 out-of-fold development
rows, B1 reduced average precision by 0.001916 and worsened Brier score by 0.000284.
Both metrics improved in zero of five folds, venue-specific Brier improvement was
negative for both venues, and the paired 5,000-sample block-bootstrap interval was
`[-0.000341, -0.000230]`. All H1-H5 promotion gates failed, so the preregistered
fallback selected B0. This is the primary research finding; B1 was not evaluated on
the holdout and cannot be rescued post hoc.

The historical study was substantially broader than the original prospective pilot.
After a label-blind data correction, it included 4,651 markets (3,832 Kalshi and 819
Polymarket), 21,439,891 positive-notional development executions, 479,179 frozen news
association events and 7,706,324 eligible development examples. The original v3 data
gate and its failure were preserved: 204,069 zero-count Kalshi rows caused 19 markets
to miss the activity requirements. Version v3.1 removed exactly those markets without
using prices, labels, outcomes or holdout data and passed its corrected gate.

One B0 candidate was frozen and evaluated once on the historical holdout
`[2026-07-22, 2026-08-08)`. The source-bounded retrieval and continuity gate passed 34
daily partitions. On 211,718 eligible rows from 300 remaining active markets, B0
achieved AP 0.171628, ROC AUC 0.628037, Brier 0.107107 and ECE 0.015317. Performance
was stronger on Kalshi than Polymarket. These values establish modest absolute
out-of-time performance for B0, not incremental news value.

One procedural deviation is fully disclosed. The frozen holdout builder reported
label prevalence before the consumption receipt. This was detected before any model
prediction or performance metric; the candidate, transforms and evaluation formulas
were already frozen. The original artifact was retained, and a truthfulness-only
amendment was frozen before the one-shot evaluation. The result is therefore a serious
pilot with a receipt-order deviation, not a perfectly protocol-clean confirmation.

The original 14-market v2.3 prospective study remains unchanged as a secondary
replication through its 28 September development close. Its ongoing source work and
sparse news support are no longer blockers to the completed historical primary result.
KOL remains deferred because both audited association candidates failed.

A stronger, separate v4 confirmation has now been preregistered. It tests whether
news relevance, market-relative novelty and cross-publisher diffusion add beyond
market history, while explicitly excluding unsupported social-virality claims. The
future cohort contains 470 Polymarket binary-YES markets (470 condition-level
clusters), selected without prices or labels. Its only confirmatory interval is
`[2026-09-06, 2026-10-30)` UTC. All four nested B0/B1/B2/B3 models and the semantic
transform are hash-frozen, and the pre-holdout integrity verifier passes 29/29 checks.

The full v4 post-collection implementation is also complete and hash-frozen before
the holdout. It enforces collection gate → consumption receipt → point-in-time input
preparation → sealed example construction → one-shot evaluation. Synthetic tests
passed without reading any real future price or label, and an independent check
verified every frozen implementation hash and the absence of downstream holdout
artifacts.

The v4 historical discovery run is also complete. On 745,443 OOF rows, B0 had log
loss 0.459158, Brier 0.143117 and AP 0.206147. B3 had log loss 0.465617, Brier
0.143959 and AP 0.204842: a log-loss improvement of -0.006459 nats/row. Its paired
bootstrap interval was `[-0.007411, -0.005545]`. B1 and B2 were also worse than B0.
This is negative development evidence, not the future confirmatory answer. The frozen
future run will proceed without feature or model changes and will be reported whether
positive or null.

A post-freeze historical decomposition has now isolated the richer feature families.
Adding relevance and novelty (B2 versus B1) changed log loss by -0.000287 nats/row,
with paired interval `[-0.000807, 0.000235]`; this is compatible with no improvement.
Adding publisher diversity and diffusion (B3 versus B2) changed log loss by -0.003671,
with interval `[-0.005767, -0.001892]`. Although AP increased slightly, proper scoring
rules worsened. On the 31,789 rows exposed to cross-publisher reports, B3 materially
underpredicted event risk. This analysis is exploratory, uses only opened historical
data and does not alter the future confirmation.

Follow-up failure diagnostics now explain why a separate v5 architecture is needed.
The B3-versus-B0 loss was nearly zero on 498,214 rows without recent news
(-0.000029), but severe when news was present. Very recent 0–30 minute news retained
a small relevance/novelty hint (B2-versus-B1 +0.001321), while extreme negative B3
corrections below -1 logit lost 0.250544 per row. Thirteen of sixteen news
coefficients changed sign across fold fits, and the constant-learning-rate solver's
representative validation loss oscillated from 0.407326 at epoch 3 to 0.433444 at
epoch 5. A two-stage trade-arrival/conditional-repricing run also failed to rescue
the existing feature representation. These results support a v5 design based on a
cross-fitted market-model offset, a sparse residual news expert, correction shrinkage
and online story-lifecycle states. V5 is a development proposal, not a frozen or
confirmed result, and it cannot alter the protected v4 experiment.

That architecture has now been implemented and tested on opened historical data.
On 364,903 sequential OOF rows, time to terminal improved a matched market baseline
by +0.002965 log loss. A converged nonlinear gated model initially improved B0-v5 by
+0.009614, but the mandatory controls reversed its interpretation: a gated
context-only model improved by +0.010485, and a global nonlinear market-only model
improved by +0.018157 with interval `[0.014238, 0.021705]`. The global market model
beat the full news model by 0.008543. Direct news-mechanism additions over context-only
were null or negative, including full news at -0.000871 with interval
`[-0.001457, -0.000208]`. The current news candidates are therefore not eligible for
freezing; this supports improving B0, not claiming news novelty or diffusion.

The B0-v5N implementation decision is now also complete on opened data. A direct
nonlinear market-only model achieved log loss 0.428513, Brier 0.135783 and AP
0.278015 on 364,903 sequential OOF rows. It improved log loss over the stacked
nonlinear model by +0.003611, paired interval `[0.001359, 0.005694]`, and over linear
B0-v5 by +0.021768. A versioned convergence repair resolved the only capped fit in
512/2,000 iterations with maximum prediction change 0.00004109. Direct B0-v5N is the
development candidate; it remains unfrozen and unconfirmed.

A label-blind older-history probe also tested whether v5 could avoid waiting by using
pre-17-May data. Lumid has zero news rows ingested before 17 May 2026; its earliest
news ingestion is `2026-05-17T06:42:40.084691Z`. The 20,307,169 articles carrying
older publisher dates are later backfills and cannot be treated as historically
available. A pre-May incremental-news experiment is therefore not source-valid.

The v5 hierarchy is now explicitly falsification-oriented. The complete evaluator
must be frozen before new labels, then report B0-v5N replication, V5-R versus B0-v5N
and V5-R versus the matched E30-gated context-only control. Failure of either news
comparison closes the v5 news branch without changing the window, features,
relevance/novelty definitions, interactions or diffusion/lifecycle scope.

## Progress dashboard

![Secondary prospective EventX v2.3 progress dashboard](data/pic/image%20copy.png)

### Work completed so far

- Preregistered v4 before its future holdout, froze a label-blind 470-market
  Polymarket cohort, and hash-froze all B0-B3 model bundles.
- Derived point-in-time relevance, seven-day market-relative novelty and 24-hour
  exact-headline cross-publisher diffusion while preserving the audited news
  association membership exactly.
- Completed the v4 historical discovery comparison and launched a sealed daily Lumid
  collector that calculates no labels, predictions, prevalence or metrics.
- Implemented, tested and hash-froze the v4 final collection audit, irreversible
  receipt, feature/label builder and one-shot evaluator before the holdout began.
- Completed a historical novelty/diffusion decomposition with paired uncertainty,
  exposure groups, novelty quartiles, category/venue results and paper-ready SVGs.
- Completed v5 failure-localization, solver-stability and two-stage feasibility
  diagnostics on opened historical data only; wrote a separate non-frozen v5 design
  candidate without reading the future v4 interval.
- Implemented the v5 gated-residual primitives, exact no-news equality tests,
  cross-fitted converged residual models, mechanism ablations, direct mechanism
  contrasts and a global nonlinear market-only control. The controls rejected the
  current news candidates and identified B0-v5N as the next baseline.
- Implemented and synthetic-tested the direct B0-v5N feature layer, compared direct
  and stacked nonlinear architectures, repaired the single capped fit in a separate
  version and specified a reduced 30-minute V5-R news candidate for new data only.
- Completed the source-valid historical v3.1 B0/B1 experiment, froze B0 and consumed
  its historical holdout exactly once.
- Preserved the failed v3 trade gate and corrected only its label-blind cohort defect
  in a separately versioned v3.1 protocol.
- Built and evaluated the historical v1 pipeline, then consumed one replacement
  out-of-time holdout exactly once.
- Corrected and independently audited the market taxonomy for all 3,420 candidates.
- Reconciled the fixed selection window and froze a 14-market Polymarket/Kalshi
  cohort.
- Built separate news and KOL association rules and subjected them to blind audits.
- Rehearsed all 14 venue-specific market-detail and trade endpoints without opening
  development outcomes.
- Preregistered v2.3, including the price definition, news-availability rule, model
  comparison, folds, metrics, bootstrap, promotion gates and one-shot holdout.
- Kept the label-blind legacy collector running and continued accumulating market,
  news and trade records.
- Launched the corrected v2.3 news collector with stable article identity, append-only
  content versions, conflict quarantine and an auditable request ledger.
- Materialised and hashed a complete Lumid warehouse snapshot through 28 August, then
  reconciled it against all valid EventX endpoint receipts without backdating feature
  availability.
- Reconciled all 12 observed collector gaps and activated host idle-sleep prevention.
- Ran frozen-rule news-density, source-lag, backfill-shock and trade-staleness
  diagnostics without reading any prices, outcomes or labels.

### What succeeded

| Component | Evidence | Decision |
|---|---|---|
| V4 pre-holdout freeze | 470 markets/clusters; all four models frozen; 29/29 verification checks | Passed before 6 Sep |
| V4 holdout implementation | All pipeline hashes match; synthetic label, invariance, model, bootstrap and receipt checks pass | Frozen before 6 Sep |
| V4 quality construction | 147,377 articles; 479,179 associations exactly equal to v3.1 membership/clock | Passed |
| V4 novelty contribution | B2−B1 log-loss improvement -0.000287; 95% interval [-0.000807, 0.000235] | No historical evidence of improvement |
| V4 diffusion contribution | B3−B2 log-loss improvement -0.003671; 95% interval [-0.005767, -0.001892] | Historically worse |
| V4 sealed collection | Four complete warm-up/news days through 3 Sep; no labels or metrics; no last error | Active |
| Historical v3.1 data gate | 4,651 markets; 21,439,891 normalized development executions; provenance and source gates passed | Passed and frozen |
| Historical development run | 7,706,324 examples; 1,460,454 OOF comparison rows; one fixed execution | Completed |
| B0 historical holdout | AP 0.171628, ROC AUC 0.628037, Brier 0.107107 on 211,718 rows | One-shot evaluation completed |
| Taxonomy | 250-row blind audit: precision 0.9720, recall 0.9739 | Passed and frozen |
| Cohort construction | All 3,420 endpoints reconciled; 14 markets passed fixed thresholds | Passed and frozen |
| News association | Precision 0.9733, recall 0.9605 | Passed; eligible for B1 |
| Trade snapshot | 14/14 mappings and 14/14 trade checks passed; 17,823 YES trades through 28 Aug; zero empty markets | Operationally feasible |
| v2.3 integrity | 16 artifacts checked with zero failures | Passed |
| Leakage control | No v2.3 labels, prevalence, predictions or metrics inspected | Preserved |
| Warehouse recovery | 28,307 rows; receipt row count matched; zero malformed/out-of-window rows | Passed for `[8 Aug, 28 Aug)` snapshot |
| News continuity | 12/12 operational gaps plus pre-launch interval reconciled | Passed as-of audit snapshot |
| Software contracts | Cap/gap, stable-identity/revision and 16-artifact preregistration checks | All passed with zero failures |
| V5 failure localization | 498,214 no-news OOF rows changed negligibly; severe loss concentrated on news-exposed corrections | Supports gated residual design |
| V5 point-in-time lifecycle diagnostic | 147,377 documents sequenced into auditable exact-headline states | Feasible; does not prove publisher independence |
| V5 matched baseline | Time-to-terminal contribution +0.002965 log loss on folds 3–5 | Retain for stronger market baseline |
| V5 nonlinear market control | +0.018157 log loss; interval [0.014238, 0.021705] | Strongest opened-data model |
| B0-v5N architecture | Direct beats stacked by +0.003611 log loss; interval [0.001359, 0.005694] | Direct nonlinear development candidate selected |
| B0-v5N convergence repair | 512/2,000 iterations; maximum prediction change 0.00004109 | All final fits converge |

### What failed or remains incomplete

| Component | Evidence | Consequence |
|---|---|---|
| V4 discovery B1-B3 | All worse than B0; B3 log-loss improvement -0.006459, bootstrap interval entirely negative | Quality/diffusion proxies have not yet supported the claim |
| Future Kalshi cohort path | Only 48/4,797 roster IDs reconciled to pre-cutoff metadata; tested detail returned 404; activity query timed out | V4 primary confirmation is Polymarket-only; Kalshi deferred |
| True news virality | No likes, views, reposts, shares or comments in validated Lumid fields | Unsupported; v4 measures cross-publisher diffusion only |
| V4 pre-holdout feature exposure | 3,680 associations in 133/470 markets; 3,297 events concentrated in macro | Adequate to execute, but uneven support limits category/general claims |
| Historical B1 promotion | Delta AP -0.001916; Brier improvement -0.000284; all H1-H5 false | Negative primary result; B0 selected |
| Original v3 trade gate | 204,069 zero-count rows; 19 markets failed corrected activity minima | v3 preserved as failed; separate label-blind v3.1 correction |
| Holdout receipt order | Builder disclosed prevalence before receipt, but before prediction/performance scoring | Fully disclosed procedural deviation; no rerun |
| KOL-v1 association | Precision 0.8000, recall 0.7317 | Failed; excluded |
| KOL-v2 association | Precision 0.8378, recall 0.6327; two uncertain rows | Failed; KOL deferred |
| Historical pilot candidates | KOL, rich-news, gated-KOL and combined variants failed frozen promotion criteria | B0 remained the historical reference |
| `/news/latest` rehearsal | Exactly 200 rows with no cursor or upper-time bound | Could not prove broad-feed completeness |
| Full development window | Window closes 28 September | Final exact-window gate cannot yet run |
| Warehouse timestamp conflicts | 698 rows across 348 normalised URLs | Quarantined from primary B1 pending deterministic reconciliation |
| B1 feature support | 43 associations in only 2/14 markets; 42 in one market; symbol feature constant zero | Major source-content/estimand risk |
| Trade freshness | Only 19.43% / 27.50% / 47.78% of grid rows are no older than 30/60/240 minutes | Staleness robustness is essential |
| Statistical breadth | Only 14 independent market clusters | Pilot-level, not population-wide claims |
| V5 correction calibration | Correction below -1 logit: -0.250544 B3-vs-B0 LL improvement on 13,967 rows | Current corrections are unsafe |
| V5 solver stability | 13/16 news coefficients changed sign; epoch-3/epoch-5 fold loss 0.407326/0.433444 | Fixed constant-LR training is unsuitable for v5 |
| V5 two-stage feasibility | Product news improvement -0.030432; 95% interval [-0.037606, -0.024146] | Current features remain harmful; keep factorization exploratory |
| V5 mechanism control | Full news versus gated context-only -0.000871; interval [-0.001457, -0.000208] | Novelty/lifecycle do not explain the apparent gain |
| V5 versus nonlinear B0 | Full gated news loses 0.008543 log loss to global market-only control | Current V5-A/V5-B are no-go for freezing |
| Pre-17-May news backfill | Zero rows ingested before cutoff; 20,307,169 older publisher-dated rows were later backfills | Cannot form a leakage-safe older news interval |

### Research plan for the next step

1. Keep the sealed v4 collector running through 30 October and audit each complete
   daily partition. Do not inspect confirmatory prices, labels, prevalence or model
   output before the consumption receipt.
2. After the v4 completeness gate passes, write the irreversible consumption receipt,
   prepare point-in-time inputs, build identical future B0-B3 rows and run the
   hash-frozen evaluator exactly once. Apply the preregistered 0.001-nat minimum
   effect, bootstrap, Brier and venue decision rules without modification.
3. Convert the frozen v3.1 and v4-discovery JSON results into paper tables and figures without
   rerunning development selection or holdout evaluation.
4. Write the primary conclusion as a negative incremental-news finding and distinguish
   it from the modest absolute B0 holdout result.
5. Disclose the failed v3 gate, label-blind v3.1 correction, cohort attrition and
   receipt-order deviation in the methods and limitations sections.
6. Run a claim audit, reproducibility check, secret scan and release-rights review.
7. Continue the unchanged 14-market prospective v2.3 collection through 28 September
   only as a separate replication; do not tune it using v3.1 results.
8. Carry the convergence-checked direct nonlinear B0-v5N specification into a new
   label-blind cohort/source/exposure/power audit. It is not yet frozen or confirmed.
9. If news research continues, test only the prespecified 30-minute V5-R family and
   require it to beat both B0-v5N and the identically gated context-only negative
   control in a new development interval.
10. Before calling v5 confirmatory, freeze the exact cohort, source rules, subgroup
    margins, one selected candidate and evaluator, then reserve a new untouched
    interval disjoint from v4. The present v5 results are outcome-informed development
    evidence only.

## 2. Research motivation and problem statement

Prediction markets are designed to aggregate public information into prices. It is
nevertheless uncertain whether structured news signals can improve short-horizon
prediction after conditioning on information already present in price and trading
history.

This question is methodologically difficult because:

- retrospectively retrieved articles may be backdated to publication times at which
  they were not available to the research pipeline;
- capped or interrupted feeds may be mistakenly represented as zero-news intervals;
- random validation can leak future market conditions;
- repeated five-minute observations from the same market are not independent;
- inconsistent price sources can create artificial measured jumps; and
- a large temporal row count can conceal a small number of independent market
  clusters.

The core research problem is therefore:

> Does point-in-time market-relevant news contain incremental predictive information
> about 30-minute absolute prediction-market repricing beyond market history alone,
> when data availability, temporal dependence, source completeness, and model
> selection are controlled prospectively?

## 3. Research objectives

The shared B0/B1 research programme has five objectives:

1. Construct a reproducible, point-in-time dataset linking binary prediction markets,
   executed trades, and associated news.
2. Predict future absolute canonical-YES log-odds jumps at a fixed 30-minute primary
   horizon.
3. Compare a frozen market-only model with an otherwise identical market-plus-news
   model on the same observations and validation folds.
4. Distinguish valid negative evidence from incomplete data and protocol
   contamination.
5. Validate an evaluation protocol that can later support the full KOL-versus-news
   EventX study on a larger market cohort.

Neither study makes a causal claim. The completed historical result estimates
predictive incremental information within its frozen cohort; v2.3 remains a separate
prospective replication.

## 4. Hypotheses

Let B0 denote the market-only model and B1 the market-plus-news model. B1 can be
promoted only if all five preregistered conditions hold:

1. **H1:** `AP(B1) - AP(B0) > 0`.
2. **H2:** `Brier(B0) - Brier(B1) > 0`.
3. **H3:** both improvements are positive in at least four of five outer folds.
4. **H4:** the paired moving-block-bootstrap 95% lower bound for
   `Brier(B0) - Brier(B1)` is above zero.
5. **H5:** `Brier(B0) - Brier(B1) >= 0` separately for Polymarket and Kalshi.

An undefined required fold metric does not count as positive. An undefined aggregate,
bootstrap, or venue metric fails its corresponding promotion condition. Undefined
metrics may still be reported descriptively but cannot be used to promote B1.

## 5. Study scope and schedule

### 5.1 Completed historical primary v3.1

| Component | Frozen specification |
|---|---|
| Venues | Polymarket and Kalshi |
| Cohort | 4,651 markets: 3,832 Kalshi, 819 Polymarket |
| Development | `[2026-05-17, 2026-07-22)` UTC |
| One-shot holdout | `[2026-07-22, 2026-08-08)` UTC; consumed |
| Cadence / horizon | Five minutes / 30 minutes |
| Candidate result | B1 failed H1-H5; B0 selected |
| External observational datasource | Lumid Findata `/retrieve` only |

### 5.2 Secondary prospective v2.3

| Component | Frozen specification |
|---|---|
| Venues | Polymarket and Kalshi |
| Outcomes | Binary contracts, canonical YES side |
| Cohort | 14 frozen markets |
| Composition | 4 Kalshi politics, 5 Polymarket politics, 4 Polymarket other, 1 Polymarket sports |
| Cadence | Five minutes |
| Primary horizon | 30 minutes |
| Secondary horizons | 5, 120, 360 and 1,440 minutes |
| Development | `[2026-08-08, 2026-09-28)` UTC |
| Reconciliation, evaluation and freeze | 28–30 September 2026 |
| One-shot holdout | `[2026-10-01, 2026-10-22)` UTC |
| Finalization | 22–31 October 2026 |
| External observational datasource | Lumid Findata only |

The cohort contains no selected crypto or macro markets. These missing strata will be
disclosed rather than repaired by changing thresholds after selection.

## 6. Data sources and required fields

All official external observations must originate from valid Lumid Findata endpoints.
The saved contract was checked on 17 August 2026 and contained 169 paths and 171 HTTP
operations. Endpoint presence and HTTP success do not by themselves establish data
completeness.

### 6.1 Market metadata

| Data | Lumid endpoint | Main use |
|---|---|---|
| Candidate universe | `GET /api/v1/lqt/universe` | Selection provenance |
| LQT markets | `GET /api/v1/lqt/markets` | Activity and coverage cross-check |
| Events | `GET /prediction-markets/events` | Event grouping and terminal checks |
| Polymarket details | `GET /prediction-markets/markets/polymarket/{condition_id}` | Binary and canonical-YES mapping |
| Kalshi details | `GET /prediction-markets/markets/kalshi/{ticker}` | Binary and canonical-YES mapping |

### 6.2 Executed trades

| Venue | Lumid endpoint | Required fields |
|---|---|---|
| Polymarket | `GET /prediction-markets/trades/polymarket/{condition_id}` | Trade ID, timestamp, token ID, price, size, side and market ID |
| Kalshi | `GET /prediction-markets/trades/kalshi/{ticker}` | Trade ID, timestamp, ticker, YES/NO price, count and taker side |

These records provide canonical prices, returns, momentum, volatility, trade activity,
notional, price age, eligibility information and all forward labels.

### 6.3 News

| Data | Lumid endpoint | Main use |
|---|---|---|
| Broad prospective news | `GET /news/latest` | Append-only capture and completeness audit |
| Targeted news | `GET /news/search` | Frozen market-specific association queries |
| Symbol news | `GET /news/{symbol}` | Conditional supplement for unambiguous symbols |
| News statistics | `GET /news/stats` | Independent coverage audit only |

Required article fields include stable ID or URL, publication time, publisher,
headline, summary, symbol, category and retrieval provenance. The pipeline additionally
records the earliest EventX observation time and response hashes.

Primary feature availability is defined conservatively as:

```text
available_at = max(published_at, first_seen_at)
```

Thus a historically backfilled article cannot enter a feature vector before EventX
first observed it through Lumid.

### 6.4 Conditional data

Lumid also exposes candles, orderbook snapshots, open interest, matched-market pairs,
KOL rosters and histories, sentiment, wallet activity and holder data. Under v2.3:

- candles and orderbooks may support separately reported robustness analyses;
- they cannot replace executed trades in the primary price series;
- sentiment, wallet and holder data are excluded from the frozen feature set; and
- KOL data are ineligible because the association validation failed.

## 7. Methodology

![EventX v2.3 experimental workflow](data/pic/image.png)

### 7.1 Prediction unit and primary price

The prediction unit is a canonical-YES market at a five-minute timestamp. The primary
price is the latest executed canonical-YES trade at or before timestamp `t`.

For each row the pipeline records:

- canonical YES price;
- last trade time;
- `price_age_minutes`;
- market, venue and timestamp; and
- eligibility or exclusion reason.

Midpoints, where available, are analysed separately and are never mixed into the
primary last-trade series.

### 7.2 Outcome definition

Prices are clipped away from zero and one and converted to log-odds. For horizon `h`,
the absolute forward movement is:

```text
delta_h(t) = abs(logit(p[t+h]) - logit(p[t]))
```

The frozen event threshold is:

```text
threshold_h(t) = 4 * sigma_1m_240(t) * sqrt(h / 30)
```

The label equals one when `delta_h(t)` meets or exceeds the threshold. The primary
horizon is 30 minutes. This is a preregistered heuristic event definition and is not
interpreted as a Gaussian four-standard-deviation event.

### 7.3 B0 market features

B0 contains:

- current price log-odds;
- momentum over 5, 30 and 120 minutes;
- realised volatility over 30 and 240 minutes;
- trade count over 60 and 240 minutes;
- notional over 60 and 240 minutes;
- minutes since the latest trade; and
- venue indicator.

Count and notional variables use `log1p`; the remaining variables retain their frozen
transformations.

### 7.4 B1 news features

B1 adds four accepted core-news features:

- associated article count over 60 minutes;
- associated article count over 360 minutes;
- associated article count over 1,440 minutes; and
- `news_symbol_mapped`.

All windows use `available_at` and the already audited news association rule.

### 7.5 Learner

The reference learner is standardised logistic stochastic gradient descent with:

- eight epochs;
- learning rate 0.02;
- L2 penalty 0.0001; and
- shuffle seed 11.

The deliberately simple model focuses the experiment on incremental information rather
than architecture search.

### 7.6 Validation

Development evaluation uses five purged expanding-time folds with held-out market
groups. A 30-minute purge prevents horizon overlap at fold boundaries. B0 and B1 use
identical observation keys and fold assignments.

The primary ranking metric is average precision. Calibration is measured by Brier
score. Uncertainty is estimated using 5,000 paired moving-block bootstrap replicates
with 360-minute blocks stratified by market.

The final report will explicitly state that temporal row count gives precision
conditional on the selected markets; it does not create hundreds of thousands of
independent markets.

### 7.7 Robustness and operational value

Predeclared descriptive analyses include:

- price-age subsets of no more than 30 and 60 minutes;
- whether the model predicts trade arrival rather than latent repricing;
- separate midpoint analysis where point-in-time orderbook coverage is valid;
- venue, market and secondary-horizon results; and
- news latency and missingness summaries.

Because the target is unsigned, the study will not report directional trading profit
and loss. Permitted operational outputs include alert rate, lead time, calibration and
a development-frozen decision-curve analysis.

## 8. Work completed

### 8.0 Completed historical primary v3.1

The v3.1 study is complete. It used 4,651 markets, 7,706,324 development
examples and 1,460,454 OOF comparison rows. B1 underperformed B0 on AP and Brier,
failed all five promotion gates and was excluded from the holdout. Frozen B0 holdout
performance was AP 0.171628, ROC AUC 0.628037 and Brier 0.107107 on 211,718 rows.
The detailed lineage, data-gate correction and disclosed receipt-order deviation are
summarized in Sections 1 and 12–16 and in the frozen artifacts in Section 17.

### 8.1 Historical pilot

The v1 pilot established the initial pipeline and reference model. On 17,540 common
development rows containing 2,027 jump events:

| Model | Average precision | Brier score | Decision |
|---|---:|---:|---|
| B0 market-only | 0.140883 | 0.102669 | Retained reference |
| Market + KOL | 0.130623 | 0.105419 | Rejected |
| Nested gated KOL | 0.136126 | 0.102895 | Rejected |
| Market + rich news | 0.121761 | 0.107002 | Rejected |
| B1 market + core news | 0.142310 | 0.103441 | Rejected: calibration worsened |
| Market + news + KOL | 0.133268 | 0.105973 | Rejected |

A new July 23–30 out-of-time holdout was evaluated once for the frozen B0 model. It
contained 1,410 eligible rows, 13 markets and 130 jumps. B0 achieved average precision
0.135527 and Brier score 0.084190. That holdout is consumed and cannot be rerun or used
for further tuning.

### 8.2 Taxonomy and cohort

- 3,420 candidate markets were assigned corrected categories.
- A 250-row independent blind audit achieved precision 0.9720 and recall 0.9739.
- Exact selection-window reconciliation completed all 3,420 endpoints with zero
  endpoint errors.
- The reconciled selection window contains 30,862 Polymarket and 5,171 Kalshi trade
  records.
- Fourteen markets passed every fixed selection threshold and were frozen.

### 8.3 Association audits

The initial 300-pair mixed news/KOL audit found:

| Source | Precision | Recall | Decision |
|---|---:|---:|---|
| News | 0.9733 | 0.9605 | Passed |
| KOL-v1 | 0.8000 | 0.7317 | Failed |

A fresh 150-pair KOL-v2 audit produced 62 true positives, 12 false positives, 36 false
negatives and 38 true negatives across 148 decided rows, with two uncertain rows.
Precision was 0.8378, recall 0.6327 and F1 0.7209. It failed the fixed gates. All 450
opened pairs are retained in an exclusion ledger and cannot validate a later rule.

The accepted news method is therefore eligible for B1; KOL is not eligible for this
cycle.

### 8.4 Lumid endpoint and data audit

An August service incident produced widespread HTTP 500 responses. By 17 August, the
required route families were responding again. A label-blind rehearsal covering
8–17 August found:

- all 14 market-detail canonical mappings passed;
- all 14 venue-trade integrity checks passed;
- 5,817 canonical-YES trades were retained;
- no selected market had zero trade records;
- all 21 frozen `/news/search` requests remained below the apparent cap;
- `/news/latest` returned exactly 200 rows despite `limit=5000`;
- the earliest retained broad-feed record was on 14 August, leaving 8–13 August
  unresolved; and
- two post-cutoff news records were quarantined.

The rehearsal was correctly frozen as incomplete rather than treated as a successful
news-data gate.

On 28 August, the project used Lumid's read-only `POST /retrieve` materialisation route
to export `news.articles` for `[2026-08-08, 2026-08-28)`. The exact receipt and local
scan agreed on 28,307 rows. They comprised 28,307 unique IDs, 27,957 normalised URLs,
350 repeated-URL rows, 962 source-run IDs and zero malformed, missing-required or
out-of-window rows. The 48,060,537-byte JSONL, SQL, receipt and catalog/source evidence
are hashed in a local manifest.

Cross-path reconciliation used the legacy prospective feed, corrected v2.3 feed,
accepted targeted searches and both label-blind rehearsals. It found 1,903 EventX-
observed in-window URLs, all present in the warehouse. Warehouse-only rows receive the
export completion time as EventX `first_seen_at`; Lumid `ingest_ts` remains provenance
and cannot retrospectively backdate B1. The audit also quarantined 698 rows across 348
URLs with conflicting publication timestamps. This resolves the historical interval
through the snapshot but cannot establish the still-future remainder of
`[2026-08-08, 2026-09-28)`.

### 8.5 Active protocol and integrity work

v2.3 resolved the remaining protocol ambiguities before labels by freezing:

- direct B1-versus-B0 hypotheses;
- the response-cap and ingestion-gap rules;
- conservative point-in-time news availability;
- undefined-metric behaviour;
- the order data gate → synthetic power simulation → labels;
- uniform last-trade prices;
- price-age robustness; and
- the October paper's news-pilot positioning.

The v2.3 verifier currently reports:

- 16 checked artifacts;
- zero failures;
- no labels inspected;
- v1 holdout consumed;
- v2.3 holdout future, reserved and uninspected.

### 8.6 Label-blind feature-readiness audit

The frozen matcher and frozen 60/360/1,440-minute count windows were applied to the
closed August 8–28 snapshot before labels. The audit read warehouse text and timestamps
plus trade timestamps, but no trade prices, labels, outcomes, predictions or holdout
data.

| Diagnostic | Result |
|---|---:|
| Warehouse articles scanned | 28,307 |
| Deduplicated associations | 43 |
| Markets with associations | 2/14 |
| Associations in Clarity Act market | 42/43 |
| Non-zero 60-minute rows | 72/80,640 (0.089%) |
| Non-zero 360-minute rows | 406/80,640 (0.503%) |
| Non-zero 1,440-minute rows | 1,450/80,640 (1.798%) |
| `news_symbol_mapped` | Constant zero |
| Export-completion backfill shock | 22 associations |
| Point-in-time invariance failures | 0 |
| Grid rows with trade age ≤30/≤60/≤240 minutes | 19.43% / 27.50% / 47.78% |
| Median trade age, conditional on a prior trade | 258 minutes |

The accepted matcher remains statistically valid on its blind audit, but the actual
Lumid warehouse presently has a domain-coverage mismatch with the frozen cohort. Most
records are finance/company/crypto news, while many selected markets concern elections,
geopolitics or sport. Consequently, B1 may be nearly identical to B0 in most markets.
This result is descriptive and label-blind; it cannot be used to relax or redesign the
frozen matcher, cohort or feature family.

The original cap/gap contract check, the corrected article-identity/content-version
contract check and the 16-artifact preregistration verifier were also rerun. All passed
with zero failures. The official power simulation was not run because the final data
gate has not closed.

### 8.7 Comprehensive Lumid Studio/FinData audit and re-audit

The August 29 audit found several catalog and retrieval problems. A full September 1
re-audit now shows substantial repair: 13 schemas and 178 tables remain discoverable;
all 178 profiles and all 178 JSON schemas complete; the catalog and
`information_schema` agree on all 22 `news.articles` columns; `/retrieve` is documented
in OpenAPI; JSONL/CSV, CTE/window SQL, empty results and a sorted 1,500-row export work;
and unsupported Parquet receives a clear validation error. The previous `/retrieve`
HTTP 500 outage is no longer reproducible. Unbounded full-text search now returns an
actionable HTTP 400 at the 30-second statement timeout, while a bounded query completes
in about 0.1 seconds.

Five active defects were confirmed. `/news/latest` converts limits `-1` and `0` to one
row and silently clamps `201` or `5000` to 200 without a cursor. All tested Kalshi
candle variants returned HTTP 500, whereas a Polymarket control returned 10 rows.
Two news records were ingested in June 2026 but dated 2028 and 2030, contaminating
`/news/stats`. The lineage-runs endpoint returns zero although `provenance.runs` has
312,096 rows, including 58,724 in the previous 30 days. Finally, all 172 OpenAPI
operations document only HTTP 200 and none defines a typed response body.

The interactive browser service was unavailable, so UI click-through is not claimed.
All programmatic probes were read-only, used non-frozen market samples, and touched no
labels, outcomes, protected prices or holdout data. The reports are under
`data/v2_3_1/lumid_studio_audit_20260901/`; the current narrative and submission-ready
issue list are `LUMID_REAUDIT_2026-09-01.md` and `LUMID_STUDIO_BUG_REPORT.md`.

### 8.8 Historical feasibility implementation

A separate label-blind protocol, `eventx-v3-historical-feasibility-20260830`, now
tests whether a broader historical B1/B0 study is possible without changing v2.3.
It uses the completed `[2026-05-17, 2026-08-08)` interval, requires
`available_at=max(published_at, ingest_ts)`, excludes greater-than-24-hour backfills
from primary feasibility and prohibits labels/outcomes.

The bounded news export passed with 218,392 unique timely articles, zero duplicate
IDs, zero invalid rows and zero out-of-window rows. The strengthened synthetic
contract passes 37 checks with zero failures. Trade activity now uses one-day UTC
chunks, 1,000-key keyset pages and per-chunk checkpoints; metadata uses 100-key
batches and the earliest pre-cutoff snapshot. Raw vendor payloads and resolution
fields are excluded from metadata so the feasibility phase cannot expose outcomes.
Activity gates count distinct trade IDs only within valid venue-native price ranges.
News support deduplicates normalized URLs, excludes timestamp-conflict identities and
counts an association only inside the market's observed trading interval.

After the August 30–31 `/retrieve` outage, the checkpointed runner resumed and passed
both venue activity manifests: 18,635,674 Kalshi retrieved rows across 18,682 pages and
901,028 Polymarket rows across 947 pages. The Kalshi activity output contains
16,802,432 unique ticker keys, but only 9,422 can satisfy both frozen activity gates;
the equivalent Polymarket universe contains 1,576 condition IDs. The first unfiltered
metadata attempt was stopped, hashed and receipted before its exact incomplete
directory was removed. The corrected exporter then completed 95 Kalshi and 16
Polymarket batches, yielding passing manifests for 5,068 and 1,574 earliest pre-cutoff
metadata rows. Checkpoints now bind the filter, key count and SHA-256 fingerprint,
store compact receipts and enforce a 5-GiB disk floor. The final audit uses an
equivalent streaming join rather than holding 16.8 million activity rows in memory.

No historical model is authorized unless all market-breadth, venue, news-support,
concentration and calendar-coverage gates pass and Lumid confirms the semantics of
`ingest_ts`. A failure becomes a descriptive source-coverage result.

The bounded-memory audit completed at `2026-09-01T14:40:02.907825Z`. It found 5,999
eligible markets (5,068 Kalshi and 931 Polymarket), 216,697 deduplicated timely news
documents over 81 usable calendar days, and 341,845 frozen-rule associations. Of the
eligible markets, 1,799 have at least five associations; the largest single-market
share is 1.0865%. Every numeric breadth, support, concentration and calendar gate
passed. At that checkpoint the status was `blocked_pending_ingest_ts_confirmation`
and no label had been opened. The subsequent stricter source-run provenance audit and
versioned v3/v3.1 protocol path resolved this historical checkpoint as described in
Sections 1 and 8.0.

## 9. Secondary prospective v2.3 collection status

Legacy collector PID `94663` remains alive and label-blind under v2.1. Hardened-news
implementation v3 is live under PID `56756`. It clamps the cadence delay to a
non-negative value, runs under `caffeinate`, resumes the same append-only state and
has three restart receipts linking predecessor PID, checkpoint, code, contract and
manifest hashes. The resumed `/news/latest` response is capped, so the checkpoint
correctly remains at `2026-08-31T04:25:00Z` until warehouse reconciliation.

The v3 collector also rejects publication times more than five minutes after
retrieval. By 2 September it had retained 88 append-only invalid-observation rows
covering 68 stable identities. Two predecessor-contaminated identities remain
quarantined; 66 were accepted only on a later poll within the frozen five-minute
tolerance, with `available_at >= published_at`. A corrected audit confirms zero unsafe
unquarantined identities. Repeated unusable returns remain deduplicated by stable
identity and publication time. The six-check source-safety audit passes while correctly
leaving `b1_execution_authorized=false` until censoring is reconciled.

The continuity audit identified 12 distinct greater-than-300-second gaps. Every one
was recovered by a later response below the cap whose unchanged `since` checkpoint
covered the gap start. The warehouse reconciliation covers the original pre-launch
interval, leaving zero unresolved intervals as of that audit snapshot. The new
August 31 onward interval was then exercised through the same recovery path. A bounded
`[2026-08-31T04:20Z, 2026-09-01T14:30Z)` snapshot passed with 871 unique IDs, zero
duplicate IDs, one duplicate-URL row and 65 source-run IDs. Cross-path reconciliation
matched 242 EventX-observed URLs, assigned conservative export-completion first-seen
times to 629 warehouse-only rows, and quarantined one conflicting URL across two rows.
The first refreshed multi-snapshot audit recovered all 22 operational gaps and 20 of
25 collector censoring intervals. On 2 September, a cumulative
`[2026-08-31T04:20Z, 2026-09-02T01:25Z)` export then passed with 3,468 unique IDs,
zero duplicate IDs, six duplicate-URL rows and 90 source-run IDs. Reconciliation
matched 1,025 warehouse rows to endpoint-observed URLs and conservatively assigned
export-completion first-seen times to 2,443 warehouse-only rows. The continuity audit
recovered all 23 operational gaps and 610 additional capped intervals. The database
then contained 630 reconciled intervals; eight later one-minute tail intervals remained
open because collection continued after the export cutoff.

A refreshed bounded pull over `[2026-08-08, 2026-09-02T01:25Z)` passed all 14
market-detail and all 14 trade-integrity checks, retaining 19,359 canonical-YES trades
(17,571 Kalshi, 1,788 Polymarket) with no zero-record market, truncation, saturated
boundary, invalid price or invalid timestamp. Its combined report preserves an
`incomplete` status for the redundant capped `/news/latest` call; the trade component
passed and the independent warehouse evidence supplies the news reconciliation.

Repeated snapshots are now joined through a frozen availability ledger rather than by
using whichever export is newest. Three verified receipts contributed 32,646 rows and
merged to 31,775 warehouse IDs. The ledger preserved an earlier safe receipt for 629
overlapping IDs and quarantined 713 rows across 355 cross-snapshot publication-time
conflict URLs. Its 26-check synthetic/hash verifier passes.

## 10. Current bottlenecks and risks

The completed v3.1 result has no remaining data-execution blocker. Sections 10.1,
10.2 and 10.4–10.6 describe risks to the separate prospective v2.3 replication. The
current primary reporting risks are correct claim scope, holdout attrition and full
disclosure of the receipt-order deviation.

### 10.1 Formal execution blocker: final exact-window closure

`/news/latest` exposes `since`, optional category and limit parameters, but no
documented cursor, offset or upper-time bound. A request can return the newest 200 rows
while omitting older rows after `since`. Repeating the same request cannot establish
complete recovery.

The verified warehouse route and cross-path audit now solve the earlier historical
gap through 28 August. The B1 gate nevertheless remains open because the development
window does not close until 28 September. At that point, the same export must cover the
full half-open interval, all new collector gaps must be reconciled, timestamp conflicts
must remain quarantined, and exact-window trades must close for all 14 markets.

### 10.2 Primary scientific risk: sparse B1 support

The closed-snapshot readiness audit finds only 43 news associations in 2/14 markets,
with 42 in one market. The 60-minute news count is non-zero on only 0.089% of current
grid rows, and the symbol-mapping feature is constant zero. Even a perfectly complete
final export may therefore leave insufficient within-fold and cross-venue variation to
identify a meaningful B1 increment. This is not missing-data zero filling; it is an
observed limitation of the frozen source, cohort and estimand.

The later `[2026-08-31T04:20Z, 2026-09-02T01:25Z)` diagnostic reinforces this result:
3,468 warehouse articles produce only three frozen-rule associations across two
markets, and only one association was endpoint-observed and usable inside the slice.
The point-in-time prefix/future invariance test still passes.

### 10.3 Completed historical-track limitations

The historical track is no longer blocked. Its stricter provenance audit joined every
candidate article to a source run and used conservative availability timing. Version
v3.1 completed after preserving the original v3 zero-notional data-gate failure and
making an exact 19-market pre-outcome correction. The remaining limitations are
scientific rather than operational: count-only news features, source dependence,
holdout attrition to 300 eligible markets, venue heterogeneity and the disclosed
receipt-order deviation. This result remains separate from v2.3.

### 10.4 Legacy collector mismatch

The running v2.1 collector polls with `limit=200` but may advance its checkpoint after
a 200-row response. It does not implement the frozen v2.3 rule that every response at
the cap is potentially censored and must not advance the checkpoint.

### 10.5 Resolved implementation risk: news identity, timing and revisions

Implementation v3 keys stable entities on provider ID or normalised URL, stores
content revisions separately, retains earliest EventX first-seen time and quarantines
publication-time conflicts plus unusable future observations. Its synthetic contract
and frozen-manifest checks pass. The warehouse audit found 348 conflicting URL
entities. The live source later exposed 68 early future-dated identities: 66 became
usable only after timely re-observation and cannot enter features before publication,
while two predecessor-contaminated identities remain quarantined.

### 10.6 Trade polling breadth and staleness

The legacy collector rotates across 3,420 candidate markets although the active cohort
contains 14. This increases observation latency. Bounded venue-trade endpoints make
exact post-window recovery realistic, but a separate focused 14-market collection path
would reduce operational risk.

Only 19.43% of five-minute rows currently have a trade no older than 30 minutes. The
frozen ≤30- and ≤60-minute freshness analyses are therefore substantive diagnostics,
not minor robustness checks.

### 10.7 Effective sample size

The pilot contains only 14 independent market clusters, with roughly two to three
validation markets per market group. This limits generalisation and may produce
unstable fold-level metrics. The study is appropriately framed as a protocol-validation
pilot. A larger Stage C benchmark is required for population-level conclusions.

### 10.8 KOL coverage and association quality

The recent KOL feed remains stale and both candidate association rules failed their
fixed validation gates. KOL is therefore not on the October critical path and cannot
be used to make a confirmatory claim in v2.3.

### 10.9 Lumid source usability

Studio is now usable for catalog discovery and bounded authenticated read queries. The
remaining research-relevant risks are silent `/news/latest` truncation, future-dated
news, and the empty lineage-run listing. OpenAPI still lacks response/error schemas,
and Kalshi candles are broken, although candles are not a frozen EventX input. Preserve
SQL, receipts, row counts, information-schema checks and hashes; treat every 200-row
latest-news response as censored; and quarantine implausible timestamps.

## 11. Proposed mitigation plan

### 11.1 Local implementation work — completed

The hardened label-blind implementation was completed before any development labels were
opened. It:

1. separates stable article identity from content-version identity;
2. tracks earliest `first_seen_at` by stable provider ID or normalised URL;
3. stores content revisions separately;
4. detects and quarantines conflicting publication timestamps;
5. clamps scheduler sleep, runs under `caffeinate`, and records every restart;
6. quarantines and deduplicates implausible future-dated observations;
7. adds synthetic tests for revisions, timestamp changes, URL-only records, future
   timestamps and historical backfill; and
8. merges repeated reconciliation receipts by earliest verified EventX first-seen,
   recomputes availability and quarantines cross-snapshot timestamp conflicts; and
9. preserves all frozen v2.3 scientific decisions.

The hardened collector runs in parallel with PID `94663`. Its restart receipts record
protocol/code/manifest hashes, process lineage and the unchanged checkpoint. The
pre-launch interval is already reconciled by the warehouse snapshot; the new August 31
onward capped interval remains explicitly unresolved rather than zero-filled.

### 11.2 Lumid-dependent recovery and verification

Historical news completeness requires at least one of:

- documented cursor or keyset pagination;
- a `before`/`to` upper-time parameter;
- a bounded bulk export for the missing interval; or
- an endpoint-equivalent warehouse result with schema, key and lineage evidence.

Any recovered export must be reconciled against prospectively collected overlap by
article identifier, timestamps, row counts, duplicates and content hashes.

The `news.articles` result is now materialised with its SQL, retrieval receipt,
source-run fields, catalog evidence and SHA-256 hashes. Feature availability uses
`max(published_at, EventX first_seen_at)`; Lumid `ingest_ts` is provenance only. The
same procedure must be repeated through development close and include the 24-hour
warm-up for the 1,440-minute feature. Repeated URLs remain in the raw export, while
conflicting timestamp entities are explicitly quarantined before feature construction.

Repeated `/news/latest` requests and category partitioning alone are insufficient.

### 11.3 Trade-risk reduction

Maintain the legacy collector but add a focused, label-blind collection/reconciliation
path for the 14 frozen market IDs. At the development cutoff, execute exact bounded
trade pulls over `[2026-08-08, 2026-09-28)` and reconcile them with the prospective
prefixes.

### 11.4 Scientific fallback

If complete news cannot be recovered:

- B0 remains executable;
- B1 is marked `incomplete_due_to_source_coverage`;
- missing news is never filled with zeros; and
- no conclusion is made about whether news provides incremental predictive value.

A search-only news study would require a separate label-blind protocol because it
would change the operational definition of B1.

Sparse news support at final close will be reported directly. It is not permission to
add sources, remap symbols, broaden association terms or replace the frozen cohort in
v2.3. Any redesigned broad-event-news benchmark belongs in a new preregistered study.

## 12. Remaining execution plan

| Date or phase | Required work | Decision gate |
|---|---|---|
| Completed 2 Sep | Freeze v3.1, construct development examples and run B0/B1 once | All H1-H5 failed; B0 frozen |
| Completed 2 Sep | Retrieve/audit historical holdout and run B0 once | Completed with disclosed receipt-order deviation; rerun prohibited |
| Immediate | Generate result tables/figures only from frozen JSON artifacts | No model or threshold changes |
| Immediate | Complete claim, reproducibility, secret and artifact audits | Every result traceable to a hash-locked source |
| Paper drafting | Report negative B1 result, B0 benchmark, source limits and deviations | No causal, KOL, novelty, virality or P&L claim |
| Through 28 Sep | Optionally continue unchanged prospective v2.3 inputs | Separate replication; no tuning from v3.1 |
| After 28 Sep | Decide v2.3 only under its existing source/data gates | Incomplete if exact source coverage fails |

## 13. Current feasibility assessment

| Component | Status | Assessment |
|---|---|---|
| Historical data/provenance | Green | Source-bounded gates and manifests passed |
| Historical development comparison | Complete | B1 negative; B0 selected under all frozen rules |
| Historical holdout | Complete/qualified | B0 evaluated once; receipt-order deviation disclosed |
| Historical statistical breadth | Green/amber | 4,651 development markets, but only 300 with eligible holdout rows |
| Historical claim scope | Pilot | Conditional on Lumid, count-only news features and frozen cohort |
| Prospective v2.3 | Secondary/ongoing | Still closes 28 Sep; protocol unchanged |
| KOL branch | Red | Ineligible after failed audits |
| Novelty and virality | Not tested | Require a new protocol and features |
| Final paper package | Amber | Results complete; writing and reproducibility audit remain |

## 14. Matters for supervisor discussion

1. Confirm that the paper should lead with the completed v3.1 negative incremental-
   news result and describe the 14-market v2.3 study as a secondary replication.
2. Confirm that the v3 failure and separate label-blind v3.1 correction are adequately
   disclosed.
3. Confirm how prominently the pre-receipt prevalence exposure should be described;
   the recommended treatment is a procedural deviation that qualifies the holdout but
   does not alter the already-frozen candidate or development finding.
4. Confirm that the B0 holdout result is presented as modest absolute prediction, not
   evidence for news.
5. Confirm that novelty, virality and KOL are explicitly outside this paper's tested
   claim and deferred to a new protocol.

## 15. Research-integrity status

- Historical v3.1 was preregistered and implementation-frozen before its affected
  outcomes; the original failed v3 branch remains preserved.
- Development B0/B1 ran once, one B0 candidate was frozen, and B1 was not evaluated
  on the holdout.
- The historical holdout is consumed and reruns are prohibited. Its receipt-order
  deviation and truthfulness-only amendment are preserved with hashes.
- The secondary v2.3 protocol remains preregistered; no v2.3 development or October
  holdout label has been generated or inspected.
- The v1 replacement holdout was evaluated once and is consumed.
- Failed association rules and negative model results remain recorded.
- No source outage is treated as zero data.
- No alternative datasource has been silently substituted for Lumid.

## 16. Conclusion

The historical primary experiment is complete. Its answer is not that external news
is universally useless, but that the frozen rolling-count representation of
conservatively available Lumid news did not improve the frozen market-only model for
30-minute absolute repricing. B1 was worse on aggregate AP and Brier, failed every
promotion gate and was therefore excluded from the holdout. B0 retained modest
out-of-time discrimination and reasonable aggregate calibration, with meaningful
venue and freshness heterogeneity.

The strongest contribution is methodological: source-bounded provenance, point-in-
time availability, explicit failed gates, pre-outcome cohort correction, clustered
validation, fixed fallback selection and one-shot evaluation were made auditable.
The paper must also disclose the important limits: count-only news features, no KOL,
novelty or virality test, cohort attrition, a Lumid-only source claim, and the holdout
receipt-order deviation. The immediate task is now reporting and reproducibility, not
additional tuning. Prospective v2.3 may continue unchanged as a secondary replication.

## 17. Key supporting artifacts

- [Complete research and experiment plan](COMPLETE_RESEARCH_PLAN.md)
- [Compact canonical project handoff](CURRENT_STATE.md)
- [Detailed legacy progress archive](PROGRESS.md)
- [V4 frozen protocol](eventx/release/v4/protocol.json)
- [V4 holdout implementation freeze](eventx/release/v4/holdout_implementation_manifest.json)
- [V4 discovery result](data/v4/discovery/models/result.json)
- [V4 novelty/diffusion decomposition](data/v4/exploratory/novelty_diffusion/SUMMARY.md)
- [V5 design candidate](eventx/release/v5/DESIGN_CANDIDATE.md)
- [V5 diagnostic decision report](data/v5/design_diagnostics/DECISION_REPORT.md)
- [V5 historical development report](data/v5/development/DEVELOPMENT_REPORT.md)
- [B0-v5N development specification](data/v5/development/market_baseline_selection_v2/model_spec.json)
- [V5 reduced-news candidate](eventx/release/v5/REDUCED_NEWS_CANDIDATE.md)
- [Older-history source decision](data/v5/label_blind/OLDER_HISTORY_DECISION.md)
- [Historical v3.1 protocol](eventx/release/v3_1_historical_primary/protocol.json)
- [Historical development selection](data/v3_1_historical/primary/development/selection_result.json)
- [Frozen B0 candidate](eventx/release/v3_1_historical_primary/candidate.json)
- [Historical holdout result](data/v3_1_historical/primary/holdout/evaluation_result.json)
- [Historical holdout consumption receipt](data/v3_1_historical/primary/holdout/holdout_consumption_receipt.json)
- [Holdout protocol-deviation disclosure](eventx/release/v3_1_historical_primary/HOLDOUT_PROTOCOL_DEVIATION.md)
- [Historical completion verification](data/v3_1_historical/primary/completion_verification.json)
- [v2.3 preregistration amendment](eventx/release/v2_3/PREREGISTRATION_AMENDMENT.md)
- [v2.3 machine-readable protocol](eventx/release/v2_3/protocol.json)
- [v2.3 news collection contract](eventx/release/v2_3/news_collection_contract.json)
- [v2.3 implementation-v2 amendment](eventx/release/v2_3_1/IMPLEMENTATION_AMENDMENT.md)
- [v2.3 hardened implementation manifest](eventx/release/v2_3_2/implementation_manifest.json)
- [v2.3 availability-ledger manifest](eventx/release/v2_3_3/implementation_manifest.json)
- [Known-source safety audit](data/v2_3_2/source_safety_20260902/report.json)
- [Latest cumulative warehouse snapshot](data/v2_3_1/reconciliation/news_warehouse/20260831T042000Z_20260902T012500Z/manifest.json)
- [Latest news continuity audit](data/v2_3_1/continuity/gap_audit_20260902.json)
- [Latest frozen-cohort trade drill](data/v2_3_1/reconciliation/frozen_cohort_20260808_20260902/audit_report.json)
- [Latest label-blind readiness slice](data/v2_3_1/feature_readiness_20260902_merged/audit_report.json)
- [Merged availability receipt](data/v2_3_2/availability_ledger_20260902/merge_manifest.json)
- [Tracked warehouse/continuity evidence receipt](eventx/release/v2_3_1/WAREHOUSE_RECONCILIATION_EVIDENCE.md)
- [Label-blind feature-readiness audit](data/v2_3_1/feature_readiness_20260829/audit_report.json)
- [Lumid Studio / FinData re-audit](LUMID_REAUDIT_2026-09-01.md)
- [Lumid Studio warehouse re-audit](data/v2_3_1/lumid_studio_audit_20260901/report.json)
- [Lumid Studio REST re-audit](data/v2_3_1/lumid_studio_audit_20260901/rest_report.json)
- [Lumid targeted follow-up](data/v2_3_1/lumid_studio_audit_20260901/followup_report.json)
- [Lumid Studio bug report](LUMID_STUDIO_BUG_REPORT.md)
- [Lumid open bugs only](LUMID_OPEN_BUGS_2026-09-01.md)
- [Lumid retrieve incident and recovery](LUMID_RETRIEVE_BUG_REPORT.md)
- [Historical feasibility protocol](eventx/release/v3_historical/feasibility_protocol.json)
- [Historical feasibility implementation manifest](eventx/release/v3_historical/feasibility_implementation_manifest.json)
- [Abandoned metadata-attempt receipt](eventx/release/v3_historical/ABANDONED_KALSHI_METADATA_ATTEMPT_20260901.json)
- [Historical feasibility runner state](data/v3_historical/feasibility/runner_state.json)
- [Historical feasibility contract tests](data/v3_historical/feasibility/contract_test_report.json)
- [Warehouse snapshot manifest](data/v2_3_1/reconciliation/news_warehouse/20260808T000000Z_20260828T000000Z/manifest.json)
- [Cross-path reconciliation manifest](data/v2_3_1/reconciliation/news_warehouse/20260808T000000Z_20260828T000000Z/reconciled/reconciliation_manifest.json)
- [News continuity audit](data/v2_3_1/continuity/gap_audit_20260828.json)
- [v2.3 locked manifest](eventx/release/v2_3/preregistration_manifest.json)
- [August 8–17 Lumid rehearsal report](data/v2_2/planning/lumid_subwindow_20260808_20260817/AUDIT_REPORT.md)
- [News truncation diagnosis](data/v2_2/planning/NEWS_TRUNCATION_DIAGNOSIS_20260817.md)
- [Frozen 14-market cohort](data/v2_1/cohort/selected_markets.jsonl)
- [Taxonomy audit](data/v2_1/taxonomy/audit_report.json)
- [v1 final research report](eventx/release/v1/FINAL_RESEARCH_REPORT.md)
