# EventX historical feasibility protocol

Protocol ID: `eventx-v3-historical-feasibility-20260830`

This is a label-blind data-sufficiency protocol. It does not replace or amend the
active v2.3 prospective experiment, and it does not authorize labels, model fitting,
outcome inspection, or holdout access.

The feasibility window is `[2026-05-17, 2026-08-08)` UTC. News is usable only when
both `published_at` and Lumid `ingest_ts` are present. Candidate point-in-time
availability is `max(published_at, ingest_ts)`. Articles ingested more than 24 hours
after publication are late backfills and may appear only in a future sensitivity
analysis. The primary export also rejects records whose ingestion timestamp precedes
publication. Lumid must confirm that `ingest_ts` represents first warehouse observation
before a confirmatory historical protocol can be frozen.

Market association uses the earliest Lumid metadata snapshot available before the
historical cutoff. The export retains only identifiers, question text, canonical-YES
mapping fields, dates, and ingestion provenance. Raw vendor payloads and resolution
fields are excluded so the feasibility inventory cannot expose market outcomes.

Trade-activity inventory is retrieved in one-day UTC chunks with keyset pagination.
This keeps each warehouse statement within Lumid's observed 30-second limit. Every
failed or successful attempt is persisted in the retry ledger; a failed retrieval is
never interpreted as an empty interval.
Activity thresholds count distinct trade IDs with valid venue-native price ranges;
duplicate or invalid-price rows cannot make a market eligible.

News-support gates count normalized URLs once, fall back to article ID only when a URL
is unavailable, and exclude URL identities with conflicting publication timestamps.
An association counts only when its point-in-time availability falls between that
market's first and last observed trade in the feasibility window.

The historical branch may advance only if all machine-readable gates in
`feasibility_protocol.json` pass without outcome access. A passing result authorizes
drafting a separate, hash-locked historical protocol with a chronological 80/20 split.
A failing result is retained as a descriptive Lumid coverage result.

The existing January–March 2025 exports remain provenance evidence. They do not
support 2025 point-in-time inference because their observed Lumid ingestion timestamps
fall in 2026.
