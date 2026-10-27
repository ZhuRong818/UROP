# V5 readiness follow-up — 15 September 2026

Seven read-only Lumid queries completed: five succeeded, two returned HTTP 400.
All queries projected source identity, timestamps or provenance only. No outcomes,
prices, sealed payloads or new labels were requested.

## Completed

- Resolved the ambiguous Belgium market as a sports fixture using its embedded
  event title **Belgium vs. Egypt**, event ID `351728`, and slug
  `fifwc-bel-egy-2026-06-15`. Recorded an append-only first-review addendum. All 30
  sampled contracts now have first-review assignments; they are not final approvals.
- Prepared a 30-record second-review packet with the first review's labels,
  rationales and automatic suggestions removed. It requires an independent
  reviewer; no second review has been fabricated or sent externally.
- Queried all 15 missing Kalshi subtitle records. All 15 returned, but normalized
  subtitles and inspected raw identity fields remain null. These originate from
  `predexon_ondemand` through Lumid. Ticker abbreviations were not expanded into
  guessed candidate/team identities.
- Added one explicit primary-to-general California gubernatorial dependency to the
  existing provisional family graph. Component count decreased from 1,523 to
  **1,522**. This is a must-link extension, not final certification; remaining
  boundaries and historical metadata are unresolved.

## May 19 coverage evidence

The broad news-named run query returned five May 19 runs in three endpoint/status
groups: analyst grades-news and price-target-news. These are not the eight article
feeds found in the discovery export. Do not reconcile their write counters against
the article export without a documented table/feed mapping.

An exact eight-feed query over May 17–20 returned 20 daily endpoint/status groups
on May 18 and May 20, **none with a May 19 run start**. Together with the earlier
zero retained article-ingestion query, this makes a coverage gap plausible. It does
not identify scheduler intent, overlapping runs, updates, or complete retry history.
Keep the day unverified; do not convert it to zero news or certify a seven-day
lookback crossing it. No exclusion or date change has been applied to an experiment.

Repeated larger joined/count queries again returned HTTP 400 after about 30 seconds.
The exact cause is unconfirmed. Small projections work, so this is not a complete
loss of source access. Stop repeating those identical expensive queries; request
provider-side committed counts or a supported bounded count/export path.

## Review artifacts and next dependencies

- Evidence/report/manifest: `data/v5/review_followup_20260915/`.
- Give only `second_reviewer/` to the independent reviewer; all 30 response fields
  are blank, with a topic rubric in `INSTRUCTIONS.md`.
- `unresolved_identity_list.json` identifies the exact 15 missing subtitles.
- `family_dependency_addendum.json` records the new edge and semantic evidence.
- SQL: `eventx/release/v5/coverage_queries_20260915/`.
- Source receipts: `data/v5/provenance_recovery_20260908/*20260915*`.

To continue source certification, obtain:

1. A schedule/retry/retained-row explanation for May 19 for the specified article
   feeds, and reconciliation of the previously identified failed/partial runs.
2. Named YES outcome identity and historical metadata/status for the 15 listed
   Kalshi contracts, or document their eventual exclusion before labels.
3. A second reviewer completing the prepared topic packet independently, followed
   by adjudication and full-cohort review.

The administrator's news-content assurance remains accepted provisionally; it is
not being requested again. Family-boundary and statistical-inference certification
still precede V5 execution. Existing plans and frozen artifacts remain unchanged.
