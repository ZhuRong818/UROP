# Submitted V6 boundary reviews — validation status

Both submitted files passed structural validation against original hashed packets:
unique/exact review-ID sets, unchanged source evidence, allowed decisions and nonempty
reviewer/rationale fields. This does not validate the semantic decisions themselves.

| Submission | Decisions |
|---|---|
| Family,697 rows |40 must-link;15 unresolved;642 no-direct-link-established |
| Story,444 rows |2 related updates;442 distinct stories |

All rows identify `model_boundary_reviewer_v6_20260916`. Human/model provenance is
not yet confirmed. One submission per task is present, not two independent reviews
of each task. Do not rename the identifier or infer human independence from filenames.

The two related stories concern SK Hynix's US listing plan and Commercial Metals'
Q3 earnings preview/results. Family risk decisions include alternative representations
of the same Fed decision and uncertain succession/metric-definition boundaries.
Submitted rationales are retained for independent checking, not adopted automatically.

Combined conservative impact preview, retaining the existing194-pair quarantine:
**265/600 flagged pairs**,71 additional,335 remaining. This preview uses40 must-link
plus15 unresolved family decisions (34 reserved groups) and two flagged reserved
articles. It is not an amended cohort, certified subset, or new sampling design.
Original graph, packets, reviews and quarantine remain unchanged.

Evidence: `data/v6/boundary_submission_validation_20260916/report.json` and manifest.

## Next action

Confirm whether submissions were human-written, model-generated or human-checked
model outputs. Then obtain independent reviews without showing first-pass decisions:

- `data/v6/boundary_submission_validation_20260916/family_second_review_packet.jsonl`
- `data/v6/boundary_submission_validation_20260916/story_second_review_packet.jsonl`

These packets contain original evidence and blank decision/reviewer/rationale fields.
Use the existing boundary review rules; retain separate submitted copies. The
`*_decisions_requiring_resolution.jsonl` files contain first-pass judgments and must
not be shown to the independent reviewer before their decisions.

After independent review, adjudicate disagreements and unresolved boundaries, then
publish a new split/sampling version. Boundary certification, source admission,
association precision and forecast evaluation remain separate, unsatisfied gates.
