# EventX complete research and experiment plan

**Program:** EventX — incremental social-media information in prediction-market price discovery  
**Planning status:** consolidated umbrella plan; not itself a frozen protocol  
**Created:** 2026-08-10  
**Last revised:** 2026-09-10 (V5 v1.1 routing and protocol revision)
**Completed primary experiment:** `eventx-v3.1-historical-primary-20260902`
**Active confirmatory experiment:** `eventx-v4-confirmatory-polymarket-20260902`
**Secondary prospective experiment:** `eventx-v2.3-news-availability-clarifications-20260817`
**Internal deadline for the active cycle:** 2026-10-31  

**Current V5 execution design:**
[`PROTOCOL_V1_1.md`](eventx/release/v5/PROTOCOL_V1_1.md). This is the self-contained
revised target/source/model/control/development/confirmation contract, **not yet an
executable research freeze**. The v1 daily-block inference screen failed; multi-day
candidates require validation, source certification and final family approval remain
open. No new V5 labels may be opened. V5 baseline replication is now a separate
finding, while failed news gates still stop the sole news candidate.

**Historical routing:** the v2.3-specific sections below, including the 14-market
cohort, AP/Brier hierarchy, September 28 cutoff and October 1 freeze, describe that
separate legacy/secondary branch. They are **not V5 instructions**. Earlier V5
proposal paragraphs are design lineage where superseded by v1.1. V4 remains governed
only by its unchanged frozen manifests. The October 31 V4 deadline is not an invented
V5 completion date.

This document consolidates the research goals, required data, methods, experiments,
execution sequence, statistical tests, integrity controls, deliverables, and longer-term
benchmark path. It is a planning and coordination document. It does **not** modify or
supersede the sealed v1 artifacts or the consumed v1 holdout. The frozen v3.1 protocol
controls the completed historical result. The frozen v4 design, cohort/window and
model manifests control the active future confirmation. The frozen v2.3
preregistration continues to control its separate prospective replication; v2.2 and
v2.1 remain immutable lineage.

The controlling sources for an actual run remain:

- [`eventx/release/v4/protocol.json`](eventx/release/v4/protocol.json);
- [`eventx/release/v4/design_manifest.json`](eventx/release/v4/design_manifest.json);
- [`eventx/release/v4/preregistration_manifest.json`](eventx/release/v4/preregistration_manifest.json);
- [`eventx/release/v4/model_freeze_manifest.json`](eventx/release/v4/model_freeze_manifest.json);
- [`eventx/release/v4/holdout_implementation_manifest.json`](eventx/release/v4/holdout_implementation_manifest.json);
- [`eventx/release/v2_3/protocol.json`](eventx/release/v2_3/protocol.json);
- [`eventx/release/v2_3/PREREGISTRATION_AMENDMENT.md`](eventx/release/v2_3/PREREGISTRATION_AMENDMENT.md);
- [`eventx/release/v2_3/preregistration_manifest.json`](eventx/release/v2_3/preregistration_manifest.json);
- [`eventx/release/v2_3/news_collection_contract.json`](eventx/release/v2_3/news_collection_contract.json);
- the sealed v2.2 and v2.1 protocols and manifests as superseded lineage;
- [`eventx/release/v2/PREREGISTRATION.md`](eventx/release/v2/PREREGISTRATION.md), except
  where the v2.1, v2.2 and v2.3 amendments explicitly supersede it;
- frozen manifests under `data/v2_1/`; and
- [`CURRENT_STATE.md`](CURRENT_STATE.md), the compact canonical live handoff; and
- [`PROGRESS.md`](PROGRESS.md), the legacy detailed history consulted only when needed.

If this document conflicts with a frozen artifact, the frozen artifact wins. Any change
to the active confirmatory experiment must be made through a new, label-blind,
versioned preregistration before the affected labels or metrics are inspected.

---

## 1. Executive research objective

EventX tests whether time-stamped KOL social-media activity contains incremental,
point-in-time predictive information about future prediction-market repricing after
conditioning on information already observable in market history and news.

The primary estimand is predictive, not causal:

> How much out-of-sample improvement, if any, does a frozen KOL feature family add to
> a frozen market-plus-news model for future absolute log-odds price jumps?

The program has four deliberately separated deliverables:

1. **Completed historical primary (v3.1):** a point-in-time, source-bounded B1-versus-
   B0 experiment over 4,651 markets. B1 failed all promotion gates; B0 was frozen and
   evaluated once on the historical holdout.
2. **Secondary prospective pilot (v2.3):** a leakage-safe, preregistered experiment on
   the frozen 14-market Polymarket/Kalshi cohort, continuing toward October 31, 2026.
3. **Active v4 confirmation:** a 470-market/470-cluster Polymarket future test of
   market history versus news volume, semantic relevance, market-relative novelty and
   cross-publisher diffusion over `[2026-09-06, 2026-10-30)`. All four models are
   frozen and its future outcome remains untouched.
4. **Full EventX benchmark:** a later, broader, multi-category and longer-window
   benchmark with redundant Lumid acquisition paths, greater market-level sample size,
   stronger microstructure coverage, a reusable Feature Track, and an extensible
   Rehydration Track.
5. **V5 design cycle:** a separate, not-yet-frozen residual-news architecture
   motivated by opened historical diagnostics. It cannot alter v4 and will require a
   new untouched confirmation sample.

The v3.1 result is the completed historical pilot, not the full EventX/KOL benchmark.
The v2.3 pilot may still provide a prospective replication finding.

The October paper/report is positioned as **“A prospective test of whether news
quality and diffusion predict short-horizon prediction-market repricing.”** Its
primary v4 conclusion concerns B3 versus B0; v3.1 supplies the count-only negative
discovery result and absolute B0 benchmark. The broader KOL objective remains the
EventX program direction and is explicitly deferred because KOL-v2 failed its
association validation threshold.

### Active v4 plan

V4 preserves the audited association membership and inherited 30-minute jump target,
but uses an interpretable nested ladder:

- B0: 12 executed-market history features;
- B1: B0 plus rolling news volume;
- B2: B1 plus frozen semantic relevance and seven-day market-relative novelty; and
- B3: B2 plus publisher diversity and exact-headline cross-publisher diffusion.

The discovery run is complete and negative: on 745,443 OOF rows, log loss was
0.459158 for B0 and 0.465617 for B3, giving -0.006459 nats/row improvement. The paired
discovery interval was `[-0.007411, -0.005545]`. B1 and B2 also underperformed B0.
This result cannot modify the already-frozen future test.

A post-freeze exploratory decomposition on the same historical OOF rows further
separates the additions. B2 versus B1 produced -0.000287 nats/row log-loss
improvement with paired interval `[-0.000807, 0.000235]`, while B3 versus B2 produced
-0.003671 with interval `[-0.005767, -0.001892]`. The former is compatible with no
effect; the latter is historically worse. Small AP gains do not override the proper-
score result. These diagnostics cannot alter the frozen confirmation and must not be
described as true social-virality analysis.

The v4 primary cohort contains 470 active, positive-volume Polymarket binary-YES
conditions ending on or after 30 October. Its sole holdout is
`[2026-09-06, 2026-10-30)`. A positive primary result requires B3-vs-B0 log-loss
improvement of at least 0.001 nats/row, a paired event/time bootstrap lower bound
above zero, Brier improvement no worse than -0.0005 and no negative eligible-venue
estimate. All B0-B3 models must be evaluated on identical rows after a consumption
receipt. The 29-check pre-holdout verifier passes.

The complete holdout implementation is also frozen before 6 September. Its enforced
order is sealed collection → source-completeness gate → irreversible consumption
receipt → point-in-time preparation → sealed feature/label matrix → one-shot
evaluation. Synthetic checks cover label and trade-arrival construction, future-
append invariance, frozen-model scoring, the event-cluster/360-calendar-minute
bootstrap and warehouse receipt validation. Missing or hash-invalid partitions stop
the branch rather than becoming zero-news observations.

V4 measures cross-publisher diffusion, not social virality: validated Lumid data has
no engagement, view, repost, share or comment fields. Kalshi is excluded from the v4
primary confirmation because current roster/detail/warehouse metadata could not be
reconciled source-safely; it is deferred to a source-repaired external replication.

### Current research direction and minimal-change rule

The long-run scientific direction remains incremental KOL information beyond market
history and news. The completed v3.1 historical primary tested B1 versus B0 under the
same core target and feature logic. B1 worsened aggregate AP and Brier score, improved
both in zero of five folds and failed all H1-H5 conditions; B0 was therefore frozen
and evaluated once. The separate active v2.3 prospective experiment is
**B1 market-plus-news versus B0 market-only**, because the fresh KOL-v2 audit
failed its fixed association gates. B3, the KOL null tests, and T5 are currently
ineligible; they may reopen only under a genuinely new, label-blind KOL-v3 rule and a
fresh audit excluding all 450 opened pairs.

The label-blind v2.3 amendment preserves every v2.2 cohort, measurement, model, metric,
date and holdout decision. It adds only the news censoring/availability contract,
explicit B1-versus-B0 hypotheses, conservative undefined-metric behavior, corrected
power-simulation order, required threshold language and October-study positioning. If
exact Lumid trade and news coverage cannot be recovered and frozen, the
correct outcome is `incomplete_due_to_source_coverage`, not a substituted datasource or
a weakened experiment.

### Proposed v5 residual-news direction

Historical diagnostics show that v4's damage is concentrated where news is present,
not across the no-news majority. On the exact 745,443 OOF rows, B3-versus-B0
log-loss improvement was -0.000029 on 498,214 no-news rows but -0.034353 when the
latest news was 0–30 minutes old. Within that recent band, relevance/novelty alone
improved B2 over B1 by +0.001321. Extreme negative B3 logit corrections below -1
were particularly harmful (-0.250544 per row). In addition, 13/16 news coefficients
changed sign across fold fits and constant-rate SGD oscillated materially across
epochs. A factorized trade-arrival/conditional-repricing feasibility run did not
rescue the current B3 representation.

The residual architecture was then implemented on 364,903 sequential OOF rows from
folds 3–5. Time to terminal improved a matched B0 by +0.002965 log loss. A converged
nonlinear gated residual initially improved the linear B0-v5 by +0.009614, but its
context-only negative control improved by +0.010485. Adding volume/age, quality/age,
lifecycle/age or the full news set supplied no gain over context-only; full news was
worse by -0.000871 with interval `[-0.001457, -0.000208]`.

A global nonlinear market-only control was stronger still: +0.018157 versus B0-v5,
interval `[0.014238, 0.021705]`, and +0.008543 over the full gated-news model. This
shows that the apparent residual gain was predominantly nonlinear market calibration,
not evidence for news novelty or lifecycle.

A versioned direct-versus-stacked market-only comparison then selected direct
nonlinear B0-v5N. Direct B0-v5N achieved log loss 0.428513, Brier 0.135783 and AP
0.278015 on the same 364,903 rows. It improved log loss over stacked B0-v5N by
+0.003611, paired interval `[0.001359, 0.005694]`, and over linear B0-v5 by +0.021768.
The only non-converged original fit was preserved and repaired in a new artifact; it
converged in 512/2,000 iterations with maximum prediction change 0.00004109.

The current market baseline candidate is therefore:

```text
p0 = direct B0-v5N(low-complexity nonlinear market history,
                    time to scheduled terminal)
```

Four-knot degree-two quantile splines are fit on training partitions only for price,
momentum, volatility, staleness and time-to-terminal variables. Count/notional inputs
remain log-linear. Inner-fold log loss selects `C in {0.001, 0.01, 0.1}` for a
deterministic converged L2 logistic solver.

The next proposed news model is V5-R, not the failed broad family:

```text
E30 = any valid associated article conservatively available in (t-30m, t]
p   = sigmoid(logit(p0) + E30 * kappa * residual(recent relevance-novelty,
                                                 age, capped count,
                                                 one terminal-time interaction))
```

Publisher diffusion and lifecycle are excluded from the primary V5-R family. The
residual learner receives cross-fitted `p0`, trains only on exposed rows and is
constrained to equal B0-v5N exactly when `E30=0`. An identically gated context-only
model is mandatory. V5-R must beat both B0-v5N and that negative control; otherwise
conditional market recalibration cannot be called news information. The opened
May–July data cannot be used again to choose variables or thresholds. V5 requires a
new source-valid development interval and a separate untouched confirmation interval
disjoint from protected v4. See
[`eventx/release/v5/DESIGN_CANDIDATE.md`](eventx/release/v5/DESIGN_CANDIDATE.md) and
[`eventx/release/v5/REDUCED_NEWS_CANDIDATE.md`](eventx/release/v5/REDUCED_NEWS_CANDIDATE.md).

The complete linear-B0/B0-v5N/C5-R/V5-R evaluator is frozen before new development
labels. B0-v5N replication is reported first, followed by V5-R versus B0-v5N and
V5-R versus C5-R. This ordering does not permit intermediate model changes. Failure
of either news comparison closes the v5 news branch; no window extension, feature or
interaction search, relevance redefinition, semantic replacement or
diffusion/lifecycle rescue is allowed within v5.

A label-blind source probe rules out manufacturing that interval from older Lumid
records. The earliest news ingestion is `2026-05-17T06:42:40.084691Z`, and zero news
rows were ingested before 17 May. Although 20,307,169 articles carry older publisher
dates, they were backfilled later; assigning them to those old dates would leak
retrospective availability. Therefore pre-17-May history is ineligible for an
incremental-news experiment. The source decision is recorded in
[`data/v5/label_blind/OLDER_HISTORY_DECISION.md`](data/v5/label_blind/OLDER_HISTORY_DECISION.md).

---

## 2. Research goals

### G1 — Build a leakage-safe prediction-market research artifact

Create a versioned dataset linking binary canonical-YES prediction-market observations
to point-in-time market, news, and KOL features with frozen labels, split indices,
associations, provenance, and evaluation code.

### G2 — Measure future repricing risk (T1)

Predict whether the absolute change in canonical-YES log-odds price over a fixed future
horizon exceeds an adaptive volatility-scaled threshold.

### G3 — Measure incremental information (T3, primary scientific goal)

Compare a fixed ladder on identical rows and splits:

- B0: market history only;
- B1: B0 plus core news;
- B2: B0 plus sparse KOL features, diagnostic only; and
- B3: B0 plus core news plus KOL features residualized from B0+B1.

The historical EventX comparison is B3 versus B1. Because B3 is ineligible after the
KOL-v2 audit, the active v2.3 confirmatory comparison is directly preregistered as B1
versus B0 at the 30-minute horizon on identical rows and splits.

The separate v4 ladder reuses the B0/B1 interpretation but defines B2 as
relevance/novelty and B3 as relevance/novelty plus publisher diffusion. These v4 names
do not reactivate KOL and are controlled only by the v4 protocol.

### G4 — Localize any KOL signal (T5, conditional)

If and only if B3 passes every development promotion gate, estimate per-KOL
out-of-fold lift, temporal stability, category/venue coverage, and false-discovery-rate
controlled significance.

### G5 — Measure operational value without inventing trading direction

For the absolute-jump target, report alert rate, lead time, calibration, and a
development-frozen decision-curve/net-benefit analysis. Directional P&L is unavailable
in v2.3 because the target predicts movement magnitude, not whether to buy YES or NO.
A trading study requires a separate preregistered signed target.

### G6 — Quantify coverage, missingness, and robustness

Measure how conclusions change across venues, categories, horizons, liquidity regimes,
price sources, missing-source conditions, and reasonable predeclared robustness checks.

### G7 — Produce a reusable and responsible release

Package identifiers, features, labels, associations, splits, evaluation code,
datasheets, manifests, and verification tools without redistributing restricted raw
tweet or news text.

---

## 3. Research questions and hypotheses

### Primary question

The v2.3 confirmatory question is whether B1 improves both average precision and Brier
score over B0 for 30-minute absolute log-odds jump prediction under the same
leakage-safe folds, promotion logic, and future October holdout contract. The original
B3-versus-B1 KOL question is deferred because KOL-v2 failed its association gate.

### Secondary questions

1. Does B1 improve over B0?
2. Does KOL activity add ranking information, calibration information, both, or neither?
3. Does any lift persist at 5, 120, 360, and 1,440 minutes?
4. Is any apparent KOL lift stronger than stratified assignment and timestamp nulls?
5. Is performance stable across venue, market, category, time block, liquidity, and
   price-source strata?
6. If B3 promotes, which handles contribute stable out-of-sample lift after FDR control?
7. If a candidate promotes, does it improve frozen non-trading alert/decision utility?

### Active v2.3 confirmatory hypotheses

- **H1_v2.3:** `AP(B1) - AP(B0) > 0`.
- **H2_v2.3:** `Brier(B0) - Brier(B1) > 0`.
- **H3_v2.3:** both H1 and H2 improvements are positive in at least four of five
  outer folds.
- **H4_v2.3:** the paired moving-block-bootstrap 95% lower bound for
  `Brier(B0) - Brier(B1)` is above zero.
- **H5_v2.3:** `Brier(B0) - Brier(B1) >= 0` separately in both venues.

All five conditions are required for B1 promotion. Failure is a valid negative result
when data are complete. The old B3-versus-B1 H1–H6 are historical lineage hypotheses
and do not run in v2.3; the KOL-specific H6 and null tests remain ineligible.

---

## 4. Scope and claim boundaries

### Active v2.3 scope

- Venues: Polymarket and Kalshi.
- Outcomes: binary contracts, canonical YES side only.
- Frozen cohort: 14 markets.
- Frozen composition: four Kalshi politics, five Polymarket politics, four Polymarket
  other, and one Polymarket sports market.
- Missing strata: no selected crypto or macro markets.
- Cadence: five minutes.
- Horizons: 5, 30, 120, 360, and 1,440 minutes.
- Primary horizon: 30 minutes.
- Development: 2026-08-08 through 2026-09-27 UTC.
- Label-blind reconciliation and candidate-freeze buffer: 2026-09-28 through
  2026-09-30 UTC.
- Holdout: 2026-10-01 through 2026-10-21 UTC.
- Finalization: 2026-10-22 through 2026-10-31 UTC.

### Claims permitted from v2.3

- Results for the frozen 14-market prospective cohort.
- Pooled results with mandatory venue-stratified diagnostics where defined.
- A protocol-validation or pilot reference finding.
- Explicitly qualified negative or underpowered findings.

### Claims prohibited from v2.3

- Representation of the sample as category-complete or market-universe representative.
- Category claims for crypto or macro.
- Broad causal claims about KOL influence.
- Claims of complete historical orderbook coverage.
- Claims that a stylized backtest is a deployable strategy.
- Claims that v2.3 is the completed deep-historical EventX benchmark.

---

## 5. Program stages

### Stage A — Closed v1 pilot

Purpose: establish the first end-to-end artifact, expose failure modes, and freeze a
reference result. The v1 holdout is consumed and may never be rerun or reused for
tuning.

### Stage B — Active v2.3 prospective experiment

Purpose: run a fresh, label-blindly selected, multi-venue prospective cycle under the
October deadline. All cohort, taxonomy, association, label, feature, candidate, and
holdout gates must be respected. The current route is B1 versus B0; the KOL branch is
closed unless a separately preregistered and freshly audited KOL-v3 rule passes before
any affected label is opened.

### Stage C — Full EventX benchmark extension

Purpose: expand market-level breadth, category representation, temporal coverage,
redundant Lumid acquisition paths, point-in-time microstructure, text rehydration,
leaderboard infrastructure, and public release quality. Stage C requires a new
protocol and new untouched holdout.

---

## 6. Data required

### 6.1 Lumid-only source rule and endpoint validation

The sole external observational datasource for this plan is Lumid Findata at
`https://lum.id/findata`. An endpoint is valid only when its exact path and method are
present in the live [`openapi.json`](https://lum.id/findata/openapi.json) contract.
The contract was rechecked on 2026-09-01 and contained 170 paths and 172 operations.
Every public REST endpoint named below was present. Read-only live probes returned
HTTP 200 for all required REST route families and for the representative optional REST
routes described below; some optional market/window queries returned empty arrays.
Lumid Studio's separate read-only `POST /retrieve` warehouse-materialisation route is
now listed in OpenAPI and independently returned HTTP 200 with the project FinData
credential. It is used only as the already-authorised Lumid warehouse reconciliation
path, never as a new datasource or feature. The OpenAPI response/error contracts remain
incomplete: all 172 operations document only HTTP 200 and no typed response body.

Contract presence and HTTP 200 are necessary but not sufficient. A source becomes
experiment-usable only after its response contains the required fields, its event-time
coverage reaches the exact cutoff, duplicates and malformed/future-dated rows are
handled, and the frozen completeness report passes. This distinction matters because
Lumid had documented retrieval outages during August, including August 30–31, but the
September 1 re-audit confirms recovery. The running collector still requires explicit
gap reconciliation, and the KOL cache remains stale.

No direct venue API, scraped page, or unrelated data vendor may supply an official
v2.3 observation under this coordination plan. A Lumid-provided warehouse or bulk
export is acceptable only if each table is mapped to one of the valid endpoints below,
uses the same field semantics, retains Lumid provenance, and reconciles to the endpoint
keys. Otherwise the affected branch is incomplete. Derived labels, features, folds,
manual relevance annotations, and model outputs are local transformations of Lumid
records, not additional external datasources.

### 6.2 Required Lumid endpoint registry

All time ranges are half-open UTC intervals. Every request stores the endpoint template,
resolved non-secret parameters, request/retrieval time, HTTP status, response hash,
protocol ID, and pagination/cursor state.

| Data needed | Valid Lumid endpoint and parameters | Required Lumid fields | Experiment use | Active status |
|---|---|---|---|---|
| Candidate universe | `GET /api/v1/lqt/universe?venue={polymarket|kalshi}&include_inactive=1` | venue, instrument/market ID, active state and roster metadata | Reproduce discovery and confirm the IDs from which the frozen selection was made | Already consumed for selection; retain for provenance, do not reselect |
| Active/LQT metadata | `GET /api/v1/lqt/markets?venue={polymarket|kalshi}` | market ID, venue, activity/LQT metadata and as-of time | Selection provenance and coverage cross-check | Already consumed for selection |
| Event metadata | `GET /prediction-markets/events?q={optional}&status={open|closed}&limit={n}&offset={n}` | `event_id`, `market_ids`, title/question context, description, category, start/end, active/closed state | Event grouping, terminal/public-resolution checks, metadata history | Required for status refresh; not a price source |
| Polymarket detail | `GET /prediction-markets/markets/polymarket/{condition_id}` | `condition_id`/`market_id`, question, outcomes, `clob_token_ids`, start/end/closed times, active/closed/archive flags, result or outcome state when supplied | Binary/canonical-YES mapping and terminal filters | Required for each selected Polymarket market |
| Kalshi detail | `GET /prediction-markets/markets/kalshi/{ticker}` | `ticker`/`market_id`, title, open/close times, status, result, bid/ask fields when supplied | Binary/canonical-YES mapping and terminal filters | Required for each selected Kalshi market |
| Polymarket trades | `GET /prediction-markets/trades/polymarket/{condition_id}?from={RFC3339}&to={RFC3339}&limit={n}` | `trade_id`, `ts`, `token_id`, `price`, `size`, `side`, `taker`, market/condition ID | Canonical price, B0 returns/activity/notional, all forward labels | Required primary source; query each frozen ID over exact windows |
| Kalshi trades | `GET /prediction-markets/trades/kalshi/{ticker}?from={RFC3339}&to={RFC3339}&limit={n}` | `trade_id`, `created_time`, `ticker`, `yes_price`, `no_price`, `count`, `taker_side` | Canonical price, B0 returns/activity/notional, all forward labels | Required primary source; query each frozen ticker over exact windows |
| Broad prospective news | `GET /news/latest?since={RFC3339}&category={optional}&limit={n}` | `published_at`, publisher, headline, summary, symbol, category, URL; stable identity/content hashes added locally | Append-only B1 capture, earliest `first_seen_at`, availability time and censoring audit | Required for B1 under the frozen 60-second/200-row/300-second-gap contract |
| Targeted association news | `GET /news/search?q={frozen_market_query}&since={RFC3339}&category={optional}&limit={n}` | same news fields as above | Complete the accepted news-v1 market-document mappings and recover broad-feed misses | Required for B1 using frozen query specifications |
| Symbol news | `GET /news/{symbol}?since={RFC3339}&limit={n}` | publication time, content fields, symbol and source | Only for a frozen market spec with an unambiguous symbol | Conditional supplement; never silently substitutes for search |
| News coverage statistics | `GET /news/stats` | source/category row counts and latest timestamps | Independent coverage/freshness audit | Operationally required; not a model feature |
| Warehouse news reconciliation | `POST /retrieve` with read-only `SELECT ... FROM news.articles WHERE published_at >= :start AND published_at < :end ORDER BY id`, `output_format=jsonl` | endpoint-equivalent article fields plus `id`, `ingest_ts`, `source`, `source_endpoint`, `source_run_id`, `raw`, row count and materialised URI | Recover and hash intervals that `/news/latest` cannot page; reconcile to endpoint URLs/fields and EventX first-seen receipts | Verified for `[2026-08-08, 2026-08-28)`; must be repeated through each final cutoff |
| Source health | `GET /freshness`, `GET /health`, `GET /usage/me` | endpoint freshness classes, service liveness, request/error telemetry | Completeness evidence and incident detection | Required operational evidence; `/health` alone never passes the gate |
| Schema/source provenance | `GET /catalog/schemas`, `GET /catalog/sources`, `GET /catalog/tables/{schema}/{table}`, `GET /catalog/tables/{schema}/{table}/schema.json`, `GET /catalog/lineage/row?schema={s}&table={t}`, `GET /catalog/lineage/runs`, `GET /catalog/lineage/run/{run_id}` | schema/table/source IDs, field metadata, run/row lineage | Verify a Lumid bulk/warehouse export and document source lineage | Required if an export is used; otherwise supporting provenance |

`/prediction-markets/markets/search?q=...` is a valid discovery endpoint and returned
HTTP 200 on the 2026-08-17 check, but it is not used to alter the already frozen cohort.
The LQT universe remains the reproducible roster source because broad market search was
unreliable during earlier collection.

### 6.3 Conditional and excluded Lumid endpoints

| Endpoint family | Lumid support observed | Decision in this plan |
|---|---|---|
| `GET /prediction-markets/candles/{venue}/{market_id}?interval={i}&from={t0}&to={t1}&limit={n}` | Documented; HTTP 200, but an examined selected-market window was empty | Validation or separately disclosed last-price fallback only; never silently replaces trades |
| `GET /prediction-markets/orderbook/polymarket/{asset_id}` and `GET /prediction-markets/orderbook/kalshi/{ticker}` with optional `from`, `to`, `limit` | Documented; Kalshi probe returned snapshots, examined Polymarket query was empty | Separate midpoint/microstructure robustness ceiling only; never mixed into the primary last-trade series |
| `GET /prediction-markets/open-interest/{venue}/{market_id}` | Documented; examined query was empty | Exploratory ceiling only, not required for B0/B1 |
| `GET /prediction-markets/matched-pairs/{venue}/{venue_id}` | Documented; examined Kalshi query returned a pair | Cross-venue descriptive analysis only; not used to expand or replace the frozen cohort |
| `GET /kols`, `GET /kols/tweets`, `GET /kols/tweets/search`, `GET /kols/{handle}/tweets`, `GET /kols/{handle}/tweets/history`, `GET /kols/tweets/by-symbol/{symbol}`, `GET /kols/tweets/by-symbol/{symbol}/history`, `GET /kols/archive/stats` | All documented; archive/search/history probes returned HTTP 200, while the recent-feed probe was empty and the local cache remains stale | KOL-v3 audit and B2/B3/T5 only; currently **not required and not eligible** after KOL-v2 failure |
| `GET /news/symbol-sentiment/{symbol}` and `GET /news/social-sentiment/{symbol}` | Both documented; symbol-sentiment probe returned HTTP 200 and social-sentiment was contract-validated only | Excluded from frozen B1, which uses only article counts and `news_symbol_mapped` |
| `GET /prediction-markets/stream`, `/ws/news`, `/ws/prediction-markets` | Documented realtime transports; earlier bounded handshakes were unusable | Optional transport only; bounded REST is authoritative |
| `GET /prediction-markets/leaderboard`, `GET /prediction-markets/top-holders/{venue}/{market_id}`, `GET /prediction-markets/wallet/{address}`, `GET /prediction-markets/wallet/{address}/activity`, `GET /prediction-markets/wallet/{address}/pnl`, `GET /prediction-markets/wallet/{address}/positions`, `GET /prediction-markets/markets/polymarket_us`, and `GET /prediction-markets/markets/polymarket_us/{slug}` | Documented prediction-market surfaces | Excluded: not needed for the frozen estimand/cohort and would introduce unpreregistered features |

The current Lumid contract does **not** establish complete long-historical L2 coverage,
venue fee schedules, public redistribution rights for raw text, source uptime guarantees,
or causal influence. Accordingly, the active experiment makes no such claims. v2.3
does not run a directional P&L backtest because an absolute-jump probability does not
specify a trade direction; a future signed-target protocol would also need validated
fee and spread inputs.

### 6.4 Complete field-to-artifact map

| Final artifact | Lumid inputs | Local deterministic derivation |
|---|---|---|
| Canonical market table | LQT universe/markets, events, and venue-detail endpoints | Normalize `(venue, market_id)`, binary status, canonical YES outcome/token, dates, status and taxonomy link |
| Canonical trade table | Both venue trade endpoints | Normalize event time to UTC, YES price, size/count, side, notional and stable deduplication key |
| Five-minute price grid | Canonical trades | Carry the latest canonical-YES trade observed at or before each grid time, record price age, clip probability and compute log-odds; never switch primary source within the series |
| Midpoint robustness grid | Conditional point-in-time orderbook snapshots | Construct and report separately where coverage is valid; never substitutes into primary labels |
| Jump labels | Five-minute price grid from Lumid observations | Compute forward changes and volatility-scaled thresholds at 5/30/120/360/1,440 minutes |
| B0 features | Canonical trades and derived price grid | Frozen lagged returns, volatility, trade counts, notional, recency and venue indicator |
| Accepted news associations | Lumid news latest/search/symbol rows plus frozen market metadata | Deduplicate by stable ID/content hash, apply frozen news-v1 matcher, retain human audit evidence |
| B1 features | Accepted Lumid news associations | Rolling 60/360/1,440-minute article counts and `news_symbol_mapped` using publication time |
| Conditional KOL associations | Lumid KOL roster/search/history rows plus frozen market metadata | Only after a fresh KOL-v3 audit; normalize handle/post ID/content hash and apply the frozen matcher |
| Conditional B2/B3/T5 | Accepted conditional KOL associations | Frozen rolling counts, unique handles, entropy, recency, fold-local residualization and handle attribution |
| Eligibility/terminal exclusions | Venue detail and event metadata plus canonical trades | Apply pre-t liquidity and known-resolution filters without using future status information |
| Split indices and predictions | Cohort keys, timestamps, labels and features above | Hash market groups, purge by horizon, train only on earlier folds and freeze predictions |
| Provenance/completeness manifest | Retrieval wrappers, health, usage, catalog/lineage | Record timestamps, endpoints, parameters, hashes, cursors, errors, duplicates, gaps and code/config hashes |

Human association judgments are annotations of pairs built only from Lumid market,
news, and KOL content. The corrected taxonomy, association rules, labels, features,
folds, metrics, and model outputs are derived research artifacts and therefore do not
require a separate external endpoint.

### 6.5 Canonical data keys

- Market key: `(venue, market_id)`.
- Prediction-unit key: `(venue, market_id, canonical_yes_outcome_id, t)`.
- Trade key: stable Lumid/venue trade ID; otherwise a documented content hash.
- News key: stable article URL/ID plus canonical content hash.
- KOL key: stable post ID plus content hash.
- Association key: `(source, market_id, content_hash)` with a stable `pair_id`.
- Retrieval key: `(endpoint_template, normalized_parameters, retrieved_at, response_hash)`.

### 6.6 Data sufficiency gate before labels

No development labels may be created until all required upstream freezes pass and a
label-blind completeness report confirms:

1. the saved OpenAPI contract contains every source endpoint actually used;
2. all 14 frozen markets have successful venue-detail responses and verified
   canonical-YES mappings;
3. both trade endpoints have been queried for every market over the exact closed
   development window `[2026-08-08, 2026-09-28)` and cursors reach the cutoff;
4. accepted news queries cover the same window with `published_at`, earliest
   `first_seen_at`, retrieval times and `available_at`; every `returned_rows >= 200`
   request and every greater-than-300-second success gap is reconciled, while
   future-dated/malformed/conflicting rows are quantified and quarantined;
5. all errors, empty pages, duplicates, zero-record markets, long gaps and source lags
   are retained as explicit evidence rather than converted to zeros;
6. a Lumid export, if used, reconciles to the documented endpoint fields and keys;
7. deterministic deduplication and canonical-YES normalization pass for every market;
8. bounded reconciliation recovers or explicitly records records missed during the
   August outage and polling rotation;
9. raw prefixes, reconciled tables, code, configuration, endpoint contract and query
   specifications are content-hashed; and
10. label-blind coverage is adequate for B0 and B1 on the identical comparison rows.

KOL coverage is not part of the active B1/B0 sufficiency gate. If no fresh KOL-v3 rule
passes before labels, B2/B3/T5 are omitted as ineligible rather than filled with zeros.
If trades fail, v2.3 is incomplete. If trades pass but news fails, only the
preregistered B0 fallback may proceed, with the cycle reported as unable to test B1.

The label-blind August 8–17 rehearsal completed on August 17. All 14 detail mappings
and all 14 venue-trade endpoint integrity checks passed, retaining 5,817 canonical-YES
trades with no zero-record market. The news gate did not pass: `/news/latest` returned
exactly 200 rows despite `limit=5000`, has no cursor or upper-time parameter, and left
the earlier part of the window unrecoverable from that request; two rows after the
half-open cutoff were quarantined. The 21 frozen `/news/search` requests did not hit
their cap. This is an explicit `incomplete` rehearsal result. B1 remains conditionally
feasible only if the capped broad-feed history is reconciled through valid Lumid
endpoint partitions or a Lumid-provided endpoint-equivalent export with lineage.
The exact evidence and admissible recovery paths are recorded in the
[August 17 news-truncation diagnosis](data/v2_2/planning/NEWS_TRUNCATION_DIAGNOSIS_20260817.md).

The admissible warehouse route was exercised label-blind on August 28. Lumid
`POST /retrieve` materialised 28,307 `news.articles` rows for
`[2026-08-08, 2026-08-28)`, with matching receipt/local row counts, zero malformed or
out-of-window rows, exact SQL, catalog/source evidence and file hashes. Cross-path
reconciliation matched all 1,903 EventX-observed URLs, assigned export-completion
first-seen time to warehouse-only rows, and quarantined 698 rows across 348 URL
timestamp conflicts. The continuity audit reconciled all 12 observed operational
gaps and the original pre-launch interval. This passes the closed snapshot only; the
same procedure must still cover the final September 28 cutoff before labels.

A same-window bounded frozen-cohort pull retained 17,823 canonical-YES trades (16,331
Kalshi and 1,492 Polymarket), passed all 14 detail mappings and all 14 trade-integrity
checks, and had no zero-record market. Its combined rehearsal status remained
`incomplete` solely because the redundant `/news/latest` branch capped; the separate
verified warehouse reconciliation is the controlling news evidence.

The September 2 elapsed-window repeat extended this evidence through
`2026-09-02T01:25Z`: all 14 detail/trade checks passed with 19,359 canonical-YES
trades (17,571 Kalshi and 1,788 Polymarket), no zero-record market, truncation,
saturated boundary, invalid price or invalid timestamp. A frozen multi-snapshot
availability ledger now preserves the earliest verified EventX receipt for overlapping
warehouse IDs and quarantines publication-time conflicts across snapshots.

The controlling v2.3 news contract adds these rules for development and holdout:

- poll `/news/latest` every 60 seconds at `limit=200`;
- record every request's parameters, start/end time, response row count and hash;
- if `returned_rows >= 200`, mark the interval potentially censored and do not advance
  the checkpoint;
- if successful requests are more than 300 seconds apart, raise a gap alarm;
- clear a gap only with an uncapped response from the unchanged checkpoint or
  independent Lumid-only reconciliation; and
- if any potentially censored interval remains unresolved at the applicable gate,
  mark B1 incomplete rather than filling it with zero news.

The frozen contract and offline implementation tests are
[`news_collection_contract.json`](eventx/release/v2_3/news_collection_contract.json)
and `python -m eventx.tasks.verify_v2_3_news_contract`. The same rules apply to the
October holdout.

---

## 7. Cohort, taxonomy, and association design

### 7.1 Cohort selection

The active v2.3 experiment inherits the already frozen v2.1 cohort. Selection used only the August 1–7 activity
window and the preregistered thresholds:

- at least 100 canonical-YES trades;
- at least 1,000 price-times-size/count notional;
- at least three active UTC days;
- last trade no more than 72 hours before selection cutoff;
- scheduled close at or after October 1; and
- no known resolution before selection cutoff.

No threshold may be relaxed and no sparse category may be refilled after observing the
14-market result.

### 7.2 Taxonomy

Use only the accepted `eventx-v2.1-taxonomy-v7` mapping. It was created from metadata,
independently audited before labels, and frozen for all 3,420 candidates. Later prices,
labels, model outputs, or holdout results may not change it.

### 7.3 Association rules

News and KOL matching are separate source-specific rules with separate audit results.

- The accepted news-v1 logic remains unchanged.
- The combined v1 candidate failed because KOL precision and recall failed their
  source gates.
- All 300 opened v1 audit pairs are development material and excluded from fresh
  validation by `pair_id`, `(market_id, content_hash)`, and content-level checks.
- `eventx-v2.1-kol-association-rule-v2-candidate` completed its fresh 150-row audit
  and failed: 62 TP, 12 FP, 36 FN and 38 TN across 148 decided rows, plus two
  uncertain rows; precision 0.8378 and hard-candidate recall 0.6327 were below the
  fixed 0.85 and 0.90 gates.
- KOL-v2 is frozen as failed opened development material. Its 150 pairs join the
  earlier 300 in the cumulative 450-pair exclusion ledger.
- The earlier opened-development diagnostic performance for KOL-v2 is not validation
  evidence and cannot rescue the failed fresh audit.

Therefore the accepted association output for the active branch contains news-v1
only. A later KOL-v3 version would require genuinely new label-blind development,
Lumid-sourced candidate content, and another fully fresh audit excluding all 450
opened pairs. The current plan does not spend the October schedule on that higher-risk
branch unless it is separately authorized before labels.

### 7.4 Association output

Freeze a source-specific association manifest containing:

- accepted rule IDs and source hashes;
- lexical/entity specifications and market aliases;
- audit sampling and scoring contracts;
- opened-pair exclusions;
- accepted news mappings and, only if a future fresh rule passes, accepted KOL mappings;
- unmatched candidates required for audit recall estimates;
- content hashes and provenance; and
- a statement that labels, prices, and performance were not used to tune matching.

---

## 8. Prediction unit, prices, labels, and eligibility

### 8.1 Prediction unit

One row is `(venue, market_id, canonical_yes_outcome_id, t)` at a five-minute cadence.
Binary NO outcomes are not added as separate observations because they are mechanically
dependent on YES.

### 8.2 Price construction

The primary price is the latest canonical-YES trade at or before `t`, carried forward
without switching measurement source. Record `price_source = last_trade` and
`price_age_minutes` on every row. A contemporaneous L2 midpoint may be constructed only
as a separate robustness/measurement-ceiling series where point-in-time coverage is
valid. Candle close is a separate fallback diagnostic only. Clip probabilities to
`[0.0001, 0.9999]` before
computing:

```text
price_logodds(t) = log(p(t) / (1 - p(t)))
```

Never silently mix source definitions. Report the source composition by venue, market,
time block, and split.

### 8.3 Forward target

For horizon `h`:

```text
fwd_dy_h(t) = price_logodds(t + h) - price_logodds(t)
threshold_h(t) = 4 * sigma_1m_240(t) * sqrt(h / 30)
y_jump_h(t) = 1[abs(fwd_dy_h(t)) >= threshold_h(t)]
```

`sigma_1m_240(t)` is computed only from information at or before `t`, with at least 30
valid one-minute changes. The primary label uses `h = 30 minutes`. This inherited
formula is a heuristic 30-minute anchor expressed in trailing **one-minute sigma
units**: at 30 minutes the threshold is `4 * sigma_1m_240`. It must not be described as
four 30-minute sigmas, and the formula may not be changed after label inspection.
Every paper/report must state: “The threshold is a preregistered heuristic event
definition inherited from the pilot protocol and should not be interpreted as a
Gaussian four-standard-deviation event.” Its justification is prospective inheritance,
not a Gaussian tail probability or observed label prevalence.

### 8.4 Pre-t eligibility

A prediction row is eligible only when, using information available at or before `t`:

- trailing 240-minute trade count is at least three;
- trailing 240-minute notional is at least 100;
- current price and volatility estimate are valid;
- the market is not mechanically settled or already publicly resolved; and
- the row is not in a prohibited boundary/terminal interval.

Forward liquidity may establish whether a target is measurable but may not determine
eligibility. Actual `resolution_ts` is a filter, never a feature.

Primary eligibility retains the fixed liquidity rules above. Predeclared descriptive
robustness repeats evaluation on rows with `price_age_minutes <= 30` and `<= 60`, and
a trade-arrival diagnostic tests whether apparent jump prediction is mainly prediction
of the next observed trade. These checks cannot rescue a failed confirmatory gate.

### 8.5 Resolution-leakage exclusion

Apply the strongest available rule in this order:

1. exclude at or after a known event-end or determination timestamp;
2. exclude at or after resolving, settling, finalized, or resolved status;
3. exclude persistent terminal convergence beyond the frozen boundary rule; and
4. apply predeclared category-specific timing rules where authoritative event times are
   available.

Record the rule responsible for every exclusion and report exclusion rates.

---

## 9. Feature families

All rolling windows are closed at `t`. No future record may change a feature computed
for an earlier `t`.

### B0 — market history

- `price_logodds`;
- momentum over 5, 30, and 120 minutes;
- realized volatility over 30 and 240 minutes;
- trade count over 60 and 240 minutes;
- notional over 60 and 240 minutes;
- minutes since the latest trade; and
- venue indicator.

Count and notional families receive `log1p`; other features use the identity transform.

### B1 — core news

- article count over 60 minutes;
- article count over 360 minutes;
- article count over 1,440 minutes; and
- `news_symbol_mapped`.

For each stable record, retain the declared `published_at`, earliest EventX
`first_seen_at` across valid Lumid endpoints, every retrieval time, ingestion latency
and quality flags. Primary B1 windows use:

```text
available_at = max(published_at, first_seen_at)
```

Thus an article published at 10:00 but first observed through Lumid at 10:17 cannot
enter a 10:05 feature vector. Missing/invalid publication times are excluded from
primary B1; conflicting publication timestamps are quarantined until reconciled.
Historical recovery cannot backdate primary features. A publication-time-only
reconstruction is an oracle sensitivity and cannot rescue the primary gate.

### B2 — sparse KOL diagnostic

- tweet count over 30 minutes;
- tweet count over 360 minutes;
- unique handle count over 30 minutes;
- unique handle count over 360 minutes;
- handle entropy over 24 hours; and
- minutes since the latest associated KOL post.

### B3 — market + news + residualized KOL

Within each outer fold, fit a ridge model with fixed penalty 1.0 on training rows to
predict each KOL feature from B0+B1. Use the residuals as KOL inputs. Apply the fitted
training transformation to validation rows. Never fit residualization globally.

### Optional microstructure ceiling

Spread, depth, imbalance, open interest, and related fields may be reported only as a
separately named exploratory ceiling if point-in-time availability is demonstrated.
They do not enter the active confirmatory ladder.

### Point-in-time tests

For every feature builder:

- truncate the source at `t` and reproduce the feature;
- move the cutoff earlier and assert later records have no effect;
- test daylight-saving and UTC boundaries;
- test empty-window, duplicate, delayed-retrieval, and out-of-order records; and
- verify training-only fitting for scalers and residualizers.

---

## 10. Splits, learner, metrics, and uncertainty

### 10.1 Development splits

Use the active preregistered five-fold expanding-window design:

- training always precedes validation;
- purge equals the evaluated horizon;
- markets are assigned by `sha256(venue + ':' + market_id) mod 5`;
- fold `k` validates on the later time block and market group `k`; and
- training uses earlier eligible rows in the other groups.

The frozen 14-market cohort creates small and uneven market groups. This limitation
must be reported. It does not authorize reassignment under v2.3. Temporal row count
provides precision conditional on these markets; it does not create hundreds of
thousands of independent market observations.

### 10.2 Confirmatory learner

Standardized logistic SGD:

- eight epochs;
- learning rate 0.02;
- L2 penalty 0.0001;
- shuffle seeds 11, 23, and 47; and
- prediction average across seeds.

All standardization, imputation, and residualization are fitted on training rows only.
A fixed LightGBM ceiling may be exploratory but may not become the confirmatory
candidate.

### 10.3 Metrics

- Primary: average precision.
- Calibration: Brier score.
- Secondary: ECE with ten equal-frequency bins, ROC-AUC, lead time, calibration slope,
  and calibration intercept.
- Diagnostics: prevalence, prediction distribution, coverage, missingness, and
  performance by venue, market, category, horizon, liquidity, and price source.

For candidate `C` and reference `R`:

```text
delta_ap = AP(C) - AP(R)
brier_improvement = Brier(R) - Brier(C)
```

### 10.4 Uncertainty

Use 5,000 paired circular moving-block bootstrap samples, stratified by market, with
360-minute blocks and seed 61. Preserve paired prediction keys across compared models.

Report point estimates, confidence intervals, fold values, venue values, and the number
of markets and positive labels contributing to every metric. Undefined metrics remain
undefined rather than being replaced. For promotion, an undefined fold AP or Brier
improvement does not count as a positive fold. An undefined required aggregate metric,
bootstrap lower bound, or either venue's required Brier improvement makes that
condition unsatisfied. Undefined metrics may not be dropped, imputed, zero-filled, or
removed from the denominator to promote B1. Descriptive results may still be reported.

---

## 11. Complete experiment matrix

| ID | Experiment | Purpose | Comparison or test | Gate/output |
|---|---|---|---|---|
| E0 | Preregistration and seal verification | Protect integrity before work | Verify protocol, manifests, cohort, taxonomy, association state, holdout receipts | Zero verification failures |
| E1 | Lumid source-health and completeness audit | Establish data usability | Validate saved OpenAPI paths, then run exact-window endpoint reconciliation and lag/error/missingness reports | Required Lumid trade/news sources complete or explicit incomplete decision |
| E2 | Canonicalization audit | Verify the prediction unit | Metadata, token/outcome, YES-side, duplicate and price checks | Every cohort market passes |
| E3 | Association validation | Validate news/KOL relevance | Accepted news evidence + completed fresh KOL-v2 blind audit | Complete: news eligible; KOL-v2 failed, so B3 is ineligible |
| E4 | Label audit | Validate target construction without model selection | Prevalence, threshold distribution, terminal exclusions, measurability | No leakage; nondegenerate labels documented |
| E5 | B0 baseline | Establish market-only reference | B0 across five folds and all horizons | Frozen predictions and metrics |
| E6 | B1 incremental news | Test news beyond market history | B1 versus B0 | Same promotion-style metrics; fallback candidate only if gate passes |
| E7 | B2 diagnostic | Describe sparse KOL information without news | B2 versus B0 | Do not run unless fresh KOL-v3 first passes; diagnostic only |
| E8 | B3 confirmatory development | Test residualized KOL beyond news | B3 versus B1 at 30 minutes | Currently ineligible; all promotion conditions apply if KOL-v3 reopens it |
| E9 | Multi-horizon analysis | Measure temporal localization | Frozen B0/B1 at 5, 120, 360, 1,440 minutes; B3 only if eligible | Secondary; no horizon shopping |
| E10 | Stratified nulls | Reject spurious topical/temporal association | 500 assignment permutations and fixed ±1–7 day shifts | Run only for an eligible, provisionally promoted B3 |
| E11 | Robustness and missingness | Test dependence on data construction | Separate midpoint grid, price-age ≤30/≤60 minutes, trade arrival, venue, market, time block, liquidity, source lag, leave-one-market-out | Descriptive; cannot rescue a failed gate |
| E12 | Candidate freeze | Lock exactly one holdout candidate | Current branch: B1 or B0; B3 only if independently reopened | Freeze code, transforms, cutoff, inputs, evaluator |
| E13 | October holdout | Obtain the single confirmatory result | Frozen candidate versus frozen reference/baseline | One run, one receipt, no rerun |
| E14 | T5 conditional attribution | Localize handle-level lift | Per-KOL OOF ablation/permutation with BH FDR | Runs only if B3 promoted |
| E15 | Non-trading decision value | Quantify operational usefulness of jump alerts | Frozen alert rate, lead time, calibration and development-frozen decision-curve net benefit | No directional P&L claim; descriptive for a promoted candidate |
| E16 | Release verification | Prove reproducibility and claim consistency | Clean-room rebuild, hashes, secret scan, datasheet, claim audit | Zero verifier failures before release |

---

## 12. Promotion and decision hierarchy

The sealed hierarchy is preserved. Operationally, KOL-v2's failed audit removes B3
before model evaluation, so the active decision starts at Section 12.2. Section 12.1
is retained as the controlling rule only if a fresh KOL-v3 audit legitimately reopens
the branch before affected labels are inspected.

### 12.1 B3 versus B1

B3 promotes only if all are true:

1. aggregate `delta_ap > 0`;
2. aggregate `brier_improvement > 0`;
3. both improvements are positive in at least four of five folds;
4. the 95% bootstrap lower bound for Brier improvement exceeds zero;
5. venue-stratified Brier improvement is nonnegative for both venues; and
6. if promoted as a KOL candidate, both frozen null tests are passed.

### 12.2 B1 versus B0

Because B3 is currently ineligible, B1 may replace B0 only under the same fixed
development promotion logic versus B0. A failed association or B3 branch may not be
replaced by another KOL specification selected from the same development results.
The directly stated H1_v2.3–H5_v2.3 are all required. An undefined required metric is
handled by Section 10.4 and cannot be interpreted favorably after the fact.

### 12.3 Final candidate

Freeze at most one promoted candidate before October 1. Under the active branch this
is B1 if it promotes, otherwise B0. The holdout is not used to select among candidates.

### 12.4 Negative and incomplete outcomes

- **Negative:** adequate data and valid experiment, but no candidate passes.
- **Incomplete:** required data, source coverage, audit, or integrity gate fails.
- **Contaminated:** protected labels/metrics were exposed before the required freeze.

These states are reported distinctly. Incompleteness is not converted into a negative
scientific finding, and contamination is not described as confirmatory.

---

## 13. Null tests, T5, and operational value

### 13.1 Assignment null

Shuffle tweet-to-market assignments within corrected category, venue, and UTC calendar
day, preserving activity structure as far as possible. Run 500 frozen-seed permutations.

### 13.2 Timestamp null

Shift KOL timestamps by market-specific offsets drawn from ±1–7 days while preserving
within-market patterns. Run the fixed permutation count and seed contract.

### 13.3 T5

If B3 promotes:

- compute per-KOL out-of-fold lift by ablating associated activity;
- use market-stratified block bootstrap or permutation p-values;
- correct across tested handles with Benjamini–Hochberg at `q = 0.05`;
- report the tested-handle universe and zero-coverage handles;
- report fold, venue, category, and temporal stability; and
- avoid causal language.

With only 14 markets, T5 is likely low-powered and must be framed as exploratory even
if the protocol permits it.

### 13.4 Non-trading value-of-information check

If a candidate promotes, freeze alert thresholds on development data and report alert
rate, time-to-jump/lead time, calibration, and a decision-curve net-benefit analysis
whose utility weights are fixed before the holdout. Report this separately from model
accuracy. Do not convert an unsigned jump probability into YES/NO trades or report P&L.
A later trading experiment requires a new signed-return target, execution rule, cost
contract, and untouched holdout.

---

## 14. Step-by-step execution plan

### Phase 0 — Integrity startup

1. Read `CURRENT_STATE.md` and repository instructions; consult detailed progress
   history only when the task requires it.
2. Verify the active v2.3 preregistration and immutable v2.2/v2.1 lineage.
3. Verify taxonomy, cohort, association, and data manifests required by the task.
4. Confirm no v2.3 development or holdout labels have been created or inspected.
5. Confirm the v1 OOT consumption receipt and prohibit evaluator reuse.
6. Save/hash the current Lumid OpenAPI contract and reject any configured source path
   that is absent from it.

### Phase 1 — Maintain and reconcile Lumid collection

1. Preserve the legacy collector as provenance evidence; do not call it v2.3-compliant.
   Any migration/restart or parallel launch of the frozen v2.3 news collector is an
   explicit operational action with its own start receipt and unresolved prior-gap state.
2. For the compliant news path, freeze polling at 60 seconds, alarm at 200 returned
   rows and at successful-request gaps above 300 seconds, and never advance a capped or
   failed checkpoint.
3. Monitor collector process and health at least daily.
4. Record endpoint-specific event freshness, first-seen/retrieval freshness, response
   counts/hashes, censoring alarms, errors and gaps.
5. Back off during service-wide HTTP failures rather than treating liveness as data
   health; after recovery, do not equate HTTP 200 with complete history.
6. Recover gaps through the exact bounded Lumid REST routes in Section 6, or a
   Lumid-provided endpoint-equivalent export with catalog/lineage evidence.
7. Preserve append-only raw files, request metadata, response hashes and checkpoints.
8. Reject or quarantine impossible timestamps, malformed rows and schema drift; do not
   infer that an empty page means zero activity without completing pagination/window checks.

### Phase 2 — Record the association result and freeze the active branch

1. Preserve the completed KOL-v2 packet, review, score, failed-result manifest and
   cumulative 450-pair exclusion ledger unchanged.
2. Record KOL-v2 as failed at precision 0.8378 and recall 0.6327; do not weaken gates.
3. Verify the accepted news-v1 source path and mapping hashes.
4. Freeze the active executable branch as B1 versus B0.
5. Do not build B2/B3/T5 unless a separately versioned, label-blind KOL-v3 rule passes
   a fresh audit before any affected labels are inspected.

### Phase 3 — Close and reconcile required development data

1. At the September 28 UTC development cutoff, call the two venue-specific Lumid trade
   endpoints for all 14 frozen IDs over `[2026-08-08, 2026-09-28)` with deterministic
   time pagination.
2. Call `/news/latest` and `/news/search` for the accepted frozen news specifications
   over the same interval; use `/news/{symbol}` only where the frozen spec authorizes it.
3. Refresh event and venue-detail metadata without changing the frozen cohort.
4. Reconcile Lumid bounded results with the append-only prospective prefixes by stable
   IDs/content hashes and preserve both versions.
5. Produce per-endpoint, per-market and per-day coverage, lag, duplicate, malformed,
   future-time, zero-record and error reports.
6. Verify canonical YES token/price mappings and publication/event-time semantics.
7. Run all ten Section 6.6 checks and repeat the label-blind frozen-rule association
   density, availability-lag/backfill and trade-staleness diagnostics; preserve sparse
   or constant features unchanged.
8. Freeze reconciled inputs, query specs, OpenAPI contract, code/config and hashes.
   Stop if the gate fails.
9. After the data gate passes, run the synthetic 14-market cluster power/precision
   simulation without empirical labels, prevalence or outcome paths.
10. Freeze the simulation configuration, seed and output. Its findings may disclose
   limited power but may not change the protocol.

### Phase 4 — Build labels and features

1. Construct the uniform last-canonical-YES-trade primary series with explicit
   `price_source` and `price_age_minutes`; build any midpoint series separately.
2. Build the five-minute evaluation grid.
3. Apply pre-t eligibility and resolution-leakage filters.
4. Generate all frozen horizons and primary labels.
5. Build B0 and B1 using `available_at` for primary news windows. B2/B3/T5 do not run
   in v2.3.
6. Run point-in-time leakage tests.
7. Freeze dataset and feature manifests.

### Phase 5 — Development evaluation

1. Materialize frozen split indices.
2. Run B0 on identical fold keys.
3. Run B1 on those same keys; run B2/B3 only if the conditional KOL gate passed.
4. Compute aggregate, fold, venue, market, horizon, and calibration metrics.
5. Run paired block bootstrap.
6. If B3 was eligible and provisionally promotes, run both null families.
7. Run predeclared robustness diagnostics without using them to rescue a failure.
8. Apply the fixed decision hierarchy once: active route B1 if it promotes, otherwise B0.

### Phase 6 — Candidate and holdout freeze before October 1

1. Select at most one candidate under the hierarchy.
2. Freeze code, features, transforms, model seeds, training cutoff, input hashes, and
   evaluator.
3. Freeze a manifest stating holdout labels and prevalence remain uninspected.
4. Test evaluator refusal behavior using synthetic fixtures, never the real holdout.

### Phase 7 — Holdout collection and single evaluation

1. Keep October 1–21 data sealed from model-selection workflows.
2. After the window closes, reconcile exact inputs and verify the manifest.
3. Run the frozen evaluator exactly once.
4. Write the result and consumption receipt atomically.
5. Refuse reruns or alternative-candidate evaluation.

### Phase 8 — Final analysis and artifact package

1. Report development and holdout results with claim boundaries.
2. Run T5 only if an eligible KOL branch was prospectively reopened; for the active
   B1/B0 branch, run only the non-trading value-of-information outputs authorized by
   promotion outcomes.
3. Write missingness, source-lag, deviation, and underpower disclosures.
4. Produce report, datasheet, manifests, reproducibility instructions, and release
   checklist.
5. Run clean-room reproduction, secret scan, and release verifier.

---

## 15. Active timeline

| Date | Milestone | Required outcome |
|---|---|---|
| Completed before this revision | KOL-v2 independent blind review | Failed and frozen; B3 currently ineligible |
| Aug 17 checkpoint | v2.2 drill followed by v2.3 clarification freeze | v2.3 verifies; explicit news censoring/availability, hypotheses, undefined metrics and execution order are frozen; the earlier `/news/latest` cap remains incomplete |
| Aug 27–28 checkpoint | Corrected collector, warehouse/news continuity and frozen-cohort trade snapshot | Implementation-v2 live; news reconciled; 14/14 trade checks and 17,823 rows passed without labels; final window still open |
| Aug 29 checkpoint | Frozen-rule feature-readiness and trade-staleness audit | 43 news associations across 2/14 markets; B1 support is sparse/concentrated; contracts passed without labels |
| Sep 2 checkpoint | Cumulative warehouse closure, availability ledger, repeated trade/readiness audit | 23/23 gaps recovered through cutoff; 14/14 trade checks and 19,359 rows passed; later slice has only three news associations |
| Aug 8–Sep 27 | Lumid development collection | Continue append-only capture; quantify the August outage and stale/empty-source behavior |
| Sep 28–30 | Exact-window reconciliation, labels, development evaluation and freeze | Reconcile `[Aug 8, Sep 28)`, pass Section 6.6, run frozen B0/B1 once, and freeze one candidate before Oct 1 |
| Oct 1–21 | Holdout collection | No model selection or outcome inspection |
| Oct 22 | One-shot evaluation | One result and consumption receipt |
| Oct 22–31 | Finalization | Internal report and reproducibility package complete |

If an upstream gate cannot be completed without violating the schedule or integrity
contract, report v2.3 incomplete. Do not move dates after inspecting affected labels.

### 15.1 Feasibility assessment as of 2026-09-02

- **B1 versus B0 is scientifically realistic:** cohort, taxonomy and accepted news
  association logic are already frozen; the learner and evaluation contract are fixed;
  development/holdout labels remain unopened.
- **Lumid trade mechanics passed the elapsed-window drill:** the required market-detail
  and venue-trade routes exist, all 14 canonical mappings and trade integrity checks
  passed through the latest elapsed cutoff, and 19,359 canonical-YES trades were
  recovered. Several sparse Polymarket
  markets have long intertrade gaps, which makes the price-age robustness essential.
- **Historical news recovery is reproducible:** the verified warehouse export and
  cross-path reconciliation close the original pre-launch interval. An interim
  August 31–September 2 cumulative export passed with 3,468 unique IDs and reconciled
  all 23 operational gap windows through its cutoff. It closed 610 additional capped
  intervals, bringing the database total to 630 reconciled; eight active-tail intervals
  remained because they ended after the export cutoff. The remaining formal blocker is
  final exact-window closure after September 28; `/news/latest` remains insufficient
  alone.
- **Repeated exports preserve availability correctly:** the frozen ledger merged
  32,646 receipt rows into 31,775 warehouse IDs, retained the earlier verified receipt
  for 629 overlaps and quarantined 713 rows across 355 conflict URLs. Its 26-check
  verifier passes; a later export cannot erase earlier safe point-in-time evidence.
- **Actual B1 support is a major scientific risk:** applying the frozen matcher to the
  complete closed snapshot yielded 43 associations in only 2/14 markets, with 42 in
  the Clarity Act market; the 60-minute count is non-zero on only 0.089% of current
  grid rows and `news_symbol_mapped` is constant zero. Retrieval completeness therefore
  does not imply adequate feature variation. This must be repeated and reported at
  final close, not repaired by changing frozen definitions.
  The later Aug 31–Sep 2 slice produced only three associations across two markets,
  with only one endpoint-observed association usable inside the slice.
- **Studio usability improved:** the September 1 re-audit completed 178/178 profiles
  and schemas, matched all 22 `news.articles` columns, documented `/retrieve`, and
  verified JSONL/CSV plus bounded SQL. Current defects are the silent 200-row news cap,
  future-dated news, broken Kalshi candles, skeletal OpenAPI responses and an empty
  lineage-run listing. Exports must retain SQL, receipts, timestamp checks and hashes.
- **The censoring behavior is executable and auditable:** v2.3 freezes 60-second
  polling, a 200-row cap alarm, a 300-second maximum successful-request gap, no
  checkpoint advance on capped/failed responses, identical holdout behavior, and
  `available_at = max(published_at, first_seen_at)`. Implementation v3 is live under
  `caffeinate`; it fixes the negative-sleep race, rejects early future-dated
  observations, and binds every restart to frozen hashes. Of 68 affected identities,
  two predecessor-contaminated identities remain quarantined and 66 were admitted only
  after a timely re-observation with availability no earlier than publication. The
  September 2 source audit finds zero unsafe identities. All six known-source guards
  pass, but B1 remains unauthorized while any capped interval is unresolved. The
  legacy daemon remains preserved but is not v2.3-compliant.
- **The timing contradiction is resolved:** development now ends September 28, leaving
  a fixed 72-hour reconciliation, evaluation, and candidate-freeze buffer before the
  October holdout. The schedule remains tight but is logically executable.
- **B3/KOL is not realistic on the current critical path:** the rule failed and recent
  KOL feed behavior is stale/empty. A new KOL-v3 audit would add material schedule and
  data risk without changing the already valid B1/B0 fallback.
- **Overall verdict:** the protocol remains executable as B1 versus B0 (or B0 if news
  coverage fails), but the scientific informativeness of B1 is now red/amber because
  the source supplies almost no cross-market variation. Coverage/timing failure gives
  an incomplete result; sparse support limits interpretation and does not justify a
  new source, post-hoc redesign, date change or early holdout opening.

### 15.2 Historical feasibility and completed v3.1 primary

Historical expansion does not amend v2.3. The label-blind protocol
`eventx-v3-historical-feasibility-20260830` tests whether a broader retrospective
study can be preregistered over `[2026-05-17, 2026-08-08)` using only Lumid data.
Its primary news export uses `max(published_at, ingest_ts)` and retains only records
ingested no earlier than publication and no more than 24 hours later. Older backfills
remain sensitivity/descriptive evidence and cannot be backdated.

The historical branch requires at least 30 eligible markets, five per venue, 20
markets with at least five timely associations, 200 associations overall, no market
above 50% of associations and 56 usable calendar days. Lumid must also confirm that
`ingest_ts` is a genuine first-seen field. Only a complete label-blind pass authorizes
a new hash-locked protocol with a chronological 80/20 split and the unchanged v2.3
B0/B1 target, features and evaluation. Failure produces a descriptive coverage study;
it cannot modify the prospective cohort, matcher or dates.

As of September 1, the bounded news export passed with 218,392 unique timely rows and
zero integrity failures. Trade/activity extraction counts distinct valid-price trade
IDs in one-day UTC, 1,000-key keyset pages with completed-chunk checkpoints; market
metadata uses 100-key batches and each market's earliest pre-cutoff snapshot. Raw
vendor payloads and
resolution fields are excluded. News support is URL-deduplicated, timestamp-conflict
identities are excluded, and associations must fall inside observed market life. The
37-check label/outcome-seal, activity-prefilter, checkpoint-compatibility and disk
safety contract passes.

After Lumid recovered, the checkpointed runner completed 18,635,674 Kalshi and 901,028
Polymarket retrieved activity rows with passing integrity manifests. Kalshi aggregation
retained 16,802,432 unique ticker keys, of which 9,422 can satisfy the already-frozen
100-trade and 10-active-day gates; 1,576 Polymarket condition IDs can do so
conservatively before canonical-YES mapping. The first unfiltered metadata run was
stopped and permanently receipted, then only its incomplete 2.35-GiB directory was
removed. The corrected exporter completed 95 Kalshi and 16 Polymarket batches with
5,068 and 1,574 passing earliest-snapshot rows. Checkpoints bind the eligible-key hash
and filter, receipts are compact, downloads enforce a 5-GiB free-space floor, and the
audit uses a streaming join. The outage remains in the retry ledger; no failed request
was interpreted as empty data.

The feasibility audit completed label-blind with 5,999 eligible markets (5,068 Kalshi
and 931 Polymarket), 216,697 deduplicated timely news documents over 81 days and
341,845 associations. The subsequent provenance audit required source-run joins and
used the conservative maximum of publication, ingestion, run-start and available
run-end timestamps; 214,944 of 218,392 candidate rows passed and 3,448 late rows were
excluded.

The authorized historical primary was frozen as v3. The v3 development trade gate
then failed before labels because 204,069 zero-count Kalshi rows caused 19 markets to
miss the frozen activity minimum. That failure remains preserved. A separately
versioned pre-outcome v3.1 correction removed exactly those 19 markets, leaving 4,651
markets, and changed no label, feature, learner, fold, metric or promotion rule.

Version v3.1 is now complete. Its 7,706,324 development examples produced 1,460,454
OOF comparison rows. B1 had AP 0.191378 versus B0 0.193294 and Brier 0.119494 versus
0.119209. Both metrics improved in zero of five folds, the bootstrap Brier-improvement
interval was `[-0.000341, -0.000230]`, and all H1-H5 gates failed. B0 was selected and
evaluated once on 211,718 historical-holdout rows, achieving AP 0.171628, ROC AUC
0.628037 and Brier 0.107107. The holdout is consumed. A pre-receipt prevalence
exposure is preserved as a procedural deviation; it occurred after the candidate and
formulas were frozen but before any prediction/performance scoring.

---

## 16. Full benchmark extension after v2.3

The complete EventX benchmark requires a new cycle with:

1. a larger label-blind cohort with meaningful market counts in both venues and every
   reported category;
2. at least 12 months of uniform, point-in-time price data under one declared source
   hierarchy;
3. redundant Lumid acquisition paths—documented REST plus endpoint-equivalent
   warehouse/bulk exports with catalog/lineage reconciliation;
4. independently recorded historical L2 if microstructure claims are retained;
5. dependable KOL/news history with deletion and freshness audits;
6. rights-cleared identifiers or representations for public release;
7. enough independent markets and KOL exposures for T5/FDR analysis;
8. a new untouched future holdout;
9. Feature-Track and Rehydration-Track baselines; and
10. a maintained evaluation harness and leaderboard contract.

Under the Lumid-only rule, Stage C cannot claim independent upstream redundancy. If a
future benchmark requires direct venue or other vendor data, that is a new datasource
scope requiring a new plan/protocol before data or labels are inspected.

The later protocol should include a prospective power/precision analysis based on
market clusters, not only the number of five-minute rows. Repeated timestamps from a
small number of markets do not substitute for independent market-level breadth.

---

## 17. Required artifacts and directory contract

### Protocol and governance

- human-readable preregistration;
- machine-readable protocol;
- locked manifest and hashes;
- deviation/amendment history; and
- holdout state and consumption receipt.

### Raw and reconciled data

- append-only raw market/news inputs and conditional KOL inputs;
- request-attempt ledger, response counts/hashes, checkpoints, censoring intervals and
  health ledger;
- exact-window reconciled tables;
- duplicate and missingness reports; and
- input hashes and retrieval provenance.

### Curated data

- canonical market/outcome table;
- accepted taxonomy mapping;
- market entity/alias specifications;
- accepted association mappings;
- news `published_at`, earliest `first_seen_at`, `available_at`, ingestion latency and
  timestamp-quality flags;
- price series with `price_source`;
- labels and eligibility reasons;
- point-in-time features; and
- split indices.

### Evaluation

- per-fold predictions;
- aggregate and stratified metrics;
- bootstrap distributions or sufficient summaries;
- null-test outputs;
- promotion decision report;
- frozen candidate/evaluator manifest; and
- final one-shot result.

### Release

- final research report;
- datasheet;
- editorial/claim audit;
- Feature-Track export;
- Rehydration manifest where rights permit;
- reproducibility guide;
- release verifier;
- licensing and responsible-use review;
- citation metadata and archive/DOI; and
- public-release readiness checklist.

---

## 18. Risks and mitigations

| Risk | Consequence | Required mitigation |
|---|---|---|
| Lumid returns HTTP errors while liveness stays green | Silent prospective gaps | Independent health ledger, circuit breaker, exact bounded Lumid reconciliation, endpoint-equivalent Lumid export or incomplete result |
| Lumid returns HTTP 200 with empty, stale, malformed or future-dated rows | False completeness or leakage | Validate event-time bounds/schema, report empty pages and lags, quarantine invalid rows, require cutoff coverage |
| KOL cache is stale | A reopened B3 branch would create false zeros | Keep B3 ineligible; recover and audit history only if a fresh KOL-v3 branch is authorized |
| `/news/latest` reaches 200 rows or a success gap exceeds 300 seconds | Silent B1 censoring | Alarm, retain checkpoint, reconcile through Lumid, and mark B1 incomplete if unresolved; same rule in holdout |
| Historical news backfill is assigned to an earlier publication time | Retrospective availability leakage | Primary `available_at = max(published_at, first_seen_at)`; publication-time-only oracle sensitivity cannot rescue |
| Historical L2 is absent | Midpoint/microstructure claims unsupported | Uniform last-trade primary series; separate midpoint robustness only |
| Only 14 markets pass selection | Weak independent-sample breadth | Pilot framing, market-level uncertainty, no category-complete claims |
| Fold groups are uneven or a required metric is undefined | Unstable or selectively interpreted gate | Report exact counts; do not reassign; undefined metrics make their v2.3 promotion conditions unsatisfied |
| Association audit overfits opened rows | Inflated relevance accuracy | Fresh content-level exclusions and independent blind audit |
| Resolution leakage | Artificial performance | Layered terminal/public-outcome exclusion and audit |
| Overlapping labels | Inflated certainty | Horizon-specific purge and block bootstrap |
| Model or feature selection from holdout | Invalid confirmation | Frozen candidate/evaluator, sealed holdout, one-run receipt |
| Public text rights are unclear | Release blockage | Feature/ID release, rights review, no raw text by default |
| Absolute-jump target has no direction | A P&L backtest invents an unregistered trading rule | No directional P&L in v2.3; report only frozen non-trading decision value |
| Negative result is hidden or rescued | Research bias | Fixed hierarchy and publication of failures |

---

## 19. Completion criteria

### Historical v3.1 scientific completion — achieved 2 September 2026

- The corrected source/provenance/data gates, power analysis, example construction,
  development comparison and one-candidate freeze are complete and hash-locked.
- B1 failed all H1-H5 conditions; B0 is the immutable selected candidate.
- The historical holdout was evaluated once and is consumed. Its pre-receipt
  prevalence exposure is explicitly documented as a procedural deviation, and no
  candidate prediction or performance metric preceded the corrected receipt.
- Development selection and holdout evaluation must never be rerun.

### v2.3 scientific completion

The active cycle is scientifically complete when:

1. the accepted news rule is verified and the failed KOL-v2 disposition is preserved;
2. required development and holdout data are reconciled and hashed, with zero
   unresolved news-censoring intervals at each applicable gate;
3. the label-blind synthetic 14-market power simulation is frozen after the data gate
   and before labels, then labels/features/splits pass leakage and integrity verification;
4. the fixed B1-versus-B0 development comparison and promotion hierarchy run once,
   with B3 omitted unless a fresh KOL-v3 gate passed beforehand;
5. one candidate or B0 is frozen no later than October 1, after the fixed September
   28–30 reconciliation/evaluation buffer and before holdout access;
6. the holdout is evaluated once after closure;
7. a consumption receipt prohibits reruns; and
8. the final report fully discloses coverage, missingness, limitations, and deviations.

### v4 scientific completion

The active v4 confirmation is complete only when:

1. all daily Lumid news and canonical-YES trade partitions through 30 October pass
   the frozen source, clock, provenance, membership, row-count and hash gate;
2. the irreversible holdout receipt is written before any label summary;
3. the discovery-fitted semantic transform is applied without refitting and all
   B0-B3 examples use identical rows;
4. the evaluator writes its attempt receipt before reading label values and executes
   exactly once;
5. the preregistered 0.001-nat effect, bootstrap lower-bound, Brier and venue
   guardrails are applied without modification; and
6. positive, null, negative or source-incomplete results are reported with the frozen
   Polymarket-only and non-virality claim boundaries.

### Internal artifact completion

The internal package is complete when the report, datasheet, manifests, code,
environment instructions, verifier, claim audit, and secret scan all pass.

### Public release completion

Public release additionally requires explicit upstream-rights approval, licenses,
privacy/dual-use review, maintainer and update policy, clean-room reproduction,
archival deposit, DOI, and citation metadata. Until then, public redistribution remains
NO-GO even if the scientific experiment is complete.

---

## 20. Immediate next actions

1. Preserve v3.1 as complete: never rerun development selection, rebuild its holdout,
   evaluate B1 on that holdout or change the frozen B0 candidate.
2. Keep the v4 sealed collector healthy through 30 October without reading future
   prices, labels, predictions, prevalence or metrics.
3. At v4 close, execute only: `audit_v4_confirmatory_collection` →
   `consume_v4_confirmatory_holdout` → `prepare_v4_confirmatory_inputs` →
   `build_v4_confirmatory_examples` → `evaluate_v4_confirmatory`. Stop if any gate
   fails and never rerun the one-shot evaluator.
4. Generate final tables and figures from the hash-locked selection and holdout JSON
   only; lead with the negative incremental-news result.
5. Disclose the original v3 data-gate failure, exact v3.1 correction, holdout cohort
   attrition and receipt-order deviation in the paper.
6. Complete a claim audit, reproduction check, secret scan, artifact inventory and
   vendor-data rights review before release.
7. Keep KOL-v1/v2 failed. Treat true virality and KOL-v3 as new research directions
   requiring a fresh label-blind protocol and untouched holdout; v4 novelty and
   semantic features are already frozen and must not be changed.
8. If the prospective v2.3 replication continues, keep its collectors and source
   gates unchanged through September 28. Do not tune it using v3.1 outcomes.
9. At v2.3 close, report incomplete if exact source recovery fails; otherwise execute
   its already-frozen order without importing any v3.1 post-outcome change.
10. Carry the convergence-checked direct nonlinear B0-v5N specification into the
    new-cycle label-blind gates. It is development-selected but not frozen or confirmed.
11. If v5 continues, test only the prespecified reduced V5-R family and require
    improvement over B0-v5N plus the gated context-only negative control in a new
    development interval.
12. Run a label-blind v5 source/cohort/power audit, specify a new untouched holdout,
    then freeze at most one candidate and its evaluator before accessing that holdout.

The shortest valid confirmatory path remains frozen v4 collection plus reporting and
reproducibility. V5 implementation may proceed in parallel on opened discovery data,
but additional modeling on the consumed v3.1 holdout cannot confirm or rescue either
study.
