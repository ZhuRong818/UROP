# V5 source-readiness audit — 8 September 2026

**Decision: staging complete; not yet admissible for repaired V5 training.**

Audited existing local, source-only inputs for opened discovery
`[2026-05-17, 2026-07-22)` UTC. No price/example/label/prediction files were opened,
no model was fitted, and no holdout was consumed. This does not select a new cohort.

## Completed

| Input | Finding |
|---|---|
| Market metadata | 4,651 snapshots staged: 3,832 Kalshi and 819 Polymarket |
| Kalshi event keys | Present for all 3,832 markets; 1,230 candidate venue-event groups |
| Multi-market event groups | 715; largest contains 77 markets |
| Polymarket event keys | Missing from the cached extract for all 819 markets |
| Metadata history | One cached version per market; every source ingest falls inside discovery |
| News export | 214,944 rows scanned; count agrees with the retrieval receipt |
| Discovery news | 148,543 unique IDs, zero duplicate IDs |
| News timestamp checks | All 148,543 match the conservative source/run availability calculation |
| Source lineage | All discovery news rows carry a run ID and headline or summary |

The 1,230 venue-event groups are **candidates**, not verified independent event
families. Adjacent events, related thresholds and cross-venue duplicates still need
semantic review. No slug-based or contract-hash family fallback was created.

## What prevents admission

### Historical metadata and exact content versions

The cached market extracts lack historical trading-status and validity intervals.
They contain a source ingest timestamp, but their local export completion is
1 September. The news export completed on 2 September. A checksum of those exports
proves which bytes we downloaded, not that the exact same content was present at the
earlier ingest timestamp.

This is **missing evidence**, not evidence that Lumid actually revised the records.
An immutable source-row guarantee supported by lineage, or historical versioned
payloads, could establish earlier content availability. We have not assumed the
download date was the original publication date or declared historical analysis
impossible. Staging preserves both clocks and leaves unproven historical content
availability null.

The existing as-of adapter also needs an affirmative historical market-status rule.
Scheduled opening/closing timestamps alone should not silently stand in for an
unobserved suspension/status history.

### News run status and completeness

| Linked run status | Discovery articles |
|---|---:|
| ok | 49,992 |
| completed | 3,561 |
| partial | 26,892 |
| failed | 68,037 |
| aborted | 61 |

There are 94,990 rows associated with partial/failed/aborted runs. A failed batch may
still contain valid committed articles; these rows must not automatically be deleted.
Conversely, consistent timestamps and a matched export row count do not establish
that all intended articles arrived. Reconcile each affected run against requested
coverage, committed rows, retries and recovered gaps.

The existing news SQL also applies publication/ingestion and 24-hour-lag filters.
Its receipt proves the returned filtered export count, not completeness of the global
news warehouse. Source/exposure availability remains a separate gate.

## Deliverables

`data/v5/source_readiness_20260908/` contains:

- `metadata_staging.jsonl`: projected metadata, separate ingest/observed clocks,
  source-file/line pointers and explicit missing proofs.
- `family_review_queue.jsonl`: market questions/categories, candidate event groups
  and empty reviewer/evidence/approved-family fields.
- `news_provenance_staging.jsonl`: article IDs, source-file/line pointers, exact
  headline/summary hashes and timestamp checks. Text stays in its existing archive.
- `report.json`: exact counts and failed admission gates.
- `manifest.json`: input, source-code and output hashes.

Every staged row remains `training_admissible=false`; every family remains
`family_verified=false`. No missing field is replaced with a guessed value.

Implementation: `eventx/tasks/prepare_v5_source_readiness.py`. Four synthetic tests
passed for candidate-versus-verified families, absence of slug/hash fallbacks,
source/run timestamp consistency and rejection of ambiguous clocks.

## Targeted next acquisition and review

The next useful work is targeted provenance recovery, not another bulk news dump:

1. Recover **condition-to-event mappings for the 819 Polymarket conditions**, with
   source identifiers, observation/version times and source-run evidence. An event
   key must not be mistaken for a token or market ID.
2. Recover **versioned market question, category, token mapping, scheduled terminal,
   trading status and validity history** for the audited markets. Preserve immutable
   original records and distinguish source-event from source-availability times.
3. Obtain **article-content version evidence** linking exact headline/summary bytes
   to their availability, or validate authoritative immutability semantics and lineage.
4. Reconcile the partial/failed/aborted news runs with batch status semantics, query
   windows, committed counts, retries and gap-recovery receipts. Do not use status
   alone to infer row invalidity or interval completeness.
5. Review event-family membership using contract semantics, including dependencies
   across venue events and venues. Only then approve an immutable mapping version.
6. Build corrected as-of examples only after those source gates pass, then audit
   warm-up support, coverage and exposure without labels. A later new-data test still
   needs an untouched interval disjoint from protected V4.

These requests describe required evidence; they do not assert that a particular live
Lumid route currently exposes it. The missing fields are absent from the audited local
extracts, not proven absent from the provider.
