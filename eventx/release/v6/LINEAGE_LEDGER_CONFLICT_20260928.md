# V6 lineage ledger conflict: three allegedly missing runs are present

Date: 28 September 2026. A later user-relayed source investigation said only two of the five scoped failed run IDs existed in its `provenance.runs` ledger, with no runs after 8 June, and suggested an alternate `/ingest` path or tenant for the other three. **This conflicts with direct EventX evidence.** Preserve that relayed account as a separate observation; do not infer a different ingestion path from it.

The original prereceipted 27 September probe obtained HTTP 200 for all nine `GET /catalog/lineage/run/{run_id}` requests. A new prereceipted check through EventX's configured `https://lum.id/findata` returned HTTP 200 again for the three disputed UUIDs. A separate prereceipted exact-UUID `POST /retrieve` query against `provenance.runs` on the **same configured API** returned **3/3 rows**:

| Article | Run ID | Started UTC | Ended UTC | Status | `args.to` |
| --- | --- | --- | --- | --- | --- |
| 189518836 | `fd734424-86f2-4d65-a67c-868d6f80730a` | 2026-06-23 16:45:01 | 2026-06-23 18:52:01 | failed | 2026-06-24 |
| 197137081 | `592ebc42-79ad-4b33-af2d-628b5edb6167` | 2026-06-30 02:45:00 | 2026-06-30 04:52:01 | failed | 2026-06-30 |
| 201756152 | `86c568d4-f947-43e2-950b-8cf740690a9e` | 2026-07-02 16:30:01 | 2026-07-02 18:37:01 | failed | 2026-07-03 |

All three are `finnhub:company-news` abandoned runs with null aggregate write counters, matching the earlier lineage records and article `source_run_id`s. The SQL result itself disproves a claim that this `provenance.runs` surface has zero post-8-June rows. The two new frozen artifacts are `data/v6/lineage_surface_conflict_20260928/` (catalog GET) and `data/v6/lineage_sql_surface_20260928/` (exact SQL query/result). The latter includes the query text, prequery receipt, report and hashes. Neither result proves a complete news window or any historical market status.

## Required reconciliation before more ingestion-path probing

Ask the source analyst to run the exact three-UUID query in `data/v6/lineage_sql_surface_20260928/query.sql` and report the API/deployment, authenticated role or tenant, query scope/filter, execution time and raw three-row result or a documented reason that their surface differs. Compare it with EventX's `https://lum.id/findata` result. Then search successor runs and cursor evidence for the **same** endpoint/feed/deployment and decision-time windows. An endpoint-level empty `scope_key` may explain the prior symbol-substring probe, but current cursor state alone does not reconstruct historical transitions. Keep failed intervals unknown unless clean completion by the decision time is shown.

Querying `provenance.ingress_acl` or submitter metadata first would not resolve this contradiction: an access-control or submitter record is not a committed article-row or full-window receipt. Use alternate-ingest investigation only if the same-surface UUID lookup actually fails after deployment/filter alignment.

**Decision:** Three runs are present, not absent, on EventX's configured Lumid catalog and SQL surfaces. Their feed windows remain uncertified. No source admission, model fit or protected-data access; V6 predictive support stays 0/8,844 contract-days.
