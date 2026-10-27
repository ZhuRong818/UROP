# Targeted collection and overlap check — 21 September

## V4 remains separate

Checkpoint-only health check at 03:04:31 UTC: collector and caffeinate alive;
22 news days and 15 trade days checkpointed through September 20. All 172
expected batch receipts present, no closed-day backlog, all 15 frozen hashes match.
No protected evaluation artifacts exist. Sealed payloads/outcomes were not opened;
this does not certify source completeness.
Evidence: `data/v4/health_checks/20260921T030431Z/report.json`.

## Development overlap and metadata collection

Same 500 development articles and 4,651 cached cards, no new cohort selection.
2,099 cards have extracted subject aliases; 426 contracts have subject mentions.
Among 1,648 subject pairs: 659 before recorded close, 357 at/after close,
632 lack a cached close. This is a temporal screen, not semantic relevance.

Forty contracts were prioritized by pre-close subject-match count, with ID tie-breaks.
All selected contracts were Kalshi; speech/threshold variants dominate this first
batch. It is not representative of venues, subjects or independent events.
Lumid returned all 40 requested records, each with primary rules, open and close
times. Thirty-one snapshots were ingested at/after recorded close. These records
support retrospective semantic investigation but do not certify historical versions.

Selection and overlap: `data/v6/targeted_recovery_20260921/`.
Fetch receipt/data: `data/v5/provenance_recovery_20260908/v6_targeted_metadata_20260921.json`.

## Next collection gate

A bounded source-count query checks Reddit/SoFi news in the intersection of their
recovered trading windows and opened development history, using ingestion time.
These two symbols are probes, not a revised research population. Symbol equality
misses untagged articles and does not establish coverage by itself.

Result: aggregate query returned HTTP400 after approximately 30 seconds. A smaller
June 1 ingestion-day probe succeeded with zero exact-tag rows. Neither result proves
news absence or full-window completeness. No additional news rows were recovered.
Receipts: `data/v5/provenance_recovery_20260908/v6_targeted_news_counts_20260921.json`
and `v6_targeted_news_probe_20260921.json`. Both attempts preserved separately.

Do not bulk-download more trades or change eligibility until the metadata windows,
existing trade coverage and news counts are reconciled. Preserve the accepted
news-content assurance; source-version and family/inference issues remain separate.
No predictive training, new annotation, family promotion or holdout evaluation.
