# EventX v2.3 news collector implementation amendment 2

Frozen on 2026-09-01 before any v2.3 development or holdout label was created or
inspected.

## Scope

This amendment repairs two label-blind collection defects while preserving every
scientific decision in protocol
`eventx-v2.3-news-availability-clarifications-20260817`.

The predecessor implementation stopped after its cadence loop computed a slightly
negative sleep interval between the loop condition and `time.sleep`. The Lumid
re-audit also established that a small number of source rows can carry implausible
future publication timestamps.

## Corrected implementation

1. The cadence wait is clamped to `[0, 0.25]` seconds and exits the inner wait loop
   when the remaining delay is zero.
2. A publication timestamp more than five minutes after EventX retrieval is treated
   as invalid under the existing publication-time quality rule. The raw row is
   retained in an append-only quarantine ledger but is not written to the primary B1
   news stream. Its stable entity is marked quarantined if a predecessor collector
   had already observed the identity, and repeated unusable source returns are
   deduplicated by stable identity and publication time rather than retrieval time or
   mutable vendor payload.
3. Stable entity identity, append-only content versions, timestamp-conflict
   quarantine, 60-second polling, the 200-row cap alarm, the 300-second gap alarm,
   checkpoint non-advancement on cap/failure and
   `available_at=max(published_at, first_seen_at)` are unchanged.
4. The collector resumes the predecessor SQLite state and append-only request ledger.
   Every start writes a separate restart receipt with code, contract, manifest, prior
   checkpoint and prior-success metadata.
5. The detached launcher runs the collector beneath `caffeinate` to reduce host-sleep
   interruption risk.
6. The interval after the predecessor's final success remains unresolved until an
   independently verified Lumid warehouse reconciliation closes it.

No label, prevalence, trade price, prediction, model metric, fold, outcome, or
October holdout observation was used to make this amendment.
