# Corrected-queue metadata recovery

The top40 source-event groups contain134 contracts. Reused34 previously recovered
records and fetched all100 remaining records:52 Kalshi and48 Polymarket.
All three requests/downloads returned HTTP200. Receipt hashes, exact requested ID
sets and row counts pass; no batch reached its500-row limit.

Among the100 new records:

- 94 contain rule/description text (six Kalshi rules missing).
- 100 contain opening/start fields.
- 96 contain close/end fields (four Polymarket end fields missing).

These are descriptive snapshots filtered to ingestion before July22, not certified
point-in-time histories. Polymarket start/end fields may not equal actual trading
activation/closure. Original cards and frozen artifacts remain unchanged. Zero
admissions; no prices, settlement outcomes, new labels or holdout payloads requested.

Plan: `data/v6/queue_metadata_20260921/`.
Verified report/manifests: `data/v6/queue_metadata_verified_20260921/`.
Append-only source receipts: `data/v5/provenance_recovery_20260908/v6_queue_*_20260921.json`.

Next reconcile all134 records against article clocks, flag the six missing rules
and four missing end fields, and distinguish nominal dates from actual trading
windows before any predictive admission or expanded news collection.
