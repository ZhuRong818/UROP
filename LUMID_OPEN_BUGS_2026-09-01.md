# Lumid Studio / FinData — open bugs only

**Verified:** 2026-09-01  
**Scope:** Only defects still reproducible in the latest read-only re-audit  
**Affected services:** `https://lum.id/studio` and `https://lum.id/findata`  
**Integrity:** No credentials, EventX labels, outcomes, protected market prices,
predictions, or October holdout data were accessed or included.

## Open-issue summary

| ID | Severity | Affected feature | Current behavior |
|---|---|---|---|
| LUMID-010 | High | `/news/latest` | Invalid limits are coerced and limits above 200 are silently capped |
| LUMID-011 | Medium | OpenAPI | All 172 operations document only HTTP 200 and no typed response body |
| LUMID-012 | High | Kalshi candles | Valid, bounded, interval and unknown-market requests return HTTP 500 |
| LUMID-013 | High | News timestamps/statistics | Future-dated 2028/2030 records contaminate freshness output |
| LUMID-014 | Medium/High | Lineage run listing | Endpoint reports zero runs while the provenance table contains 312,096 |

## LUMID-010 — `/news/latest` silently clamps and coerces `limit`

**Observed results:**

| Requested limit | Returned rows | HTTP status |
|---:|---:|---:|
| `-1` | 1 | 200 |
| `0` | 1 | 200 |
| `1` | 1 | 200 |
| `200` | 200 | 200 |
| `201` | 200 | 200 |
| `5000` | 200 | 200 |

The OpenAPI schema describes `limit` only as an integer. The endpoint has no cursor,
upper-time boundary, `has_more`, or truncation indicator.

**Impact:** A client requesting more than 200 rows can silently lose older articles
and mistake an incomplete interval for complete or zero-news coverage.

**Requested fix:** Declare `minimum=1` and `maximum=200`; reject invalid values with
422; add stable `(published_at,id)` pagination; and return `has_more`, `next_cursor`,
or an explicit truncation flag.

**Acceptance test:** Requests outside `[1,200]` fail validation, while a response that
has additional records exposes a usable continuation cursor.

## LUMID-011 — OpenAPI lacks real response and error contracts

The current OpenAPI contains 170 paths and 172 operations. All 172 operations list
only an HTTP 200 response, and none defines a response content schema. Live endpoints
nevertheless return structured 400 and 500 responses. Integer parameter constraints
are also incomplete.

**Impact:** Generated clients cannot validate successful payloads or reliably
distinguish validation, not-found, timeout, rate-limit, and server failures.

**Requested fix:** Add typed success schemas, shared
400/401/404/422/429/500 error schemas, parameter bounds, examples, and automated
contract tests against the handlers.

**Acceptance test:** Every public operation exposes its real success body and supported
error statuses, and CI detects a response that violates the contract.

## LUMID-012 — Kalshi candle endpoint returns HTTP 500

Every targeted Kalshi candle probe returned:

```json
{"detail":"internal server error"}
```

The failure reproduced across:

- two valid, open, non-EventX Kalshi markets;
- default, `1d`, and `5m` intervals;
- an explicitly bounded August interval; and
- an unknown ticker.

The equivalent non-EventX Polymarket control returned HTTP 200 and 10 candle rows.

**Impact:** Kalshi historical candle data is unavailable through this route, and an
invalid market is incorrectly surfaced as a server failure rather than a client or
not-found response.

**Requested fix:** Repair the Kalshi query/identifier path, define empty/not-found
semantics, and add cross-venue regression tests for default, bounded, empty, and
invalid requests.

**Acceptance test:** Valid Kalshi markets return candle rows or a documented empty
result; unknown markets return the documented 4xx response; neither returns 500.

## LUMID-013 — Future-dated news contaminates freshness statistics

Two warehouse records are dated years after their June 2026 ingestion:

| Source | Source endpoint | `ingest_ts` | `published_at` |
|---|---|---|---|
| Finnhub | `html_index:stub_from_url_date` | 2026-06-14 | 2028-04-24 12:00 UTC |
| FMP | `html_index:stub_from_url_date` | 2026-06-14 | 2030-04-07 12:00 UTC |

`GET /news/stats` consequently reports `2030-04-07T12:00:00Z` as the latest timestamp
for the null category.

**Impact:** Implausible timestamps can distort freshness monitoring, interval counts,
historical backtests, and point-in-time feature construction.

**Requested fix:** Validate URL-derived dates against ingestion/current time,
quarantine implausible records, exclude them from freshness aggregates, and expose a
data-quality flag while preserving the raw source value.

**Acceptance test:** No future-dated record contributes to `/news/stats`; affected rows
are identifiable through a validation/quarantine field.

## LUMID-014 — Lineage run listing contradicts stored provenance

The catalog endpoint returns:

```json
{"count":0,"runs":[]}
```

During the same authenticated audit, a read-only aggregate over `provenance.runs`
returned:

- 312,096 total runs;
- 58,724 runs in the preceding 30 days; and
- latest run timestamp `2026-09-01T09:15:11.675001Z`.

Row-level lineage succeeds when supplied with the documented natural key, so the
problem is specific to run enumeration rather than a completely absent lineage store.

**Impact:** Researchers cannot enumerate the ingestion/materialisation runs needed to
reproduce data lineage even though those records exist.

**Requested fix:** Reconcile endpoint filtering and permissions with
`provenance.runs`, document the default time window and pagination, and make `count`
match the listing query.

**Acceptance test:** The endpoint returns recent runs, a consistent non-zero count,
stable pagination, and run identifiers resolvable through the run-detail route.

## Evidence

- Warehouse/catalog audit:
  `data/v2_3_1/lumid_studio_audit_20260901/report.json`
- REST audit:
  `data/v2_3_1/lumid_studio_audit_20260901/rest_report.json`
- Targeted follow-up:
  `data/v2_3_1/lumid_studio_audit_20260901/followup_report.json`
- Machine-readable status:
  `data/v2_3_1/lumid_studio_audit_20260901/issue_comparison.json`

SHA-256:

- Warehouse: `4e8c7931deed1deaefdf2037a7d688362547fbb16cdae7af47d6b90bd499ab6d`
- REST: `ca918cce6c9600ce9f8a15533b8df793a8ad889d78e74c20a7d9a8f966e7e1a4`
- Follow-up: `2be8bba57e05173aa8d15a0ce11397d855876fe39dfeeb7f190a7116d2b6a7a8`

This report intentionally excludes repaired, non-reproducible, policy-only, and
performance-observation items. Historical issue status remains available in
`LUMID_STUDIO_BUG_REPORT.md`.
