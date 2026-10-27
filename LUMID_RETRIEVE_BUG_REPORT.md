# Lumid FinData incident report: `/retrieve` unavailable while `/health` was OK

**Reported:** 2026-08-31 14:02 SGT (2026-08-31T06:02:02Z)  
**First observed:** 2026-08-30  
**Current status:** **Recovered; not reproducible on 2026-09-01**  
**Historical severity:** High — research data retrieval was blocked  
**Affected service:** `https://lum.id/findata`  
**Affected endpoint:** authenticated `POST /retrieve`  
**Security:** No credentials, protected outcomes, labels, or holdout data are included.

## Current resolution evidence

The retrieval dependency recovered without an EventX client-side change:

- `SELECT 1::integer AS ok` materialised and downloaded successfully in two independent
  2026-09-01 audit runs.
- A sorted 1,500-row `news.articles` export returned HTTP 200 and downloaded all 1,500
  rows in 26.99 seconds.
- A bounded full-text query completed in about 0.1 seconds.
- The previously blocked historical exporter completed 18,635,674 Kalshi activity rows
  and 901,028 Polymarket activity rows with passing integrity manifests.
- An intentionally expensive unbounded FTS query now returns an actionable HTTP 400 at
  the 30-second server statement limit instead of an opaque client-side failure.

The incident is therefore closed operationally for EventX. One acceptance criterion
remains unverified: `/health` still exposes only service liveness, so its behavior during
a future retrieval dependency outage cannot be proven from a healthy-period test.

## Historical incident summary

On August 30–31, Lumid's public health endpoint reported the data service as healthy,
while authenticated SQL retrieval returned HTTP 500 for every tested request, including
the trivial query `SELECT 1 AS ok`. The failure was therefore not specific to the
EventX aggregation query.

EventX's continuous client recorded repeated failures in its retry ledger. It did not
interpret any failed request as an empty interval, and it resumed from checkpoints when
the source recovered.

## Historical reproduction

At `2026-08-31T06:02:02.977650Z`:

```http
GET /findata/health
HTTP/1.1 200 OK

{"status":"ok","service":"lumid-data-service"}
```

```http
POST /findata/retrieve
Authorization: Bearer <redacted>
Content-Type: application/json

{"sql":"SELECT 1 AS ok","output_format":"jsonl"}
```

Actual historical response:

```http
HTTP/1.1 500 Internal Server Error

{"detail":"internal server error"}
```

## Historical impact

- Kalshi and Polymarket activity/metadata retrieval paused.
- The label-blind historical feasibility gates could not be evaluated while the source
  dependency was down.
- `/health` could not distinguish query-specific failure from database/materialisation
  unavailability.
- No scientific result was corrupted because failed reads were preserved as failures,
  never converted into zero rows.

## Requested preventive fixes

1. Add a readiness endpoint that verifies a trivial database read and materialisation,
   or mark readiness degraded while the retrieval dependency is unavailable.
2. Document and return stable, typed errors for database unavailability, statement
   timeout, validation failure, and materialisation failure.
3. Keep a traceable request/run ID on every 5xx response.
4. Add retrieval dependency monitoring so an outage is detected before long-running
   clients launch work.

## Acceptance status

| Criterion | 2026-09-01 result |
|---|---|
| Trivial authenticated retrieve succeeds repeatedly | **Pass** |
| Bounded EventX retrieval succeeds or returns a specific limit error | **Pass** |
| Historical activity exporter can resume from checkpoints | **Pass** |
| Readiness degrades when retrieval is unavailable | **Not testable while healthy** |
| 5xx responses use a documented, traceable error schema | **Not established; OpenAPI remains incomplete** |

## Evidence

- Historical retry ledger:
  `data/v3_historical/feasibility/raw/kalshi_activity/retry_ledger.json`
- Completed Kalshi activity manifest:
  `data/v3_historical/feasibility/raw/kalshi_activity/manifest.json`
- Completed Polymarket activity manifest:
  `data/v3_historical/feasibility/raw/polymarket_activity/manifest.json`
- 2026-09-01 follow-up report:
  `data/v2_3_1/lumid_studio_audit_20260901/followup_report.json`
- Broader current issue report: `LUMID_STUDIO_BUG_REPORT.md`

This file preserves the outage history; it should no longer be cited as an active
research blocker.
