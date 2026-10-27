# Cached multi-leg metadata inspection

Inspected the historical Kalshi metadata cache and all 95 page files (96 files
total). All **397 target contracts** are present; 794 matched records include
the consolidated/page copies, not 794 distinct contracts.

All 397 have contract open, close, expiration and ingestion timestamps. However,
none of these records contains explicit underlying leg IDs, per-leg polarity
mappings, per-leg event dates, resolution/cancellation rules or a raw payload.
Human-readable YES/NO selection text is present but is not an ID-linked leg map.

The original export SQL explicitly selected only market/event identifiers, title,
subtitles, market type, contract timestamps and provenance. Thus the review queue
was not hiding a richer record in these source pages: the needed structure was
omitted from the fetched projection. Contract expiration is not a substitute for
the dates of the underlying events. This does **not** establish that Lumid lacks
the fields, or that no other repository cache contains them.

No additional family links or eligibility decisions were made. The 397 mappings
remain unresolved and the 1,487-component family graph is unchanged. No provider
contact, protected payload access or experiment changes.

Evidence: `data/v5/cached_multileg_inspection_20260915/` contains the per-contract
source lines, field inventories, report and input/output hashes. Task:
`eventx/tasks/inspect_v5_cached_multileg_20260915.py`.

Next decision: recover a richer metadata projection when source access is resumed,
or propose a separate label-blind exclusion of unresolved multi-leg contracts.
Neither action is authorized or applied by this inspection alone. Exclusion would
not resolve the remaining single-contract family, source or inference checks.
