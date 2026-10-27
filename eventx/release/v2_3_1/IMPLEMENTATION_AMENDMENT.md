# EventX v2.3 news collector implementation amendment 1

Frozen at 2026-08-27 before any v2.3 development or holdout label was created or
inspected.

## Scope

This amendment changes only the label-blind storage implementation of the v2.3 news
collector. It preserves all scientific decisions: Lumid remains the sole source,
`/news/latest` remains the endpoint, polling remains fixed at 60 seconds, responses
of at least 200 rows remain censored, gaps above 300 seconds remain alarms, capped or
failed requests cannot advance the checkpoint, and primary availability remains
`max(published_at, first_seen_at)`.

The original implementation incorporated a full-row content hash into the purported
stable record key. A headline, summary or timestamp revision could consequently
create a new entity and evade same-article timestamp-conflict detection.

## Corrected implementation

1. Stable identity uses a Lumid provider identifier (`article_id`, `id` or `uuid`),
   otherwise a conservatively normalised URL.
2. Records without either use a clearly flagged content fallback.
3. Content SHA-256 values are stored as append-only versions beneath the stable
   identity and do not change `first_seen_at`.
4. Conflicting publication timestamps for one stable identity quarantine that entity
   until reconciliation.
5. The corrected collector launches in parallel with the legacy v2.1 collector; it
   does not overwrite or relabel legacy output.
6. Its launch receipt records hashes, PID, initial checkpoint and the unresolved
   pre-launch development interval.

No outcome label, prevalence, model metric, prediction, fold or holdout observation
was used to make this correction.
