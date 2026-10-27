# EventX v3 historical feasibility implementation amendment 2

Frozen on 2026-09-01 while the feasibility study remained label-blind. No
prediction-market outcome, EventX label, model prediction, validation metric or
October holdout row was read.

## Problem found

The first metadata implementation requested snapshots for every distinct activity
key. The completed Kalshi activity export contains 16,802,432 ticker keys, although
only 9,422 can satisfy both already-frozen cohort activity gates. The unfiltered
metadata run consequently created 31,676 completed 100-key batches, 63,354 page and
query files, and 2.35 GiB of incomplete output without producing a valid manifest.

## Corrected implementation

1. Metadata is requested only for an activity key that can still satisfy both frozen
   cohort gates: at least 100 valid distinct trades and at least 10 active UTC days.
   The thresholds and inclusion semantics are copied unchanged from
   `feasibility_protocol.json`.
2. For Polymarket, a condition ID is retained when any asset can pass both gates.
   This may conservatively over-include metadata before canonical-YES mapping, but it
   cannot exclude a condition whose canonical-YES asset passes.
3. Each metadata checkpoint records the eligible-key count, SHA-256 fingerprint and
   exact filter. A checkpoint lacking or disagreeing with these fields is rejected.
4. Retrieval receipts retain run ID, row count, materialized URI, output format,
   byte count and latency. SQL remains in separately hashed query artifacts; verbose
   duplicate access-chain SQL and signed URLs are not copied into checkpoints.
5. The exporter fails closed before downloads if the working volume has less than
   5 GiB free.
6. The incomplete unfiltered attempt is abandoned with hashes and counts recorded in
   `ABANDONED_KALSHI_METADATA_ATTEMPT_20260901.json`. Completed activity and news
   manifests are not modified.
7. The final feasibility audit streams the large activity exports and retains only
   activity records whose metadata key was materialised. This is an equivalent join
   to the former all-row in-memory dictionary and bounds audit memory without changing
   any eligibility or association decision.

This amendment changes retrieval efficiency, checkpoint compatibility and storage
safety only. It does not alter the historical window, source, taxonomy, availability
rule, association rule, cohort thresholds, support gates or pass/fail estimand.
