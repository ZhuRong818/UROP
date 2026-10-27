# EventX V6: scoped historical source-evidence request

**To:** Lumid findata ingestion and prediction-market data owners  
**Date:** 2 October 2026  
**Study interval:** `[2026-05-17, 2026-07-22)` UTC, opened development only  
**Attachment:** `LUMID_EVENTX_V6_SCOPE_20261002.json` (nine article/run IDs, nine proposed decision clocks, content hashes, 15 contract IDs, two global zero-export days)

We are checking whether a Lumid-fed EventX analysis can reconstruct **what was available and tradable at each historical decision time**. Please return the operational records below for the attached scope. If a record was not retained, identify the unavailable field, system, and retention limit. A current row or a later successful retry should not be described as historical coverage at an earlier time.

This request does not ask for market prices, resolutions, credentials, protected V4 data, or a model evaluation. It asks for source, clock, completion, and status evidence. We will keep unreceipted intervals `unknown`.

## What we have already established

- Our configured live `https://lum.id/findata` catalog and SQL surfaces returned all nine article run IDs. Four scoped runs are `ok`; five Finnhub `company-news` runs are `failed` after abandonment. A retained article linked to a failed run proves a row exists, not that the requested feed window completed.
- `finnhub:company-news` uses one endpoint cursor with `scope_key=''`. It does not retain a separate NVDA/MSTR cursor. The visible `provenance.runs.args` gives Finnhub `to` and `n_symbols`, without an effective `from` or the requested symbol list. Three scoped FMP `ok` runs have explicit `from`/`to`; those bounds do not prove every page completed.
- The current `reference.symbol_universe` has one FMP-seed row each for NVDA and MSTR, ingested 19 May before the nine proposed clocks. This proves reference-roster membership under the retained validity fields, **not** inclusion in each Finnhub request. Live run arguments change from 7,851 to 7,258 symbols on 28 May 22:30 UTC and from 7,258 to 7,220 on 27 June 19:15 UTC. The 7,851 roster includes 593 ETF/fund rows, so ETF/fund exclusion is a possible explanation for 7,258; the collector filter is unverified.
- EventX derives `available_at` as the maximum of publication time, `ingest_ts`, run start, and run end (falling back to `ingest_ts` for missing run end). It is **not** a stored first-client-delivery field. For the five failed runs it equals the later abandonment-cleanup time. We have kept that conservative decision clock and have not substituted publication time or `ingest_ts`.
- Each of the 15 scoped market IDs has one retained row on our read surface. That row does not establish earlier active/suspended state or unchanged question, YES/NO mapping, and rules. The visible schema has no historical status/version interval.
- The frozen EventX support ledger has 268 `zero_export_rows_not_proven_empty` contract-days. These are **two EventX filtered-export days, 17 and 19 May, repeated across 134 contracts**, not 268 independent Lumid requests or evidence that Lumid stored no articles. Neither filtered export day is certified as a complete zero.

The attached JSON contains the exact scope. The nine article/run pairs are summarized here so the request can be triaged without opening the attachment:

| Article ID | Run ID | Run status | Proposed EventX decision time (UTC) |
| --- | --- | --- | --- |
| 102500031 | `510bc928-4d72-466b-be04-00532d6051c2` | ok, FMP | 2026-05-23 15:19:29.435984 |
| 152232532 | `eb87b497-a8b2-4d98-a763-5269bf7e5c1c` | ok, FMP | 2026-05-26 08:15:07.502489 |
| 166357183 | `d8bcb0d0-be28-4a0a-920c-d6087a07e5a8` | failed, Finnhub | 2026-05-30 13:52:00.659674 |
| 168034724 | `c40c9e49-4a6a-44d1-a0d9-43ca033d21ae` | failed, Finnhub | 2026-06-01 16:22:01.898330 |
| 189518836 | `fd734424-86f2-4d65-a67c-868d6f80730a` | failed, Finnhub | 2026-06-23 18:52:01.311813 |
| 193693829 | `377266b5-b120-47f1-88fc-de86ee87462b` | ok, FMP | 2026-06-28 06:17:55.446337 |
| 197137081 | `592ebc42-79ad-4b33-af2d-628b5edb6167` | failed, Finnhub | 2026-06-30 04:52:01.676592 |
| 201756152 | `86c568d4-f947-43e2-950b-8cf740690a9e` | failed, Finnhub | 2026-07-02 18:37:01.281842 |
| 211869183 | `ad764123-d034-44db-aa25-a156ab855fe2` | ok, Finnhub | 2026-07-09 14:59:45.841566 |

## 1. Article commit, visibility, and version semantics

For the exact article IDs and content hashes in the attachment:

1. At what operation is `news.articles.ingest_ts` stamped: receipt, upsert attempt, committed row, or first query-visible row? Can a later correction overwrite the same row while retaining an earlier `ingest_ts` or `source_run_id`?
2. Are the first committed headline/summary bytes and subsequent edits, deletions, or replacements retained with their own timestamps and hashes? If not, state whether the retained row alone can establish the bytes that were visible at each attached decision time.
3. Is there any first client-read/delivery or query-visibility log for the exact row version? If not, confirm that no such per-client claim can be reconstructed. We can use the existing conservative EventX `available_at` if its construction cannot precede the row version's visibility, but we will not label it “first delivery.”

Please return the field/operation definition or code version and any exact row/version receipt. A statement about feed refresh cadence is insufficient to establish a row's first visibility.

## 2. News-window and symbol coverage at each decision time

For **all nine runs**, including the four `ok` runs, please locate retained loader/Finnhub collector file logs or another source of per-request evidence. We found no queryable page, per-run symbol-roster, per-window completion, or historical-cursor table through our read role; this does not rule out file logs or a private archive. Please identify the log path/system, retention policy, and relevant collector code/config version.

For each run return:

- effective `requested_from` and `requested_to`, how the Finnhub `from` was derived from the previous cursor, endpoint/feed scope, and exact requested symbol list or a versioned list/hash that can prove NVDA/MSTR inclusion;
- pages or keysets requested, completed, retried, and failed; row counts and write failures by scope; source response status and any truncation/rate-limit/cap indicators;
- retry/successor run IDs, the **time each relevant window completed**, and the historical cursor value/transition. For partial or abandoned runs, identify which pages or symbols actually persisted;
- whether the declared scope/window was complete **before the attached decision time**. A run ending later, a later retry, and the present overwritten cursor cannot backdate completion.

Please explain the two dated `n_symbols` changes (7,851→7,258 on 28 May; 7,258→7,220 on 27 June) with the actual filter/configuration or roster history. Numeric equality with the FMP reference roster is only a hypothesis about the first change. The first 7,851-count Finnhub run also predates the retained FMP roster ingest, so the count match alone cannot prove which table was read.

For the EventX **filtered news export** on **17 and 19 May 2026 UTC**, provide the declared feed universe, query/filter definitions, and complete request/page/cursor receipts needed to determine whether each filtered result was genuinely empty. Lumid may hold other articles on those days; the zero refers to this export only. If complete-zero proof does not exist, please mark those two filtered days `unknown`. The 268 EventX contract-day cells are repeated views of these two days, not separate Lumid collection runs.

## 3. Historical market terms and tradability

For the **15 contract IDs** in the attachment at each of the **nine proposed decision times** (135 market-time cells, including not-yet-open and closed states), provide:

- first tradable time, active/accepting-orders status, suspension/reopen/early-close intervals, and the evidence source with its observation or effective time;
- the question/subtitle, YES/NO token mapping, operative rules/resolution text, and any changes with first valid and first Lumid-visible times;
- the distinction between Kalshi `open_time`/`close_time` and settlement, and between Polymarket nominal `start_date`/`end_date` and actual CLOB tradability.

If only latest-state market snapshots are retained, please explicitly return `unknown` for historical intervals and identify whether venue archives, raw API payloads, event logs, or another Lumid service holds earlier versions. One current row per contract cannot establish that terms or status were stable.

## 4. Trade-feed integrity for later outcome construction

Please document, for these 15 contracts, the trade endpoint(s), pagination/keyset contract, execution ID and deduplication rule, late trades/corrections, token-to-YES mapping, and whether a time interval with zero returned trades can be certified as genuinely empty. Identify any retained extraction receipts or known gaps. Raw trade prices or outcomes are **not** requested in this source-assurance reply; feed semantics and receipts are enough for this item.

## Requested response format

Please provide a short explanation plus JSONL or CSV with separate `news_window` and `market_at_decision` rows. Each row should include:

`source_surface`, `deployment_or_replica`, `queried_at_utc`, `endpoint_id`, `scope_key`, `article_id` or `contract_id`, `run_ids`, `requested_from`, `requested_to`, `symbol_list_or_hash`, `pages_requested`, `pages_completed`, `pages_failed`, `completed_at`, `cursor_advanced_at`, `decision_time`, `coverage_at_decision` (`covered` / `incomplete` / `unknown`), `market_status_at_decision`, `terms_version_or_hash`, `receipt_id_or_uri`, and `unavailable_reason`.

Null is acceptable when a field was never retained. Please distinguish records observed on a stale replica from records on the live service. For any `covered` classification, the receipt must bind the **exact scope and interval** and precede the applicable decision time. Please do not infer complete coverage or a clean zero from `status=ok`, an endpoint-level row count, a current cursor, or a later retry alone.

## Separate operational issues

1. **Read replica:** A researcher reports that a cluster-internal read path stopped near 7 June 2026 while `https://lum.id/findata` still returns the scoped June/July runs. Please identify that read surface, confirm its snapshot/replication timestamp, and restore or repoint it. This is an operations issue; replica repair does not certify historical feed windows.
2. **Audit-log credential exposure:** A researcher separately reported a credential-bearing error in `lumid_data_meta.audit_log`. Please route the sanitized incident description through a restricted security channel, check whether the credential remains valid, rotate/remediate as needed, and prevent credentials from being persisted in error logs. **Do not include the raw error or credential in this research response.**

If historical page/symbol/status records do not exist, a clear negative answer is useful: we will preserve those retrospective cells as `unknown` and use a new prospective capture protocol with append-only page, cursor, roster, row-version, and market-status receipts. Tweet-to-market research is a separate future source cycle and is not part of this nine-article V6 request.
