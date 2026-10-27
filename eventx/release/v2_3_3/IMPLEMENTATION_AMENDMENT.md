# EventX v2.3 multi-snapshot availability-ledger amendment

Frozen on 2026-09-02 before any v2.3 development or holdout label, prediction or
model metric was created or inspected.

## Problem

Lumid `/news/latest` is silently capped, so EventX closes censored periods with
repeated, hashed warehouse exports. The same article can occur in more than one
snapshot. Using only the newest reconciliation would replace a valid earlier EventX
receipt with the later export-completion time, unnecessarily removing point-in-time
news features. Selecting a publication or Lumid ingest timestamp instead would risk
backdating information.

## Frozen implementation rule

1. Every input reconciliation manifest and availability-index hash must pass before
   merging.
2. For a repeated Lumid warehouse ID, retain the earliest verified EventX
   `first_seen_at` from the supplied reconciliation receipts.
3. Recompute `available_at = max(published_at, eventx_first_seen_at)`; never substitute
   Lumid `ingest_ts` as EventX availability.
4. If the same stable URL has conflicting publication timestamps across snapshots,
   quarantine every affected row from primary B1.
5. Preserve the selected receipt path/hash, receipt count, all input hashes and output
   hashes in a label-blind merge manifest.
6. The feature-readiness audit must verify the merged availability manifest before it
   can consume a merged index.

This is an operational reconciliation clarification. It does not change the cohort,
dates, association matcher, B0/B1 features, label, learner, validation, metrics,
promotion gates or sealed October holdout.
