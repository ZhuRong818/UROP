# Rich multi-leg metadata recovery

User authorized renewed metadata retrieval. Six read-only Lumid `/retrieve`
queries succeeded: a three-contract probe, four exact-ID parent batches
(100/100/100/97 records), and a 70-ID underlying query (26 records).
Projected contract structure/provenance only; no prices, resolved results or
protected holdout payloads requested. No message sent to the administrator.

## Recovered

- All **397/397 parents** have `raw.mve_selected_legs` containing market ticker,
  event ticker and side: **1,752 references to 70 unique underlying contracts**.
- All returned selections are YES. Explicit IDs replace the prior name-only
  display fragments; mappings no longer depend on inferred entity matches.
- **26/70 underlying records** returned; **44 missing from this exact-table query**.
  No event-ID conflicts among matched records. This does not prove source-wide absence.
- **39 parents** have metadata for every underlying leg, but are not certified.
- Parent primary/secondary rule fields are empty for all 397. Seventeen underlying
  records have nonempty primary and secondary rule text; the remainder do not.

The previous local projection genuinely omitted available structure. This retrieval
resolves the parent-to-leg ID gap, not historical validity, cancellation mechanics,
missing underlying records or final family independence. No graph or protocol changed.
Current family map remains 1,487 provisional components; zero final certification.

Evidence: `data/v5/rich_leg_recovery_20260915/` contains parent/underlying metadata,
leg references, missing IDs, consistency checks and hashes. Original API receipts
remain in `data/v5/provenance_recovery_20260908/`; exact SQL in
`data/v5/rich_leg_queries_20260915/` and the probe under
`eventx/release/v5/coverage_queries_20260915/multileg_raw_probe.sql`.

Next: reconcile explicit underlying IDs against the family inventory and review
the retrieved rule text. Keep external/missing nodes explicit; do not discard a
leg because its contract lies outside the research cohort. Investigate a bounded
alternative metadata path for the 44 missing records and parent cancellation rules
before final certification. Model fitting and source/inference gate relaxation
remain out of scope.
