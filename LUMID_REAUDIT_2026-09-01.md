# Lumid Studio / FinData comprehensive re-audit — 2026-09-01

## Verdict

Lumid is now usable for EventX's bounded warehouse exports and most catalog functions.
The general `/retrieve` outage, incomplete news schema, profile timeouts, schema 404s,
undocumented retrieval route, and Parquet ambiguity observed in August are fixed or no
longer reproducible.

The re-audit found five current defects: silent `/news/latest` truncation/coercion,
skeletal OpenAPI response contracts, a broken Kalshi candle route, future-dated news,
and an empty lineage-run listing inconsistent with the underlying provenance table.
None justifies changing the frozen EventX v2.3 scientific protocol. They require local
data-quality controls and a source bug report.

## Scope and integrity boundary

The audit covered:

- the Studio HTTP shell and live OpenAPI contract;
- all 13 catalog schemas and all 178 catalog tables;
- all 178 table profiles and JSON schemas;
- authenticated read-only `/retrieve` in JSONL and CSV;
- invalid-format/table and query-timeout behavior;
- row and run lineage;
- MCP tool discovery;
- representative news, KOL, market, macro, quote, fundamental, health, freshness, and
  prediction-market REST routes; and
- targeted repetitions for news limits, Kalshi candles, future news, and provenance.

The prediction-market samples were verified outside the frozen 14-market EventX
cohort. No protected market prices, labels, outcomes, predictions, or October holdout
data were read. The browser-control service was unavailable, so interactive Studio UI
clicks and authenticated page workflows remain unverified.

## Test results

| Area | Result | Assessment |
|---|---:|---|
| Catalog discovery | 13 schemas, 178 tables | Pass |
| Table profiles | 178/178 completed, zero timeouts | Pass; prior issue fixed |
| JSON schemas | 178/178 completed, zero 404s | Pass; prior issue fixed |
| `news.articles` schema | 22 catalog columns = 22 actual columns | Pass; prior issue fixed |
| `/retrieve` basic/CTE/empty | HTTP 200 | Pass |
| 1,500-row ordered retrieve | 1,500/1,500 rows in 26.99 s | Pass, near statement limit |
| Bounded news FTS | HTTP 200 in about 0.1 s | Pass |
| Unbounded news FTS | Actionable HTTP 400 at 30.02 s | Safe failure; use bounds |
| Output formats | JSONL/CSV work; Parquet clearly rejected | Contract clarified |
| Row lineage | Valid natural key returns 200 | Pass |
| Lineage run listing | 0 listed vs 312,096 stored runs | Fail |
| Representative REST | 30/31 HTTP 2xx in broad run | Mostly pass |
| Kalshi candles | HTTP 500 across all nine targeted variations | Fail |
| Polymarket candle control | HTTP 200, 10 rows | Pass |
| `/news/latest` limits | invalid limits coerce; >200 clamps to 200 | Fail |
| News timestamp quality | two future records; latest 2030 | Fail |
| OpenAPI response contracts | 172/172 only document 200; 0 typed response bodies | Fail |
| Studio interactive UI | Not tested | Browser service unavailable |

## What was fixed

- Catalog profile completion improved from 157/178 to 178/178.
- Two former schema 404s now return successfully.
- `news.articles` now publishes all six previously missing provenance/search fields.
- `/retrieve` is present in OpenAPI and accepts documented JSONL/CSV/raw formats.
- Unsupported Parquet receives a clear validation response and is excluded from the
  advertised enum.
- Row-lineage natural-key semantics and missing-key errors are clearer.
- `/retrieve` recovered from the August 30–31 service outage.
- Statement-limit failures now return an actionable HTTP 400 telling callers to bound
  the scan instead of appearing as a generic client timeout.

## What remains unusable or unsafe

### Directly unusable

- Kalshi candles are currently unusable because every tested request returns 500.
- `/catalog/lineage/runs` is unusable for enumerating real warehouse runs because it
  returns an empty list despite a populated provenance table.

### Usable only with client safeguards

- `/news/latest` is suitable for low-volume monitoring only when any 200-row response
  is treated as censored. It cannot prove historical completeness by itself.
- News timestamps require plausibility checks against ingestion and current time.
- `/retrieve` should use bounded predicates and preserve materialisation receipts.
- OpenAPI is useful for route discovery but not as a complete response/error contract.

### Valid but limited observations

- Empty orderbook/open-interest samples are not errors.
- `/status` is intentionally HTML.
- KOL archive statistics and market search can be slow, but both returned successfully.
- UI-level availability cannot be claimed from this run.

## Effect on EventX

The principal EventX research route is not blocked by these new bugs:

- executed trades, not candles, are the frozen primary price source;
- historical `/retrieve` is working and the separate feasibility runner completed
  both venue activity exports;
- the project already treats 200-row `/news/latest` responses as censored and uses
  warehouse reconciliation for closure; and
- local timestamp validation/quarantine prevents future-dated records from becoming
  point-in-time features.

The active research blocker remains the September 28 exact-window data gate, with
sparse/concentrated news support as the main scientific risk. The new source defects
should be reported to Lumid but do not authorize post-hoc changes to the cohort,
features, dates, or holdout.

## Reproducible artifacts

- `eventx/tasks/audit_lumid_studio_warehouse.py`
- `eventx/tasks/audit_lumid_studio_rest.py`
- `eventx/tasks/audit_lumid_studio_followup.py`
- `data/v2_3_1/lumid_studio_audit_20260901/report.json`
- `data/v2_3_1/lumid_studio_audit_20260901/rest_report.json`
- `data/v2_3_1/lumid_studio_audit_20260901/followup_report.json`
- `LUMID_STUDIO_BUG_REPORT.md`
- `LUMID_RETRIEVE_BUG_REPORT.md`

The three runtime reports have SHA-256 values recorded in the current bug report.
