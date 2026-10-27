# EventX historical-source certification request

Prepared 2026-09-10; **NOT SENT**. No credentials included.

We can retrieve historical metadata and news from Lumid. Our remaining issue is
point-in-time certification, not endpoint reachability or missing event IDs.
Please provide evidence or identify a supported read-only export for the following.

## 1. Historical exact-content and metadata availability

For `news.articles` and Polymarket/Kalshi market metadata, can the exact payload at a
historical timestamp be recovered? We need archived versions or an authoritative
immutability statement explicitly covering the relevant table, field and time range,
supported by ingestion/version lineage. A current row's `ingest_ts` alone is not
sufficient if content can subsequently be updated while that timestamp is retained.

Required metadata fields include question, YES/NO subtitle and contract rules,
canonical outcome/token mapping, category, scheduled terminal and trading status.
For articles, exact headline/summary bytes, stable identity, first-seen and version
availability are needed. Please distinguish event/publication time, initial ingest,
later mutation and local export time; disclose deletion/backfill semantics.

Our existing engineering-recovery scope is `[2026-05-17,2026-07-22)` UTC. These
outcomes are already opened; certifying that scope would improve the source pipeline,
not make it an untouched confirmation set. Please also state the earliest/latest
coverage of any version archive so a separate unopened scope can be assessed without
requesting outcome data. We do not request protected V4 `[2026-09-06,2026-10-30)` data.

## 2. Committed rows, retries and completeness

Please explain the committed-row and retry coverage of these three example runs:

| Run ID | Endpoint | Live metadata observation |
|---|---|---|
| `592ebc42-79ad-4b33-af2d-628b5edb6167` | finnhub:company-news | failed/abandoned cleanup; write counters null; requested to June 30 |
| `5022dbb8-a4b4-40fa-9aed-8e88b7363572` | finnhub:company-news | failed/abandoned cleanup; write counters null; requested to June 18 |
| `b2ea4fcf-57e1-46f4-82dc-5f6c0ea60a62` | fmp:stable/news/crypto-latest | failed/abandoned cleanup; write counters null; request dates 2020-01-01 to 2026-05-29 |

We are not assuming that their committed articles are invalid. We need requested
coverage, commit receipts, successor/retry IDs and resolved/unresolved gaps for the
declared feed universe. Current retained table counts need not equal original writes
after upserts/deduplication, so please specify counter and natural-key semantics.

The complete prior priority sample contains 20 runs, listed locally in
`data/v5/certification_probe_20260910/request_plan.json`. Further staged run IDs and
article hashes can be supplied through a scoped, non-secret attachment if needed.

## 3. What we tested on September 10

- Broad accessible archive/version/request/response schema inventory returned 103
  field rows; it exposed no matching news/market-metadata version archive.
- Visible trigger inventory for the four relevant tables returned zero rows. We
  recognize that role visibility and application-level guarantees may explain this;
  we do not infer that no private archive/immutability enforcement exists.
- A bounded 20-run retained-article reconciliation query returned HTTP 400 after
  about 30 seconds. Cause unconfirmed. A three-run metadata-only fallback succeeded.

Please provide endpoint/table documentation and the supporting evidence above, or
confirm which proofs cannot be supplied. We will keep the research admission gate
closed for unsupported fields/intervals rather than backdating current payloads.
