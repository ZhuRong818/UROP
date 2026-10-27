# Lumid Studio / FinData bug report

**Re-audit date:** 2026-09-01  
**Original audit:** 2026-08-29 to 2026-08-31  
**Reporter context:** EventX research project, read-only API/catalog/warehouse use  
**Affected services:** `https://lum.id/studio` and `https://lum.id/findata`  
**Security and research integrity:** No credentials, protected EventX outcomes,
labels, prices, predictions, or October holdout data are included or were inspected.

## Executive summary

Lumid has fixed most defects reported in the first audit. All 178 catalog profiles and
schemas now complete, the published `news.articles` schema matches the 22 queryable
columns, `/retrieve` is documented and operational, JSONL/CSV materialisation works,
Parquet is explicitly excluded, and row-lineage natural-key requirements are now
described. The August 30–31 `/retrieve` outage is no longer reproducible.

Five confirmed issues remain or were newly found:

1. `/news/latest` silently coerces invalid limits and caps all requests above 200.
2. The OpenAPI contract provides no response schema and documents only HTTP 200 for
   all 172 operations, despite real 400 and 500 responses.
3. Kalshi candle retrieval returns HTTP 500 across valid markets, intervals, bounded
   queries, and unknown identifiers; a Polymarket control succeeds.
4. Two warehouse news records have future publication timestamps in 2028 and 2030,
   which also contaminate `/news/stats` freshness output.
5. `/catalog/lineage/runs` returns zero runs while `provenance.runs` contains 312,096
   rows, including 58,724 from the preceding 30 days.

These findings mean Lumid is usable for bounded, authenticated research exports, but
clients must still enforce their own pagination/completeness, timestamp-validity, and
provenance checks. The interactive Studio UI itself was not click-tested because the
browser-control service was unavailable; only its HTTP shell and API surfaces were
verified.

## Previous-issue status

| ID | Original issue | 2026-09-01 status | Re-audit evidence |
|---|---|---|---|
| LUMID-001 | `news.articles` catalog schema omitted six columns | **Fixed** | Catalog and `information_schema` now contain the same 22 columns |
| LUMID-002 | Large-table profiles timed out | **Fixed** | 178/178 profiles completed; zero timeouts |
| LUMID-003 | Two existing table schema routes returned 404 | **Fixed** | 178/178 schema routes completed; zero schema 404s |
| LUMID-004 | `/retrieve` absent from OpenAPI | **Fixed for discovery** | `/retrieve` is present with SQL/output documentation; response contract remains incomplete under LUMID-011 |
| LUMID-005 | Parquet capability was ambiguous | **Fixed** | OpenAPI enumerates `jsonl`, `csv`, and `raw`; Parquet returns a clear 400 stating it is not implemented |
| LUMID-006 | Unbounded FTS ended as an opaque client timeout | **Fixed for error handling** | Server returns actionable HTTP 400 at 30 seconds; bounded FTS completes in about 0.1 seconds |
| LUMID-007 | Row-lineage key requirements undocumented | **Partly fixed** | Natural key `(url, published_at)` is now described and valid row lineage returns 200; run listing is still inconsistent under LUMID-014 |
| LUMID-008 | Anonymous catalog metadata exposure | **Still observed / policy unclear** | Catalog remains readable without authentication; document or restrict intentionally |
| LUMID-009 | `/health` OK while `/retrieve` returned 500 | **Recovered; not reproducible now** | Two trivial retrieves succeeded and a 1,500-row ordered export completed; readiness behavior during a future outage is unverified |

## Active confirmed issues

### LUMID-010 — `/news/latest` silently clamps and coerces `limit`

**Severity:** High for completeness-sensitive clients  
**Status:** Confirmed on 2026-09-01

The live OpenAPI declares `limit` only as an unconstrained integer. Actual results are:

| Requested limit | Returned rows | HTTP status |
|---:|---:|---:|
| `-1` | 1 | 200 |
| `0` | 1 | 200 |
| `1` | 1 | 200 |
| `200` | 200 | 200 |
| `201` | 200 | 200 |
| `5000` | 200 | 200 |

There is no cursor or upper-time boundary on the route, so a caller cannot distinguish
an exhaustive 200-row result from a censored one.

**Impact:** A caller asking for more than 200 rows can silently lose older articles;
invalid zero/negative limits appear successful. This can convert missing data into
false zero-news periods.

**Requested fix:** Publish `minimum=1` and `maximum=200`, return 422 for invalid values,
add a cursor or stable `(published_at,id)` keyset, and include `has_more`/`next_cursor`
or an explicit truncation flag.

### LUMID-011 — OpenAPI response and error contracts are skeletal

**Severity:** Medium  
**Status:** Confirmed on 2026-09-01

The current contract contains 170 paths and 172 operations. All 172 operations list
only a `200` response, and none provides a response content schema. Actual probes
returned structured 400 and 500 responses. Integer parameters such as news `limit`
also omit bounds.

**Impact:** Generated clients cannot validate responses or distinguish validation,
query-limit, not-found, and server failures. Real behavior can drift from documentation
without contract tests detecting it.

**Requested fix:** Add typed success schemas and shared 400/401/404/422/429/500 error
schemas, parameter constraints, examples, and a CI contract test against live handlers.

### LUMID-012 — Kalshi candles return HTTP 500

**Severity:** High for prediction-market use  
**Status:** Confirmed and venue-specific on 2026-09-01

Every tested Kalshi candle request returned `500 {"detail":"internal server error"}`:

- two valid, open, non-EventX markets;
- default, `1d`, and `5m` intervals;
- an explicitly bounded August query; and
- an unknown ticker, which should produce a client/not-found response rather than 500.

The same candle route for a non-EventX Polymarket control returned 10 valid rows with
HTTP 200.

**Requested fix:** Repair the Kalshi query/identifier path, return 404 or an empty result
for unknown markets according to a documented contract, and add cross-venue regression
tests for default, bounded, empty, and invalid requests.

### LUMID-013 — Future-dated news contaminates freshness statistics

**Severity:** High for point-in-time research  
**Status:** Confirmed on 2026-09-01

An aggregate warehouse query found two records whose `published_at` is more than one
day after current time:

| Source | Source endpoint | Ingested | Published timestamp |
|---|---|---|---|
| Finnhub | `html_index:stub_from_url_date` | 2026-06-14 | 2028-04-24 12:00 UTC |
| FMP | `html_index:stub_from_url_date` | 2026-06-14 | 2030-04-07 12:00 UTC |

`/news/stats` consequently reports `2030-04-07T12:00:00Z` as the latest timestamp for
the null category.

**Impact:** Future records can distort freshness, time-window counts, backtests, and
point-in-time features if a client trusts `published_at` without validation.

**Requested fix:** Validate URL-derived dates against ingestion/current time, quarantine
implausible values, exclude them from freshness statistics, and expose a data-quality
flag rather than silently rewriting provenance.

### LUMID-014 — Lineage run listing contradicts the provenance table

**Severity:** Medium/High for reproducibility  
**Status:** Confirmed on 2026-09-01

`GET /catalog/lineage/runs` returns:

```json
{"count":0,"runs":[]}
```

In the same authenticated session, a read-only aggregate over `provenance.runs`
returned 312,096 total rows, with 58,724 in the last 30 days and a latest timestamp of
`2026-09-01T09:15:11.675001Z`. Row-level lineage also succeeds for a valid natural key.

**Impact:** Users cannot enumerate runs needed to reproduce an export even though the
underlying lineage records exist.

**Requested fix:** Reconcile endpoint filters/permissions with `provenance.runs`, define
the default time window and pagination, and ensure `count` reflects the listed query.

## Operational observations, not currently classified as defects

- `/kols/archive/stats` succeeded but took about 20.6 seconds; prediction-market search
  took about 6.3 seconds. These merit latency monitoring but no latency SLO was found.
- Empty results for the tested Kalshi open-interest and Polymarket orderbook calls are
  valid data responses, not endpoint failures.
- `/status` returns HTML by design according to OpenAPI; it is not a JSON endpoint bug.
- Unbounded whole-table FTS remains unsuitable for interactive use, but it now returns
  a clear statement-timeout error. Bounded FTS is usable.
- Catalog metadata remains anonymously visible. This is a policy question unless Lumid
  intends the catalog to require authentication.

## Evidence

All probes were read-only and used non-frozen prediction-market samples. No EventX
market prices, labels, outcomes, or holdout data were read.

- Re-audit narrative: `LUMID_REAUDIT_2026-09-01.md`
- Warehouse/catalog report:
  `data/v2_3_1/lumid_studio_audit_20260901/report.json`
- REST report:
  `data/v2_3_1/lumid_studio_audit_20260901/rest_report.json`
- Targeted follow-up:
  `data/v2_3_1/lumid_studio_audit_20260901/followup_report.json`
- Warehouse report SHA-256:
  `4e8c7931deed1deaefdf2037a7d688362547fbb16cdae7af47d6b90bd499ab6d`
- REST report SHA-256:
  `ca918cce6c9600ce9f8a15533b8df793a8ad889d78e74c20a7d9a8f966e7e1a4`
- Follow-up report SHA-256:
  `2be8bba57e05173aa8d15a0ce11397d855876fe39dfeeb7f190a7116d2b6a7a8`

## EventX handling pending Lumid fixes

- Use authenticated, bounded `/retrieve` queries with exact SQL, receipts, row counts,
  hashes, and local integrity validation.
- Treat every `/news/latest` response at 200 rows as censored; never advance a
  completeness checkpoint from it.
- Reject or quarantine future-dated and implausibly backdated articles before any
  point-in-time feature construction.
- Do not use the Kalshi candle route as a required EventX input; executed trades remain
  the frozen primary price source.
- Preserve row-level lineage and source-run fields locally because the run-list endpoint
  is not reliable.
