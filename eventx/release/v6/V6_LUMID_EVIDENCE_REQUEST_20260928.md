# V6 scoped Lumid evidence request — ready to send, not sent

Date: 28 September 2026. Scope: opened development `[2026-05-17, 2026-07-22)` UTC; nine article IDs/run IDs and 15 contract IDs are in `data/v6/context_development_review_20260927/provider_scope.json`. This version supersedes the 27 September draft for any later message. It asks for operational receipts only; no prices, resolutions, credentials or protected V4 records.

## 1. Align the run ledger first

Our configured `https://lum.id/findata` returned all three disputed June/July `finnhub:company-news` runs both through `GET /catalog/lineage/run/{run_id}` and an exact-UUID `POST /retrieve` query against `provenance.runs`. The exact query and responses are in `data/v6/lineage_sql_surface_20260928/`. The IDs are `fd734424-86f2-4d65-a67c-868d6f80730a`, `592ebc42-79ad-4b33-af2d-628b5edb6167` and `86c568d4-f947-43e2-950b-8cf740690a9e`; each returned a failed run after 8 June. Your earlier ledger query found none.

Please rerun the attached exact query and identify the API base URL/deployment, authenticated role or tenant, query time, and every filter or retention boundary used for the earlier result. Return the three rows or the precise reason the surfaces differ. We do not infer a separate `/ingest` path from a missing-row result until this is aligned.

The same EventX API returned one current `provenance.scrape_cursor` row for `finnhub:company-news`: `scope_key=''`, `last_run_id=fd8e77f3-7814-46b5-9a5a-54da94a26545`, `last_data_date=2026-09-28T12:37:40Z`, `last_run_at=2026-09-28T13:10:24.970190Z`. Please confirm the endpoint-wide scope/symbol-universe mapping and whether an append-only historical cursor or per-window completion ledger exists. Current overwritten cursor state is not a historical receipt.

## 2. Delivery and feed-window proof at the decision time

EventX's exported `available_at` is derived as the maximum of publication, row ingest, run start and run end; it is not a stored first-commit field. For the five failed runs below it equals abandoned-run cleanup time. Please confirm what `news.articles.ingest_ts` timestamps (row commit versus earlier processing), whether an earlier read-visibility/first-delivery receipt exists for the exact article bytes, and whether the conservative EventX `available_at` can ever precede visibility. A later cleanup timestamp is acceptable as a conservative decision clock, but should not be described as first delivery.

For each scoped article/feed interval, please provide the requested `from`/`to`, scope/symbol universe, pages attempted/committed/failed, row counts, exact successor or retry run IDs, completion times, and historical cursor transition. Mark whether its declared feed window was complete **before the article's proposed decision time**. If a completed query returned zero rows, provide the clean run and cursor/page receipt for that exact interval; if no such receipt exists, report `unknown` rather than zero news. The five failed runs and decision clocks are:

| Article | Failed run | EventX decision clock UTC | First later completed/partial endpoint run found within seven days |
| --- | --- | --- | --- |
| 166357183 | `d8bcb0d0-be28-4a0a-920c-d6087a07e5a8` | 30 May 13:52:00.659674 | `78ae76ec-0a9f-4231-86de-635bd3f3635c` ok, ended 30 May 20:39:52, `to=31 May` |
| 168034724 | `c40c9e49-4a6a-44d1-a0d9-43ca033d21ae` | 1 June 16:22:01.898330 | `05f950df-a4d5-4fce-96d2-0e4dca4fa68a` partial, ended 5 June 08:10:00, `to=5 June` |
| 189518836 | `fd734424-86f2-4d65-a67c-868d6f80730a` | 23 June 18:52:01.311813 | None found within seven days |
| 197137081 | `592ebc42-79ad-4b33-af2d-628b5edb6167` | 30 June 04:52:01.676592 | `c4c5b4aa-c148-465a-ae43-a6f0e5d2a797` ok, ended 6 July 18:02:33, `to=7 July` |
| 201756152 | `86c568d4-f947-43e2-950b-8cf740690a9e` | 2 July 18:37:01.281842 | `c4c5b4aa-c148-465a-ae43-a6f0e5d2a797` ok, ended 6 July 18:02:33, `to=7 July` |

These later endpoint summaries do not prove that the earlier requested window or any symbol was complete. The other four scoped article runs are `ok`, but please state the complete declared feed/window contract for those too; `ok` alone gives no per-window certificate. The current 268 zero-export contract-days in the support ledger remain unverified empty until their exact completed windows are identified.

## 3. Market activation and version history

For each of the 15 contracts in the attachment, please provide the trading-active interval at each of the nine article decision clocks and any suspension, reopening or early closure. For Kalshi, distinguish `open_time`/`close_time` from settlement. For Polymarket, treat `start_date`/`end_date` as nominal unless an `active`, `acceptingOrders`, `closed` or CLOB book-status receipt establishes tradability. Identify any changes to question, YES/NO mapping, rules or resolution text and their first valid/visible times, or explicitly report that a historical status/version trail is unavailable.

## Requested return format

One machine-readable row per article interval and contract-status interval, with `source_surface`, `scope_key`, `requested_from`, `requested_to`, `run_ids`, `completed_at`, `cursor_advanced_at`, `page_counts`, `row_counts`, `decision_time`, `coverage_at_decision` (`covered`, `incomplete`, `unknown`), `market_status_at_decision`, and the receipt ID/URI. Unknown fields may stay null. A response with only the present cursor or later retries will remain an `unknown` historical certificate.

Evidence already held: `data/v6/scoped_source_evidence_20260927/`, `data/v6/lineage_surface_conflict_20260928/`, `data/v6/lineage_sql_surface_20260928/`, and `data/v6/cursor_successor_probe_20260928/`. No data source, article–contract link or predictive day is admitted by this request.
