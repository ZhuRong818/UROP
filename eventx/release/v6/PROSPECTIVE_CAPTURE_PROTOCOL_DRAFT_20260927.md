# Prospective V6 source-capture protocol — draft

Date: 27 September 2026. This is a separate V6 fallback design if historical version/status/feed proof is unavailable. It is **not launched**, not a new confirmation freeze and not an edit to the protected V4 collection. No future price, outcome or V4 sealed payload is used here.

## Purpose and scope

Capture the exact article and contract bytes as first observed, with repeated version/status snapshots and full bounded feed receipts. A local timestamp proves when this collector saw a payload; it does not prove first public publication or complete provider coverage. The declared feed, query scope, pagination and provider-run reconciliation must be frozen before interpreting an empty day as zero news.

Run an initial **development-only source feasibility window** after a new receipt/freeze, using contract selection from then-current active single-event metadata and predeclared topic/activity strata. Record all selected and excluded contract IDs and reasons before looking at any future repricing. Exclude V4's 470 frozen contracts and any contract/story/event family that could overlap its protected interval; unresolved overlap is quarantined. Do not reuse V4 collector code or modify its manifests, process, checkpoints, cohort or output directories. No forecast confirmation cohort is drawn from this pilot.

## Immutable capture objects

| Object | Required fields and receipt |
| --- | --- |
| Feed request | Endpoint, query, filters, declared provider feed universe, UTC window, page/keyset boundary, response code, retry/backoff chain, provider run ID, request and response SHA-256; credentials omitted from receipts. |
| Article version | Provider article ID, raw headline/summary bytes and SHA-256, source/publisher/URL, publication and provider-ingest clocks, collector first-seen UTC, each later changed-byte version with prior-version link. Keep duplicate and syndicated IDs. |
| Contract version | Venue/contract/event/leg IDs, question/subtitle/rules/token side, raw payload SHA-256, provider-ingest and collector-seen clocks, observed open/suspended/closed status, valid interval if supplied; never backdate a later snapshot. |
| Trade observation | Venue execution ID/time, arrival time, token/YES mapping, price, size, source page/run and deduplication key. Raw trades are sealed separately from source-quality checks when reserved for future evaluation. |
| Daily coverage | Requested/received page and row counts, keyset continuity, source-run commit/retry lineage, time-range coverage, raw and normalized hashes, empty-window proof, failures/caps marked unknown. |
| Link and split provenance | Candidate retrieval channel, article/story ID, provisional event family, contract applicability, reviewer decision and uncertainty; annotations never overwrite source payloads. |

Use append-only, date-partitioned raw storage and a manifest chaining each day's input/output hashes. Create a pre-request receipt for each pull. Store tokens only in `.env`; log no authorization headers or credentials. Resume from the last verified keyset, not a guessed timestamp. A failed or capped partition remains `unknown` until reconciled.

## Separation and operating rules

- First phase is source/readiness development: no prediction labels, feature selection from future outcomes or claim of untouched confirmation. Keep the exact first-observed bytes even when a provider later updates an article or contract.
- Before any later confirmation phase, freeze the supported population, 30-minute target and YES mapping, content-neutral T definition, linker/class policy, story/family isolation, model/inference code, sample size and stop rule. Allocate a future nonoverlapping time window and record a consumption receipt before its one-shot evaluation.
- Capture the complete declared news feed in selected windows, including nonmatches, plus at least seven days of prior available history if novelty is examined. A keyword-only or matcher-returned export cannot measure missed links or no-news controls.
- Run daily label-blind health checks of process, request receipts, page continuity, schema and payload hashes. A process being alive does not certify provider completeness. Source-quality failures block admissions for affected windows; they do not become zero counts.
- Do not claim independent forecasting power until distinct reviewed stories/event episodes, supported contract-days and exposure concentration are counted. Set the required pilot duration and final cohort size by a development-only power and synthetic-coverage calculation, not by a desired significant result.

## Launch gate

Before any collector starts, issue a versioned manifest with selected active contracts, V4 overlap exclusion, precise feed routes/filters, capture cadence, storage paths, retry/retention rules, source completeness criteria, and a start receipt. Verify credentials and endpoint schema without printing secrets. A later change creates a new capture version and preserves the failed/partial one. The current historical provider request and 102-pair human review proceed independently; neither is replaced by this draft.
