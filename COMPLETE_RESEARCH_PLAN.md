# EventX complete research and experiment plan

**Program:** EventX — incremental social-media information in prediction-market price discovery  
**Planning status:** consolidated umbrella plan; not itself a frozen protocol  
**Created:** 2026-08-10  
**Last revised:** 2026-08-17 (v2.3 news availability and decision contract)  
**Active controlling experiment:** `eventx-v2.3-news-availability-clarifications-20260817`  
**Internal deadline for the active cycle:** 2026-10-31  

This document consolidates the research goals, required data, methods, experiments,
execution sequence, statistical tests, integrity controls, deliverables, and longer-term
benchmark path. It is a planning and coordination document. It does **not** modify or
supersede the sealed v1 artifacts or the consumed v1 holdout. The frozen v2.3
preregistration now controls the active experiment; v2.2 and v2.1 remain immutable
lineage.

The controlling sources for an actual run remain:

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

The program has two deliberately separated deliverables:

1. **Active prospective pilot (v2.3):** a leakage-safe, preregistered experiment on the
   frozen 14-market Polymarket/Kalshi cohort, completed by October 31, 2026.
2. **Full EventX benchmark:** a later, broader, multi-category and longer-window
   benchmark with redundant Lumid acquisition paths, greater market-level sample size,
   stronger microstructure coverage, a reusable Feature Track, and an extensible
   Rehydration Track.

The v2.3 pilot may validate the protocol and provide a reference finding. It must not
be described as the completed deep-historical benchmark.

The October paper/report is positioned as **“A prospective protocol-validation study
of incremental news information in prediction-market repricing.”** Its abstract and
primary conclusion concern B1 versus B0. The broader KOL objective remains the EventX
program direction and is explicitly deferred because KOL-v2 failed its association
validation threshold.

### Current research direction and minimal-change rule

The long-run scientific direction remains incremental KOL information beyond market
history and news. The active v2.3 confirmatory experiment is
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
The contract was rechecked on 2026-08-17 and contained 169 paths and 171 operations.
Its retrieved document SHA-256 was
`ef50330e2725b2c725e2049a93d248e09da98d4ccf0aaa70375f077e6680be22`.
Every endpoint named below was present. Read-only live probes on that date returned
HTTP 200 for all required REST route families and for the representative optional REST
routes described below; some optional market/window queries returned empty arrays.

Contract presence and HTTP 200 are necessary but not sufficient. A source becomes
experiment-usable only after its response contains the required fields, its event-time
coverage reaches the exact cutoff, duplicates and malformed/future-dated rows are
handled, and the frozen completeness report passes. This distinction matters because
Lumid returned service-wide HTTP 500s from August 10 until the current recovery, and
the running collector still has gaps and a stale KOL cache.

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
7. Run all ten Section 6.6 checks, then freeze reconciled inputs, query specs, OpenAPI
   contract, code/config and hashes. Stop if the gate fails.
8. After the data gate passes, run the synthetic 14-market cluster power/precision
   simulation without empirical labels, prevalence or outcome paths.
9. Freeze the simulation configuration, seed and output. Its findings may disclose
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
| Aug 8–Sep 27 | Lumid development collection | Continue append-only capture; quantify the August outage and stale/empty-source behavior |
| Sep 28–30 | Exact-window reconciliation, labels, development evaluation and freeze | Reconcile `[Aug 8, Sep 28)`, pass Section 6.6, run frozen B0/B1 once, and freeze one candidate before Oct 1 |
| Oct 1–21 | Holdout collection | No model selection or outcome inspection |
| Oct 22 | One-shot evaluation | One result and consumption receipt |
| Oct 22–31 | Finalization | Internal report and reproducibility package complete |

If an upstream gate cannot be completed without violating the schedule or integrity
contract, report v2.3 incomplete. Do not move dates after inspecting affected labels.

### 15.1 Feasibility assessment as of 2026-08-17

- **B1 versus B0 is scientifically realistic:** cohort, taxonomy and accepted news
  association logic are already frozen; the learner and evaluation contract are fixed;
  development/holdout labels remain unopened.
- **Lumid trade mechanics passed the elapsed-window drill:** the required market-detail
  and venue-trade routes exist, all 14 canonical mappings and trade integrity checks
  passed, and 5,817 canonical-YES trades were recovered. Several sparse Polymarket
  markets have long intertrade gaps, which makes the price-age robustness essential.
- **News completeness is currently blocked:** `/news/latest` silently capped the broad
  request at 200 rows and exposes neither a cursor nor an upper-time parameter. Lumid
  `/news/stats` reports 10,861 `company` rows in the last seven days, so category-only
  partitioning cannot by itself establish completeness. The two outside-window rows
  were quarantined, and the 21 frozen search queries did not cap.
- **The censoring behavior is now executable and auditable:** v2.3 freezes 60-second
  polling, a 200-row cap alarm, a 300-second maximum successful-request gap, no
  checkpoint advance on capped/failed responses, identical holdout behavior, and
  `available_at = max(published_at, first_seen_at)`. Offline fixtures verify the cap,
  gap and availability behavior. The running legacy daemon has not been restarted and
  is explicitly not represented as compliant.
- **The timing contradiction is resolved:** development now ends September 28, leaving
  a fixed 72-hour reconciliation, evaluation, and candidate-freeze buffer before the
  October holdout. The schedule remains tight but is logically executable.
- **B3/KOL is not realistic on the current critical path:** the rule failed and recent
  KOL feed behavior is stale/empty. A new KOL-v3 audit would add material schedule and
  data risk without changing the already valid B1/B0 fallback.
- **Overall verdict:** the October pilot is conditionally feasible as B1 versus B0 (or
  B0 if news coverage fails), but not yet guaranteed. Failure of exact Lumid coverage
  or timing gates produces a valid incomplete result; it does not justify a new source,
  a date change after labels, or an early holdout opening.

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

1. Keep the recovered legacy collector and health ledger under observation without
   calling its news cursor v2.3-compliant or inspecting protected labels.
2. Decide and record an explicit migration/restart or parallel-launch time for the
   frozen v2.3 news collector. Its start receipt must preserve all earlier unresolved
   intervals; no launch may silently reset the completeness state.
3. Preserve KOL-v2 as failed and use the accepted-news B1-versus-B0 branch; do not
   spend the current schedule on KOL-v3 unless that choice is separately authorized
   before labels.
4. Resolve the recorded `/news/latest` 200-row cap without changing datasource: seek a
   valid Lumid cursor/time-partition or a Lumid-provided endpoint-equivalent export with
   catalog/lineage evidence. Category partitioning alone is insufficient at the
   observed volume. Preserve the incomplete rehearsal as evidence.
5. Continue Lumid trade/news capture and focused bounded recovery for the 14 frozen
   markets and accepted news query specifications.
6. At development close, reconcile `[2026-08-08, 2026-09-28)` from the exact endpoints
   in Section 6 and produce the per-market/per-day completeness report.
7. Run and freeze the label-blind data sufficiency gate, then run and freeze the
   synthetic 14-market cluster power simulation. Only afterward create development
   labels, the uniform last-trade B0/B1 features and frozen folds.
8. Run B0 and B1 once on identical keys, apply H1_v2.3–H5_v2.3 and the conservative
   undefined-metric rules, and freeze
   B1 if it promotes, otherwise B0.
9. Keep the October holdout sealed from selection; after it closes, reconcile Lumid
   inputs and run the frozen evaluator exactly once.
10. If required Lumid inputs or timing gates fail, report the affected branch or cycle
   incomplete rather than introducing another datasource or weakening a threshold.

This sequence is the shortest path to a valid October result. Skipping an upstream
freeze may make the experiment faster to run, but it would make the result unusable.
