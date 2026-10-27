# Lumid findata: historical collector and read-surface bug report

**Triage status:** Open; please classify each issue as a defect, an unsupported historical capability, or unable to reproduce.  
**Suggested priority:** P1 for the reported stale read surface and failed-run recovery; P2 for missing historical auditability. The reported credential exposure is a separate security incident for restricted review.

**To:** Lumid findata ingestion and prediction-market data owners  
**Date:** 2 October 2026  
**Study interval:** `[2026-05-17, 2026-07-22)` UTC, opened development only  
**Scope:** Nine article/run IDs, nine proposed decision clocks, 15 contract IDs, and two filtered-export days; the exact machine-readable list is in Appendix A below.

**Problem:** The current Lumid read surfaces return the scoped rows and run summaries, but they do not let us determine which news windows completed or which market terms and trading states were visible at the historical decision times. Five scoped Finnhub runs ended as failed/abandoned. A researcher also reports that one cluster-internal read surface stopped updating in early June, while the live findata API returns later runs. Please investigate the failures and read-surface divergence, then state which historical evidence is retained. If a capability was never provided, classify it as such rather than as a defect.

This request does not ask for market prices, resolutions, credentials, protected V4 data, or a model evaluation. It asks for source, clock, completion, and status evidence. We will keep unreceipted intervals `unknown`.

## Triage summary

| Issue | Observed behavior | Expected behavior or contract to clarify | Status |
| --- | --- | --- | --- |
| A. Collector recovery | Five scoped Finnhub jobs ended failed/abandoned; retained rows exist, but completion by decision time cannot be established from run summaries. | Failed scopes should have a traceable retry/completion state, or be explicitly marked incomplete. | Failed runs confirmed on live lineage; recovery details unknown. |
| B. Read-surface freshness | The live findata API returns three June/July run IDs that a researcher could not see on a cluster-internal read path. | A read endpoint described as current should expose its replication lag and converge with the authoritative store. | Stale-replica diagnosis reported; Lumid confirmation needed. |
| C. Historical auditability | The readable database exposes a latest-only cursor and one retained row for each scoped market; no per-page or market-status history was visible. | If historical point-in-time queries are supported, the associated page, cursor, roster, and status records should be retrievable. | Capability or retention gap; not yet established as a software defect. |
| D. Timestamp and version meaning | The EventX decision clock is derived; the first visible version of an article cannot be reconstructed from the fields we have. | Document the commit/visibility and update semantics of the stored article fields. | Documentation or instrumentation question. |
| E. Audit-log secret | A researcher reports a credential-bearing error in an API audit log. | Credentials must not persist in ordinary diagnostic logs. | Security incident pending restricted verification; no secret included here. |

## Reproduction and evidence

1. On the live https://lum.id/findata surface, call GET /catalog/lineage/run/{run_id} for the nine run IDs in the table below. Four return ok and five return failed/abandoned. The retained article rows linked to failed runs do not supply page or symbol completion receipts.
2. On both read surfaces, query provenance.runs for the three post-8-June run IDs:

       SELECT run_id, endpoint_id, started_at, ended_at, status, args
       FROM provenance.runs
       WHERE run_id IN (
         'fd734424-86f2-4d65-a67c-868d6f80730a'::uuid,
         '592ebc42-79ad-4b33-af2d-628b5edb6167'::uuid,
         '86c568d4-f947-43e2-950b-8cf740690a9e'::uuid
       );

   The live API returned all three. The researcher-reported cluster-internal read path returned none and reported a maximum run start near 7 June. Please repeat on both surfaces and return deployment, role, query time, and replica lag.
3. Inspect provenance.scrape_cursor for finnhub:company-news. It has one endpoint-wide empty scope key and only current cursor fields. Inspect the nine provenance.runs argument objects: Finnhub records to and n_symbols but no effective from or per-run symbol list. The observed symbol counts change on 28 May and 27 June.
4. Inspect historical versions for the 15 contract IDs in Appendix A. Our live read role returned one retained market row per ID, with no queryable status or term-version interval. Please identify any other archive that can reproduce the state at the nine listed clocks.

## Observed results

- Our configured live `https://lum.id/findata` catalog and SQL surfaces returned all nine article run IDs. Four scoped runs are `ok`; five Finnhub `company-news` runs are `failed` after abandonment. A retained article linked to a failed run proves a row exists, not that the requested feed window completed.
- `finnhub:company-news` uses one endpoint cursor with `scope_key=''`. It does not retain a separate NVDA/MSTR cursor. The visible `provenance.runs.args` gives Finnhub `to` and `n_symbols`, without an effective `from` or the requested symbol list. Three scoped FMP `ok` runs have explicit `from`/`to`; those bounds do not prove every page completed.
- The current `reference.symbol_universe` has one FMP-seed row each for NVDA and MSTR, ingested 19 May before the nine proposed clocks. This proves reference-roster membership under the retained validity fields, **not** inclusion in each Finnhub request. Live run arguments change from 7,851 to 7,258 symbols on 28 May 22:30 UTC and from 7,258 to 7,220 on 27 June 19:15 UTC. The 7,851 roster includes 593 ETF/fund rows, so ETF/fund exclusion is a possible explanation for 7,258; the collector filter is unverified.
- EventX derives `available_at` as the maximum of publication time, `ingest_ts`, run start, and run end (falling back to `ingest_ts` for missing run end). It is **not** a stored first-client-delivery field. For the five failed runs it equals the later abandonment-cleanup time. We have kept that conservative decision clock and have not substituted publication time or `ingest_ts`.
- Each of the 15 scoped market IDs has one retained row on our read surface. That row does not establish earlier active/suspended state or unchanged question, YES/NO mapping, and rules. The visible schema has no historical status/version interval.
- The frozen EventX support ledger has 268 `zero_export_rows_not_proven_empty` contract-days. These are **two EventX filtered-export days, 17 and 19 May, repeated across 134 contracts**, not 268 independent Lumid requests or evidence that Lumid stored no articles. Neither filtered export day is certified as a complete zero.

Appendix A contains the exact machine-readable scope. The nine article/run pairs are summarized here:

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

## Issue D — Article commit, visibility, and version semantics

**Observed:** The EventX decision time is a conservative derivation, while the stored article row does not expose a first-delivery or revision history to our read role. **Expected or contract to clarify:** The timestamp and update semantics should identify which exact bytes were query-visible at a historical time, or explicitly state that this cannot be reconstructed. **Impact:** A publication timestamp could incorrectly backdate model access by hours; an overwritten article could be mistaken for its earlier version.

For the exact article IDs and content hashes in Appendix A:

1. At what operation is `news.articles.ingest_ts` stamped: receipt, upsert attempt, committed row, or first query-visible row? Can a later correction overwrite the same row while retaining an earlier `ingest_ts` or `source_run_id`?
2. Are the first committed headline/summary bytes and subsequent edits, deletions, or replacements retained with their own timestamps and hashes? If not, state whether the retained row alone can establish the bytes that were visible at each listed decision time.
3. Is there any first client-read/delivery or query-visibility log for the exact row version? If not, confirm that no such per-client claim can be reconstructed. We can use the existing conservative EventX `available_at` if its construction cannot precede the row version's visibility, but we will not label it “first delivery.”

Please return the field/operation definition or code version and any exact row/version receipt. A statement about feed refresh cadence is insufficient to establish a row's first visibility.

## Issue A — Failed collector runs and untraceable window recovery

**Observed:** Five Finnhub jobs in the scoped lineage ended failed/abandoned, while some rows from failed jobs persisted. The run ledger and latest-only cursor do not establish which symbols/pages completed by the proposed decision clocks. The four ok runs likewise lack per-page completion evidence. **Expected or contract to clarify:** Each requested scope should have a retrievable completed, incomplete, or unknown state with dated retry lineage; if this was never supported, please confirm that limitation. **Impact:** We cannot certify historical feed coverage or treat missing articles as a clean zero.

For **all nine runs**, including the four `ok` runs, please locate retained loader/Finnhub collector file logs or another source of per-request evidence. We found no queryable page, per-run symbol-roster, per-window completion, or historical-cursor table through our read role; this does not rule out file logs or a private archive. Please identify the log path/system, retention policy, and relevant collector code/config version.

For each run return:

- effective `requested_from` and `requested_to`, how the Finnhub `from` was derived from the previous cursor, endpoint/feed scope, and exact requested symbol list or a versioned list/hash that can prove NVDA/MSTR inclusion;
- pages or keysets requested, completed, retried, and failed; row counts and write failures by scope; source response status and any truncation/rate-limit/cap indicators;
- retry/successor run IDs, the **time each relevant window completed**, and the historical cursor value/transition. For partial or abandoned runs, identify which pages or symbols actually persisted;
- whether the declared scope/window was complete **before the listed decision time**. A run ending later, a later retry, and the present overwritten cursor cannot backdate completion.

Please explain the two dated `n_symbols` changes (7,851→7,258 on 28 May; 7,258→7,220 on 27 June) with the actual filter/configuration or roster history. Numeric equality with the FMP reference roster is only a hypothesis about the first change. The first 7,851-count Finnhub run also predates the retained FMP roster ingest, so the count match alone cannot prove which table was read.

For the EventX **filtered news export** on **17 and 19 May 2026 UTC**, provide the declared feed universe, query/filter definitions, and complete request/page/cursor receipts needed to determine whether each filtered result was genuinely empty. Lumid may hold other articles on those days; the zero refers to this export only. If complete-zero proof does not exist, please mark those two filtered days `unknown`. The 268 EventX contract-day cells are repeated views of these two days, not separate Lumid collection runs.

## Issue C — Historical market status and terms cannot be reconstructed

**Observed:** Our read role returned one retained row per scoped contract and no queryable status or term-version trail. **Expected or contract to clarify:** If Lumid supports historical point-in-time market data, it should return the active state and operative terms at a requested clock. Otherwise, please identify this as a snapshot-only limitation. **Impact:** A nominal market date or current flag can misclassify whether a contract was tradable when an article arrived.

For the **15 contract IDs** in Appendix A at each of the **nine proposed decision times** (135 market-time cells, including not-yet-open and closed states), provide:

- first tradable time, active/accepting-orders status, suspension/reopen/early-close intervals, and the evidence source with its observation or effective time;
- the question/subtitle, YES/NO token mapping, operative rules/resolution text, and any changes with first valid and first Lumid-visible times;
- the distinction between Kalshi `open_time`/`close_time` and settlement, and between Polymarket nominal `start_date`/`end_date` and actual CLOB tradability.

If only latest-state market snapshots are retained, please explicitly return `unknown` for historical intervals and identify whether venue archives, raw API payloads, event logs, or another Lumid service holds earlier versions. One current row per contract cannot establish that terms or status were stable.

## Follow-up diagnostic — Trade-feed integrity

This is a data-contract question, not a demonstrated trade-feed bug.

Please document, for these 15 contracts, the trade endpoint(s), pagination/keyset contract, execution ID and deduplication rule, late trades/corrections, token-to-YES mapping, and whether a time interval with zero returned trades can be certified as genuinely empty. Identify any retained extraction receipts or known gaps. Raw trade prices or outcomes are **not** requested in this source-assurance reply; feed semantics and receipts are enough for this item.

## Acceptance criteria and requested response format

Please provide a short explanation plus JSONL or CSV with separate `news_window` and `market_at_decision` rows. Each row should include:

`source_surface`, `deployment_or_replica`, `queried_at_utc`, `endpoint_id`, `scope_key`, `article_id` or `contract_id`, `run_ids`, `requested_from`, `requested_to`, `symbol_list_or_hash`, `pages_requested`, `pages_completed`, `pages_failed`, `completed_at`, `cursor_advanced_at`, `decision_time`, `coverage_at_decision` (`covered` / `incomplete` / `unknown`), `market_status_at_decision`, `terms_version_or_hash`, `receipt_id_or_uri`, and `unavailable_reason`.

Null is acceptable when a field was never retained. Please distinguish records observed on a stale replica from records on the live service. For any `covered` classification, the receipt must bind the **exact scope and interval** and precede the applicable decision time. Please do not infer complete coverage or a clean zero from `status=ok`, an endpoint-level row count, a current cursor, or a later retry alone.

## Issue B and security incident E — Separate operational tickets

1. **B — Read replica freshness.** Observed, as reported by a researcher: a cluster-internal read path stops near 7 June 2026 while the live findata surface returns the scoped June/July runs. Expected: identify whether this path is intentionally a fixed snapshot or a current replica; a current replica should advance or report its lag. Please identify the deployment, confirm its snapshot/replication timestamp, and repair or repoint it if it is supposed to be live. This is an operations issue; repair does not certify historical feed windows.
2. **E — Audit-log credential exposure.** Observed, as reported by a researcher and not independently queried by EventX: a credential-bearing error was persisted in the API audit log. Expected: error logging redacts credentials before persistence. Please confirm and handle this through a restricted security channel, rotate/remediate as needed, and check for similar errors. **Do not include the raw error or credential in this research response.**

If historical page/symbol/status records do not exist, a clear negative answer is useful: we will preserve those retrospective cells as `unknown` and use a new prospective capture protocol with append-only page, cursor, roster, row-version, and market-status receipts. Tweet-to-market research is a separate future source cycle and is not part of this nine-article V6 request.

## Appendix A. Exact scope (machine-readable)

This JSON is included here so the request needs no separate attachment. It contains identifiers, clocks, content hashes, and provenance hashes; it contains no article text, prices, resolutions, or credentials.

```json
{
  "request": "EventX V6 historical source evidence",
  "window_start_utc_inclusive": "2026-05-17T00:00:00Z",
  "window_end_utc_exclusive": "2026-07-22T00:00:00Z",
  "articles": [
    {
      "article_id": "102500031",
      "source_run_id": "510bc928-4d72-466b-be04-00532d6051c2",
      "source_run_status": "ok",
      "proposed_decision_time_utc": "2026-05-23T15:19:29.435984Z",
      "content_sha256": "dd9a1f96292c7708397d592107fa9f35355781a012c69fae722617cf7c1b1234"
    },
    {
      "article_id": "152232532",
      "source_run_id": "eb87b497-a8b2-4d98-a763-5269bf7e5c1c",
      "source_run_status": "ok",
      "proposed_decision_time_utc": "2026-05-26T08:15:07.502489Z",
      "content_sha256": "661974d4833f6c938f3dbb1ffc6edf177180e23fa08a7c6834d3a68687cd924d"
    },
    {
      "article_id": "166357183",
      "source_run_id": "d8bcb0d0-be28-4a0a-920c-d6087a07e5a8",
      "source_run_status": "failed",
      "proposed_decision_time_utc": "2026-05-30T13:52:00.659674Z",
      "content_sha256": "89e61eccf4f7474b82e8797d2c19f27e4287a0e081b31a882bc31659f4a65d9d"
    },
    {
      "article_id": "168034724",
      "source_run_id": "c40c9e49-4a6a-44d1-a0d9-43ca033d21ae",
      "source_run_status": "failed",
      "proposed_decision_time_utc": "2026-06-01T16:22:01.898330Z",
      "content_sha256": "a6bdfd7961e178114fbb4d0b451a089f5f8e30c1fb4dc11120dfba206b7a4183"
    },
    {
      "article_id": "189518836",
      "source_run_id": "fd734424-86f2-4d65-a67c-868d6f80730a",
      "source_run_status": "failed",
      "proposed_decision_time_utc": "2026-06-23T18:52:01.311813Z",
      "content_sha256": "8ad77a881ecef9b3d017ef4eee201ef1038b438174f55c59e5d7ded987ebe111"
    },
    {
      "article_id": "193693829",
      "source_run_id": "377266b5-b120-47f1-88fc-de86ee87462b",
      "source_run_status": "ok",
      "proposed_decision_time_utc": "2026-06-28T06:17:55.446337Z",
      "content_sha256": "87aae8a6f3e5197942b1300c9cff98092bc97ed03e9c02c00525e05e252bb9cb"
    },
    {
      "article_id": "197137081",
      "source_run_id": "592ebc42-79ad-4b33-af2d-628b5edb6167",
      "source_run_status": "failed",
      "proposed_decision_time_utc": "2026-06-30T04:52:01.676592Z",
      "content_sha256": "2ecbdc0cac2dc0dad3d5db144742d935d143ea2f717e51df4a03279428ab0469"
    },
    {
      "article_id": "201756152",
      "source_run_id": "86c568d4-f947-43e2-950b-8cf740690a9e",
      "source_run_status": "failed",
      "proposed_decision_time_utc": "2026-07-02T18:37:01.281842Z",
      "content_sha256": "c4388f470e8e1170ba0df5f17b9e57db1ed0d0d7a76b1787c2e9451168e8d207"
    },
    {
      "article_id": "211869183",
      "source_run_id": "ad764123-d034-44db-aa25-a156ab855fe2",
      "source_run_status": "ok",
      "proposed_decision_time_utc": "2026-07-09T14:59:45.841566Z",
      "content_sha256": "82cf2e0bfd19e76e2eb7d84ec068203d853c48865a966942b3f74daf916a30d9"
    }
  ],
  "contract_ids": [
    "kalshi:contract:KXWC3RDPLACE-26-MEX",
    "polymarket:contract:0x0c4cd2055d6ea89354ffddc55d6dbcef9355748112ea952fc925f3db6a5c457f",
    "polymarket:contract:0x38903ef70b7d9ee41ea22ef2aec6287e4e6c77ec8702ca741e37d5c5df090a4d",
    "polymarket:contract:0x3910cb53f972d00c049ad674c1b183b375bd56786eb4c085ea217f84defdd1ca",
    "polymarket:contract:0x58078283e2356f9b9537b42e7479d7785b83bcd6f18002de8a2526c499eda837",
    "polymarket:contract:0x5ccfe1b69a582d2985db08a8481a0d74c314b1fce9b4711ae2efb2c6467fe6aa",
    "polymarket:contract:0x75a50ed92507226816900d6da63984b4db752ad3a3f73e691514416cc5ccd980",
    "polymarket:contract:0x84edef36bded182da6a395ac6c785dba8f3e09b6c5ad041385b2042536cbef25",
    "polymarket:contract:0xa0f4c4924ea1a8b410b4ce821c2a9955fad21a1b19bdcfde90816732278b3dd5",
    "polymarket:contract:0xbb57ccf5853a85487bc3d83d04d669310d28c6c810758953b9d9b91d1aee89d2",
    "polymarket:contract:0xbe20fcfd54937c2a48a7b8521ca349e6a2c4373566328ebb950a8c35ab1be3d9",
    "polymarket:contract:0xc9c9790c8f26dd9c8cabae9dd76be37aa86a6ded7de660e1da9d19324cf618d4",
    "polymarket:contract:0xce6f2c7437b15b808a6be3ea61fc125077e35ce7cc55b66fdbf15f7ce22493ea",
    "polymarket:contract:0xdaa4866bae18be58c5a79d2aeeffd035ec78f1bb49dbd88f72993997778a990f",
    "polymarket:contract:0xe284a52d608552290b056def0a62e1914b3ebe316407504f56f6361fafc68358"
  ],
  "global_zero_export_days_not_proven_empty": [
    {
      "day_utc": "2026-05-17",
      "repeated_contract_day_cells": 134
    },
    {
      "day_utc": "2026-05-19",
      "repeated_contract_day_cells": 134
    }
  ],
  "provenance": {
    "provider_scope_sha256": "a7f29e06ce2199ad7c75b33f4f5a1812fb42970994f2ea6beddf0c82b40b5a13",
    "frozen_support_ledger_sha256": "862796eb81c168539f1af4275286d2211aa271dfb3637d733499a6d67a57330f"
  }
}
```
