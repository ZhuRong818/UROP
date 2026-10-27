# EventX v2.3.1 Lumid warehouse reconciliation evidence

**Evidence date:** 2026-08-28  
**Protocol:** `eventx-v2.3-news-availability-clarifications-20260817`  
**Status:** label-blind interim snapshot passed; final September 28 closure pending

This tracked receipt summarises the larger runtime artifacts under the gitignored
`data/` tree. It changes no frozen scientific decision and contains no labels,
prevalence, model outputs or holdout outcomes.

## Warehouse snapshot

- Lumid surface: read-only `POST https://lum.id/findata/retrieve`
- Warehouse table: `news.articles`
- Lumid retrieval run: `e457a37f-0ea2-4e77-8d9e-46ce508927f7`
- Window: `[2026-08-08T00:00:00Z, 2026-08-28T00:00:00Z)` by `published_at`
- Requested: `2026-08-28T05:22:31.528758Z`
- Completed: `2026-08-28T05:23:09.589470Z`
- Receipt row count and locally parsed rows: 28,307 each
- Unique warehouse IDs: 28,307
- Unique normalised URLs: 27,957
- Duplicate-URL rows: 350
- Invalid JSON, missing-required and out-of-window rows: 0 each
- Distinct source-run IDs: 962
- Raw JSONL size: 48,060,537 bytes
- Raw JSONL SHA-256:
  `6181c5ab8fdff4efb1b077ca54f881db0d6e616e1a69ca836abdad528059a685`
- SQL SHA-256:
  `ffb00b3db4f7e056ecf92eecc749cfd60746a31733987a3714e6372c352df989`
- Retrieval-receipt SHA-256:
  `1b640ded9dce6ad2f5d57c99fefb3eaf3db228a12f63296cc58bbe57d2c8997f`
- Runtime export-manifest SHA-256:
  `6f6d7eb037d40f2bc5f1136cb67dca02476de4ab83445af4d386a3dd8a7ee18e`

Source counts were 24,538 Finnhub, 2,357 FMP and 1,412 Massive records. The
export retained `id`, `published_at`, `ingest_ts`, text, URL, symbol fields, source,
source endpoint, source-run ID and original vendor JSON.

## Cross-path point-in-time reconciliation

The warehouse was reconciled against the legacy prospective feed, the corrected v2.3
feed, accepted targeted searches and both label-blind Lumid rehearsals.

- EventX input envelopes scanned: 5,770
- In-window usable endpoint rows: 2,343
- Unique EventX-observed normalised URLs: 1,903
- EventX-observed URLs absent from the warehouse: 0
- Warehouse rows matched to an earlier EventX receipt: 1,928
- Warehouse rows first observed at export completion: 26,379
- Conflicting publication timestamps: 698 rows across 348 URLs
- Conflict disposition: quarantined from primary B1 until deterministic resolution
- Availability index SHA-256:
  `dd7bcd148b91b1d3469139a5e96b689be897d5c943ee912bd463aa20030c7b79`
- Timestamp-conflict ledger SHA-256:
  `da39d4cca26ad62909bfa4e7f5a6818632135c64e6c42f1b82b7560b7615cfd7`
- Runtime reconciliation-manifest SHA-256:
  `862c4442b568d6edd74886b79ea8642ce2da0b9f99a18cb08b801f576330bd13`

The primary rule remains:

```text
first_seen_at = earliest successful EventX receipt across valid Lumid paths
available_at  = max(published_at, first_seen_at)
```

Lumid `ingest_ts` is retained as source provenance only. It is not substituted for
EventX `first_seen_at`, so the warehouse recovery cannot backdate primary B1 features.

## Continuity result

At the audit snapshot, the corrected collector ledger contained 1,108 requests: 1,099
successful and 9 failed. Twelve distinct greater-than-300-second operational gaps were
all recovered by later uncapped responses from unchanged checkpoints. The warehouse
window covered the original pre-launch interval. The result was:

```text
status: continuity_reconciled_with_warehouse
operational gaps unresolved: 0
pre-launch intervals unresolved: 0
```

Runtime continuity-audit SHA-256:
`cf97ea485398b8eb68ae24e75d905ff7bc7658c8f1b73982e5926e860e1fa013`.

## Frozen-cohort trade snapshot

A bounded Lumid pull for the same `[2026-08-08, 2026-08-28)` window passed all 14
market-detail mappings and all 14 venue-trade integrity checks.

- Canonical-YES trade rows: 17,823
- Kalshi rows: 16,331
- Polymarket rows: 1,492
- Zero-record markets: 0
- Kalshi JSONL SHA-256:
  `27a6c0f768a0ec42bf779aa7567637be9b4ebef9aad4c547d52c746be260a195`
- Polymarket JSONL SHA-256:
  `0cfa2a1767eeb863e45254a8fde8236180b3a72da36bf53371350acdf021b539`
- Runtime audit-report SHA-256:
  `341d70a1a261959eec1a7d16e2e15ad64bdda912e0ac7c1bfaed11c1b4e88b63`

The rehearsal program also issued its legacy news checks and therefore labelled its
combined status `incomplete` when `/news/latest` capped. That status is preserved.
The trade component passed; the independently verified warehouse and continuity
artifacts above are the controlling news evidence for this snapshot.

## Label-blind feature-readiness audit

On 29 August, the frozen news matcher and frozen feature windows were applied to the
reconciled snapshot without reading prices, labels, outcomes or holdout data. This is
a feature-availability diagnostic, not the official data gate or power analysis.

- Warehouse articles scanned: 28,307
- Deduplicated market/article associations after conflict quarantine: 43
- Markets with at least one association: 2/14
- Association concentration: 42 Clarity Act, 1 Iran-head-of-state; 12 markets had zero
- Primary-grid non-zero rows: 72/80,640 at 60 minutes, 406/80,640 at 360 minutes and
  1,450/80,640 at 1,440 minutes
- Frozen `news_symbol_mapped`: constant zero because no event-market symbol mapping is
  defined
- Export-completion diagnostic: 22 recovered associations become available together
  at `2026-08-28T05:25:00Z`; all 22 are warehouse-backfill components
- Point-in-time prefix/future-append checks: zero failures
- Trade timestamp coverage: 17,823 rows across all 14 markets
- Five-minute rows with a trade no older than 30/60/240 minutes: 19.43% / 27.50% /
  47.78% of all 80,640 rows
- Median price age conditional on a prior trade: 258 minutes

The source is complete for the closed snapshot, but feature support is currently too
sparse and concentrated to assume that B1 will be informative across the frozen
cohort. This is a source-content/estimand risk distinct from retrieval completeness.
It does not authorise changing the frozen matcher, cohort or B1 features. The same
audit must be repeated at September 28 before any labels are generated.

- Audit report SHA-256:
  `feb53ac06d8997961d7a98d1fb523ae310ecf15cad18d1fe10b91202a5d7afd6`
- Audit program SHA-256:
  `c685f5ff5785b553cdee361d01f7758bd4d99c23511ab30ca04db1227a019582`
- Runtime report:
  `data/v2_3_1/feature_readiness_20260829/audit_report.json`

## Reproduction programs

- `eventx/tasks/export_v2_3_news_warehouse.py`
- `eventx/tasks/reconcile_v2_3_news_warehouse.py`
- `eventx/tasks/audit_v2_3_news_continuity.py`
- `eventx/tasks/audit_v2_3_feature_readiness.py`

## Lumid Studio usability audit

The 29 August read-only Studio audit was performed without labels, outcomes, trade
prices or holdout access. The interactive browser service was unavailable, so UI
click-through is not claimed; the public Studio shell, live OpenAPI, catalog, MCP and
authenticated FinData routes were tested directly.

- Catalog: 13 schemas and 178 tables; 157 profiles completed, 19 large-table profiles
  timed out at 30 seconds, and two materialized-view schemas returned 404.
- `news.articles`: actual `information_schema` has 22 columns, while the Studio JSON
  schema exposes only 16 and omits `id`, `ingest_ts`, source/endpoint/run provenance and
  `search_tsv`; its table estimate also reports zero despite populated data.
- `/retrieve`: JSONL, CSV, CTE/window SQL, empty results and a 1,500-row result worked;
  Parquet was rejected and `/retrieve` is absent from OpenAPI. Unbounded news FTS timed
  out at 30 seconds, while an EventX-window-bounded FTS query completed.
- MCP `tools/list` returned 90 tools. Row lineage worked with the natural key
  `news.articles.id=240598138`; omitting the key returned the documented-by-path but
  unusable 400 error. Lineage-runs listing returned zero runs.
- 28 representative REST probes returned 2xx, including news/KOL/prediction-market,
  OHLC, quotes, fundamentals, macro, health and freshness routes. Kalshi open-interest
  and Polymarket orderbook returned valid empty results for the tested samples.

Audit reports:

- `data/v2_3_1/lumid_studio_audit_20260829/report.json` SHA-256
  `53686c328978ddd38e8a0c3028f085b1a9da8e19f38387daab8bb4086c21d26a`
- `data/v2_3_1/lumid_studio_audit_20260829/rest_report.json` SHA-256
  `7e1ef79aa7260153f9eda447bb2460995486c3220c33f0c1ebc2206899546b07`
- `eventx/tasks/audit_lumid_studio_warehouse.py` SHA-256
  `0b317b5703d766a8067d75da430c01750d2bc6f098ed0455f6a333e689d8ca67`
- `eventx/tasks/audit_lumid_studio_rest.py` SHA-256
  `9f885cca82c8e9b73240bf057c7447b620af3d2b98192b6b3000bd649abc87b8`

The final data-sufficiency gate still requires the same export and reconciliation over
`[2026-08-08, 2026-09-28)`, exact-window trades for all 14 markets, zero unresolved
censoring intervals, frozen hashes, and the preregistered power simulation before any
development label is created.
