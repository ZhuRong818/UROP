# V6 scoped source reply reconciliation

Date: 28 September 2026. The researcher relayed a Lumid/source analysis in conversation. These statements are useful leads, **not direct row/window receipts**. This note compares them with the frozen EventX export and nine scoped run records. It does not admit a historical exposure.

## Decision clock correction

The relayed analysis calls `available_at` the server-side first-commit timestamp. The frozen EventX export explicitly defines it in `eventx/tasks/prepare_v3_historical_primary_inputs.py` as:

```sql
GREATEST(a.published_at, a.ingest_ts, r.started_at,
         COALESCE(r.ended_at, a.ingest_ts)) AS available_at
```

The archived `news.articles` schema lists `ingest_ts` and `source_run_id`, but **no `available_at` column**. In all nine scoped rows, derived `available_at` equals `run_ended_at`. For the five failed runs, this is the abandoned-run cleanup time and is 1–2 hours after `ingest_ts`. Thus the EventX value is a conservative no-earlier-than clock, not proof of the first row commit or first client read. Preserve it for existing frozen analyses; a revised clock needs a separate version and row-level commit/read-visibility evidence. Do not silently replace it with `published_at` or `ingest_ts`.

The row-lineage API suggested in the relayed response may help establish the first committed row and version. Its exact semantics and whether `ingest_ts` marks visible commit remain to be confirmed from an authoritative Lumid record. The prior article-content stability assurance remains provisional.

## Exact five failed runs for per-scope cursor reconciliation

All five are `finnhub:company-news`, `status=failed`, `error_category=abandoned_run_cleanup` in the scoped Lumid lineage GETs. The failed run's retained article is real, but it does not prove a complete feed window. The `to` argument is the run's request bound, **not** a certified start/end interval or per-symbol coverage proof.

| Article | Symbol | Failed `run_id` | `args.to` | Article `ingest_ts` | Derived `available_at` |
| --- | --- | --- | --- | --- | --- |
| 166357183 | NVDA | `d8bcb0d0-be28-4a0a-920c-d6087a07e5a8` | 2026-05-30 | 2026-05-30 12:03:26Z | 2026-05-30 13:52:00Z |
| 168034724 | MSTR | `c40c9e49-4a6a-44d1-a0d9-43ca033d21ae` | 2026-06-01 | 2026-06-01 14:34:10Z | 2026-06-01 16:22:01Z |
| 189518836 | MSTR | `fd734424-86f2-4d65-a67c-868d6f80730a` | 2026-06-24 | 2026-06-23 17:03:39Z | 2026-06-23 18:52:01Z |
| 197137081 | MSTR | `592ebc42-79ad-4b33-af2d-628b5edb6167` | 2026-06-30 | 2026-06-30 03:04:53Z | 2026-06-30 04:52:01Z |
| 201756152 | MSTR | `86c568d4-f947-43e2-950b-8cf740690a9e` | 2026-07-03 | 2026-07-02 16:48:29Z | 2026-07-02 18:37:01Z |

These are the five endpoint/request-bound pairs the provider asked for. None is the 19 May OOM run. The four other scoped runs are `ok`, but run success alone does not certify all overlapping feed windows.

## Cursor check to request

The live catalog schema for `provenance.scrape_cursor` exposes `endpoint_id`, `scope_key`, `last_run_id`, `last_data_date`, `last_run_at`, `next_action`, and `retry_count`. A prereceipted read-only query for `finnhub:company-news` cursor keys containing `NVDA` or `MSTR` returned HTTP 200 and **zero rows**. This does not prove those symbols were absent: `scope_key` may use a different encoding or aggregation. Its result and request receipt are preserved separately in `data/v6/scoped_cursor_scope_probe_20260928/`.

For **each** failed run above, ask Lumid for: (1) the exact `scope_key`/symbol mapping and requested date interval, (2) the first successor run that completed that scope/window, with status, start/end, committed/failed counts and cursor transition, (3) the cursor state **as of each proposed decision time**, including any completed zero, and (4) a list of still unknown intervals. A current cursor advanced past a date does not alone prove the feed was complete at an earlier prediction time; a later retry cannot be backdated. For `partial` runs, require per-scope success rather than aggregate inserted rows. A zero export requires a clean run and documented cursor advance for the declared scope/window.

An executable check needs Lumid's `scope_key` mapping and historical cursor transitions. Use the supplied five IDs and the full nine-article attachment `data/v6/context_development_review_20260927/provider_scope.json` as inputs. Until these records arrive, output `unknown` for failed windows; do not implement a fabricated `covered` result from endpoint-level run counts or a symbol substring join.

## Market status and aggregate-count qualifications

The relayed explanation says Kalshi `open_time`/`close_time` bracket trading while settlement is separate; Polymarket `start_date`/`end_date` are nominal and `active`/`acceptingOrders`/`closed`/CLOB state govern tradability. The warehouse holds refreshed snapshots without a scoped historical status/change log, so these statements do not certify the exact 15 markets' active intervals, suspensions, rule text or YES/NO mapping at decision time. Keep those cells unknown until venue or provider records are supplied. Kalshi's public API exposes distinct open, close and settlement fields; this supports the distinction, not the scoped historical status.

The relayed aggregate table says 3,073 runs but its four status rows sum to **2,982**, leaving **91 unaccounted for**. The failure-cause text is also internally garbled. Do not use its 14.53M/1.96M row or 154 committed-zero figures as V6 certificates. Request a corrected aggregate if needed, but prioritize the nine scoped runs and per-scope windows.

**Status:** no new full-window source certificate, market-status certificate, semantic link admission, or predictive contract-day admission. The V6 count remains 0/8,844.
