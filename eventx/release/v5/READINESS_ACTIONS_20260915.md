# V5 readiness actions after returned review

## Completed

The user authorized the recommended adjudication on 15 September. MicroStrategy's
Bitcoin sale is corporate/traditional financial, with crypto secondary context:
the settlement variable is a company action. Original reviewer decisions remain
unchanged. All 30 pilot topics are now approved for cached-context classification,
not historical metadata or family certification. Pre-adjudication agreement stays
29/30; do not report adjudicated agreement as independent accuracy.

Reproducible task: `eventx.tasks.close_v5_topic_packet_20260915`.
Outputs and hashed input lineage: `data/v5/topic_adjudication_20260915/`.

- `approved_pilot_topics.jsonl`: 30 decisions.
- `remaining_topic_review.jsonl`: 4,621 unreviewed contracts, no suggested labels.
- `family_boundary_review.jsonl`: 1,522 provisional components, none certified.

Remaining reviewers should follow the original six-topic rubric in
`data/v5/review_followup_20260915/second_reviewer/INSTRUCTIONS.md`.
Classify actual settlement outcomes. Keep independent passes separate; record
insufficient context instead of inferring missing identities. Family review must
inspect resolution semantics and dependencies outside each component; a component
being connected is not evidence of independence from other components. The queue
covers the historical inventory, not an adopted V5 cohort. No auto-approval or
propagation of the 30 decisions to other contracts has occurred.

## Source evidence still required — request prepared, not sent

Existing small source probes already establish access; repeating failed expensive
queries is not useful. Ask Lumid for these specific missing items:

1. For May 19 UTC, expected schedule, overlapping runs, retry lineage and committed
   article counts for the eight feeds listed in
   `READINESS_FOLLOWUP_20260915.md` and its linked query artifacts. Distinguish a
   real empty interval from an ingestion outage. Include reconciliation of the
   failed/partial runs in `LUMID_CERTIFICATION_REQUEST_20260910.md`.
2. The exact field carrying updated availability for revised headline/summary
   text, with one redacted example or explicit confirmation of the existing field
   mapping. The accepted content-availability assurance is not being requested again.
3. Historical named YES outcomes and status/metadata evidence for the 15 IDs in
   `data/v5/review_followup_20260915/unresolved_identity_list.json`.

No new source query or adapter change was made in this pass: assigning an
unverified revision field would falsely resolve the mapping issue. Exclusion rules
must be an explicit, label-blind protocol decision, not silent missingness repair.

## Inference decision remains blocked

Reviewed `CERTIFICATION_RESOLUTION_20260910.md`: both prior block methods and
grouped-t failed persistent/regime-shock screens. Do not rerun the same screens
and call unchanged results certification. No new estimator was selected here.

Retain the new-family/new-calendar target. Before another candidate screen, specify
independent event/calendar episodes and plausible dependence assumptions using
source semantics rather than prediction outcomes. Then freeze the synthetic
process envelope, estimator, weighting, full selection hierarchy, simulation seed
and coverage/power acceptance rules. A defensible episode inventory is not yet
available; final family review is one input, not proof of temporal independence.
Narrowing to realized-calendar descriptive performance would require a separate
explicit protocol choice. We have not made that change.

## V4 health, checked without outcomes

Check timestamp: 2026-09-14 17:41:34 UTC (15 September in Singapore).
Collector and guard alive; 15 news days and 8 trade days checkpointed; 95 batch
receipts present; zero closed-day backlog; no reported metadata problems.
All 15 frozen implementation hashes match. No protected evaluation artifacts
exist. No sealed payload contents read, restart or source-completeness certification.
Evidence: `data/v4/health_checks/20260914T174134Z/report.json`.

## Execution boundary

V5 was not frozen or run. No prediction labels, protected outcomes, models or
original protocols were changed. Next work requires substantive remaining review,
the provider response above and an explicit defensible episode/inference design.
These are unresolved dependencies, not completed experiment steps.
