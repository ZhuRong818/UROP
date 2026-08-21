# EventX Research Progress Report

**Student:** _[Insert name]_  
**Supervisor:** _[Insert supervisor name]_  
**Reporting date:** 21 August 2026  
**Project:** EventX — Incremental Information in Prediction-Market Repricing  
**Active protocol:** `eventx-v2.3-news-availability-clarifications-20260817`  
**Target completion date:** 31 October 2026

## 1. Executive summary

EventX studies whether information external to a prediction market contains
incremental, point-in-time predictive information about subsequent market repricing.
The longer-term research programme concerns key-opinion-leader (KOL) social-media
activity beyond market history and news. The active October pilot has been narrowed,
before opening any development labels, to the prerequisite comparison:

```text
B0: market-history features
B1: market-history features plus market-relevant news
```

The current research question is whether B1 improves the prediction and calibration
of 30-minute absolute price jumps relative to B0. This is positioned as a prospective
protocol-validation study rather than a complete test of the KOL hypothesis.

Substantial progress has been made. A historical pilot and one replacement
out-of-time evaluation have been completed; a corrected taxonomy has passed an
independent audit; 3,420 candidate markets have been reconciled; a 14-market
Polymarket/Kalshi cohort has been frozen; the news association method passed its audit;
two KOL association candidates failed and were appropriately excluded; and the active
v2.3 protocol now passes a 16-artifact integrity verifier with no failures. No v2.3
development or holdout labels, prevalence values, predictions, or model metrics have
been created or inspected.

The primary blocker is not modelling. It is proving complete, point-in-time news
coverage. Lumid's `/news/latest` endpoint returned exactly 200 rows despite a larger
requested limit and exposes no documented cursor, offset, or upper-time parameter.
The running legacy collector is alive but does not implement the v2.3 censoring
contract. A corrected collector should therefore be versioned and launched in
parallel, while the earlier interval must be recovered through a Lumid cursor,
bounded-time endpoint, or endpoint-equivalent export. If news completeness cannot be
established, B1 will be reported as incomplete rather than as a negative result; the
market-only B0 branch remains feasible.

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

The active study has five objectives:

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

The active study does not make a causal claim. It estimates predictive incremental
information within the prospectively frozen cohort.

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

## 9. Current collection status

At the `2026-08-21T06:46:59Z` health snapshot, legacy collector PID `94663` was alive,
label-blind and operating under the superseded v2.1 protocol:

| Source | Records written | Cumulative errors | Latest event time |
|---|---:|---:|---|
| Market-event snapshots | 147,146 | 12 | Not consistently supplied |
| News | 4,196 | 4,130 | 2026-08-21 04:36 UTC |
| Kalshi trades | 17,707 | 1,512 | 2026-08-21 04:19 UTC |
| Polymarket trades | 61,919 | 243,296 | 2026-08-21 05:25 UTC |
| KOL posts | 1,853 | 4,129 | 2026-07-25 12:34 UTC |

The error totals include the earlier Lumid incident and should not be interpreted as
current error rates. Recent requests were succeeding, but request success alone does
not prove complete interval coverage. The v2.3-compliant news collector has not yet
been launched.

## 10. Current bottlenecks and risks

### 10.1 Primary blocker: historical news completeness

`/news/latest` exposes `since`, optional category and limit parameters, but no
documented cursor, offset or upper-time bound. A request can return the newest 200 rows
while omitting older rows after `since`. Repeating the same request cannot establish
complete recovery.

This prevents the B1 data-sufficiency gate from passing. It does not invalidate the
trade rehearsal.

### 10.2 Legacy collector mismatch

The running v2.1 collector polls with `limit=200` but may advance its checkpoint after
a 200-row response. It does not implement the frozen v2.3 rule that every response at
the cap is potentially censored and must not advance the checkpoint.

### 10.3 News record-identity edge case

The current v2.3 implementation combines a provider identifier with the hash of the
complete response row. A changed timestamp or content can therefore produce a new key
rather than being detected as a revision of the same article. This should be fixed in
a new label-blind implementation version before live launch, because v2.3's files are
already hash-locked.

### 10.4 Trade polling breadth

The legacy collector rotates across 3,420 candidate markets although the active cohort
contains 14. This increases observation latency. Bounded venue-trade endpoints make
exact post-window recovery realistic, but a separate focused 14-market collection path
would reduce operational risk.

### 10.5 Effective sample size

The pilot contains only 14 independent market clusters, with roughly two to three
validation markets per market group. This limits generalisation and may produce
unstable fold-level metrics. The study is appropriately framed as a protocol-validation
pilot. A larger Stage C benchmark is required for population-level conclusions.

### 10.6 KOL coverage and association quality

The recent KOL feed remains stale and both candidate association rules failed their
fixed validation gates. KOL is therefore not on the October critical path and cannot
be used to make a confirmatory claim in v2.3.

## 11. Proposed mitigation plan

### 11.1 Local implementation work

Create a new label-blind implementation version before any development labels are
opened. The patch should:

1. separate stable article identity from content-version identity;
2. track earliest `first_seen_at` by stable provider ID or normalised URL;
3. store content revisions separately;
4. detect and quarantine conflicting publication timestamps;
5. add synthetic tests for article revisions, timestamp changes, URL-only records and
   historical backfill; and
6. preserve all frozen v2.3 scientific decisions.

The corrected collector should then be launched in parallel with PID `94663`. Its
launch receipt should record protocol/code hashes, process ID, start time, initial
checkpoint, output path and the unresolved pre-launch interval. The legacy process
should remain preserved as provenance evidence.

### 11.2 Lumid-dependent recovery

Historical news completeness requires at least one of:

- documented cursor or keyset pagination;
- a `before`/`to` upper-time parameter;
- a bounded bulk export for the missing interval; or
- an endpoint-equivalent warehouse result with schema, key and lineage evidence.

Any recovered export must be reconciled against prospectively collected overlap by
article identifier, timestamps, row counts, duplicates and content hashes.

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

## 12. Remaining execution plan

| Date or phase | Required work | Decision gate |
|---|---|---|
| Immediate | Version-fix article identity and launch compliant collector in parallel | No label access |
| Immediate–27 Sep | Continue market/news capture and pursue Lumid bounded recovery/export | Preserve all gaps and provenance |
| 28 Sep | Close development window and reconcile exact market/news inputs | Stop if completeness fails |
| 28 Sep | Freeze the label-blind data-sufficiency report | Zero unresolved B1 censoring intervals required |
| 28–29 Sep | Run and freeze synthetic 14-market power simulation | May disclose limitations but cannot alter protocol |
| 29–30 Sep | Construct labels/features, run B0/B1 once and apply H1–H5 | Freeze B1 if all pass; otherwise B0 |
| 1–21 Oct | Maintain sealed prospective holdout | No model selection or outcome inspection |
| 22 Oct | Reconcile holdout and evaluate frozen candidate once | Write consumption receipt |
| 22–31 Oct | Final report, datasheet, evidence manifests and reproducibility package | Internal completion by 31 Oct |

## 13. Current feasibility assessment

| Component | Status | Assessment |
|---|---|---|
| Research design and leakage control | Green | Frozen and verified |
| Taxonomy and cohort | Green | Completed and frozen |
| Trade endpoint feasibility | Green | All 14 rehearsal checks passed |
| Full development trade completeness | Amber | Exact final reconciliation pending |
| News association method | Green | Passed independent audit |
| Prospective v2.3 news collection | Red/amber | Correct implementation not yet running |
| Historical broad-news completeness | Red | Pagination/export solution required |
| KOL branch | Red | Ineligible after failed audits |
| Statistical breadth | Amber | Suitable for pilot, not population-wide claims |
| Development labels | Sealed | Correctly uncreated and uninspected |
| October holdout | Sealed | Reserved for one evaluation |
| October completion | Conditional | Feasible if news recovery is resolved promptly |

## 14. Matters for supervisor discussion

1. Confirm that the October paper should remain a B1-versus-B0 news
   protocol-validation pilot, with the KOL hypothesis deferred.
2. Confirm a label-blind implementation amendment to correct article identity before
   launching the compliant news collector.
3. Support escalation to Lumid for cursor access, bounded export, or warehouse data
   covering the unresolved development interval.
4. Confirm that B1 should be reported as incomplete, rather than negative, if complete
   news recovery is unavailable by the data gate.
5. Confirm that the 14-market scope and associated claim limitations are acceptable
   for the October deliverable.

## 15. Research-integrity status

- The active v2.3 protocol is preregistered and verifies with zero failures.
- Frozen protocol and manifest files have not been modified.
- No v2.3 development or holdout labels have been generated or inspected.
- The v1 replacement holdout was evaluated once and is consumed.
- The October holdout is future, reserved and uninspected.
- Failed association rules and negative model results remain recorded.
- No source outage is treated as zero data.
- No alternative datasource has been silently substituted for Lumid.

## 16. Conclusion

The project has progressed from an exploratory historical pilot to a substantially
stronger prospective, multi-venue protocol. The central research design, market cohort,
taxonomy, news association method, price definition, model comparison, statistical
tests and holdout rules are now fixed. Trade recovery appears feasible.

The decisive unresolved issue is the completeness and point-in-time validity of news
data. The next priority is therefore to version-correct and launch the compliant news
collector while obtaining a Lumid-supported historical recovery path. Resolving that
issue will permit the preregistered B1-versus-B0 experiment to proceed. Failure to
resolve it will produce an explicitly incomplete news branch rather than an invalid or
overstated scientific conclusion.

## 17. Key supporting artifacts

- [Complete research and experiment plan](COMPLETE_RESEARCH_PLAN.md)
- [Compact canonical project handoff](CURRENT_STATE.md)
- [Detailed legacy progress archive](PROGRESS.md)
- [v2.3 preregistration amendment](eventx/release/v2_3/PREREGISTRATION_AMENDMENT.md)
- [v2.3 machine-readable protocol](eventx/release/v2_3/protocol.json)
- [v2.3 news collection contract](eventx/release/v2_3/news_collection_contract.json)
- [v2.3 locked manifest](eventx/release/v2_3/preregistration_manifest.json)
- [August 8–17 Lumid rehearsal report](data/v2_2/planning/lumid_subwindow_20260808_20260817/AUDIT_REPORT.md)
- [News truncation diagnosis](data/v2_2/planning/NEWS_TRUNCATION_DIAGNOSIS_20260817.md)
- [Frozen 14-market cohort](data/v2_1/cohort/selected_markets.jsonl)
- [Taxonomy audit](data/v2_1/taxonomy/audit_report.json)
- [v1 final research report](eventx/release/v1/FINAL_RESEARCH_REPORT.md)
