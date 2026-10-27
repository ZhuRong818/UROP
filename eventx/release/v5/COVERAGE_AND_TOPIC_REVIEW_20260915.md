# EventX V5 coverage and topic review

Written 15 September 2026, Asia/Singapore. Source probes and local computations
were performed on 14 September UTC. This is readiness evidence, not a new
experiment, source admission or change to an existing plan.

## Findings

### May 17 export absence explained

A successful read-only warehouse aggregate returned **12,898,490 retained articles**
with ingestion timestamps on 17 May. All 12,898,490 had ingestion lag greater than
24 hours; none passed the within-24-hour condition. Ingestion ranged from
`2026-05-17T06:42:40.084691Z` to `2026-05-17T08:37:58.818424Z`.

The existing news export excludes articles ingested more than 24 hours after
publication. Thus the observed absence of May 17 rows is explained by this filter
for the queried ingestion-day population; it is not evidence that the warehouse
contained no news. This does not establish upstream feed completeness or pre-May
availability. No backfilled article was admitted to earlier prediction times.

Evidence: `data/v5/provenance_recovery_20260908/coverage_may17_counts_20260914.json`
and its `.jsonl` output; SQL in `coverage_queries_20260914/may17_counts.sql`.

### May 19 remains unresolved

An ordered, bounded source-record query with ingestion in `[2026-05-19,2026-05-20)`
returned HTTP 200 and zero rows, with a matching materialized receipt. This supports
absence of retained rows under that predicate at query time. It does not establish
whether the feed was intentionally inactive, records were later updated to another
ingestion timestamp, an upstream outage occurred, or a provider query issue exists.
This is not an independently reconciled empty-feed certificate.

The larger three-day joined coverage query and a three-run committed-count query
both returned HTTP 400 after about 30 seconds. Neither failure is evidence of data
absence; the precise server-side cause remains unknown. The smaller May 19 and May
17 queries succeeded. All four attempts were retained; no secret-bearing error body
was saved and no provider message was sent.

### Availability lag matters for the research interpretation

Within the already exported, opened-discovery 148,543 news articles:

| Delay in minutes | Median | 90th percentile | 99th percentile |
|---|---:|---:|---:|
| Publication to ingestion | 263.83194455 | 832.83270030 | 1348.09797378 |
| Ingestion to conservative run-based availability | 24.41452577 | 122.17485759 | 586.57817009 |

These quantiles describe a filtered historical export, not all Lumid news or its
current live-service latency. Quantiles of the two delays must not be added to
infer the quantiles of total delay. The export's 24-hour filter truncates the lag
distribution. The conservative availability calculation also waits for recorded
run completion where later than ingestion.

The administrator's content assurance remains accepted provisionally. It addresses
content-version timing; it does not make late-ingested articles newly public. A
30-minute exposure window after source availability can contain articles published
hours earlier. Results therefore concern usefulness after observable source arrival,
not a clean test immediately following first public disclosure. Publication age and
source lag should be reported in the proposed diagnostic extension. Adding them as
model inputs or changing the clock would need a new specification before outcomes.

### Topic and contract-identity review

Source-only triage covers **4,651 contracts / 1,551 candidate venue events**.
There are 138 repeated-question groups covering 727 contracts. Fifteen of those
contracts lack a cached YES subtitle. Multi-leg flags cover 397 contracts.
These counts overlap and do not constitute additive exclusions.

The automatic suggestion queue separates 81 possible corporate/traditional-financial
contracts from the legacy taxonomy. Suggestions are not approved labels. A fixed
30-contract packet was selected deterministically across six suggested topics, with
at most one contract per candidate venue event.

Codex completed the first semantic review: **29 assignments, six corrections from
the suggestions, one unresolved question**. No independent second review occurred;
final approved topics and final approved families remain zero. The packet is a
balanced review aid, not a population-random accuracy sample.

Concrete corrections illustrate why the legacy categories are insufficient:

- Coinbase advertising at the World Cup: corporate activity rather than crypto
  solely because the company operates in crypto.
- Brent closing-price threshold: traditional asset-price outcome under the proposed rubric.
- Scottie Scheffler top-20 finish and Anthony Davis trade: sports rather than Other.
- SP500 threshold: traditional financial market rather than Other.
- World Cup resale-ticket price: Other pending boundary adjudication, rather than
  sporting performance.

“Will Belgium win on 2026-06-15?” lacks enough cached event/opponent context to
approve its topic. Named-outcome subtitles also distinguish earnings-call words
and political candidates, so the shared question alone cannot define associations.

Artifacts:

- `data/v5/topic_coverage_triage_20260914/report.json`: exact counts and lag summaries.
- `topic_review_queue.jsonl`: all 4,651 suggestions and identity flags.
- `review_packet.jsonl`: fixed 30-contract review packet.
- `news_run_inventory.jsonl`: all 4,088 discovery run IDs and observed row counts.
- `data/v5/topic_first_review_20260914/first_review.jsonl`: explicit first-review
  decisions, rationales and source identity, with second review left empty.

## What is now resolved and what remains

| Item | Status |
|---|---|
| News-content revision concern | Provisionally resolved by user-relayed admin assurance |
| Why May 17 has no within-lag export rows | Explained by retained backfill ages |
| May 19 intended feed coverage | Unresolved; successful predicate query returned zero |
| Failed/partial run reconciliation | Unresolved; larger aggregate queries failed |
| Topic review | First 30-contract review completed, second review pending |
| Family graph | Existing 1,523 provisional components; no final boundary approval |
| Activity strata | Prior observed-clock diagnostics available; no certified training cutoffs |
| Statistical inference | Still uncertified; earlier failed simulations preserved |

No new outcome labels, holdout payloads, forecasts or model results were accessed.
Current plans and frozen V4 artifacts were not changed.

## Next actionable work

1. Complete the second topic review and recover missing contract context/subtitles.
   Extend review to the full proposed cohort before claiming reviewed topic labels.
2. Resolve May 19 and failed-run semantics through bounded source queries or provider
   reconciliation evidence. The request should focus on those gaps and metadata
   history; do not reopen the already accepted content assurance as a generic blocker.
3. Finish family-boundary review, then define admissible historical scope and
   training-only activity cutoffs. Inventory size alone is not independent support.
4. Report source lag explicitly in the proposed study. Determine before labels
   whether the scientific question remains source-arrival prediction or requires
   faster observable news. No date/clock/feature changes have been made here.
5. Resolve inference and power before new V5 training or confirmation.
