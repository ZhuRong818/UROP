# Enriched-card retrieval comparison

Created134 separate retrospective review cards with exact source-file/line/field
and ingestion provenance for recovered rule text.128 have rules;6 remain missing.
Original cards remain unchanged; certificates unset and training admission false.

On the fixed185 time-screened pairs/70 articles, compared question+subtitle TF-IDF
ranking with question+subtitle+rules using shared unigram/bigram IDF.28 articles
have multiple candidates. Adding rules changes the top-ranked contract for9 articles.
All output hashes and370 finite score-range checks pass.

This is a lexical representation ablation, NOT a validated semantic relation model.
Changes are not improvements without reference labels. No threshold was tuned and
no links admitted. Shared IDF uses retrospective cards, so this is not a point-in-time
deployment experiment. Original relation decisions are retained alongside scores.

Artifacts: `data/v6/enriched_rule_comparison_20260921/` contains enriched cards,
185 score pairs, per-article ranking changes, report and lineage manifest.

Next inspect the nine changed rankings for rule boilerplate, entity/metric confusion
and genuine predicate evidence before adding model complexity or requesting reviews.
No new API calls, annotation, predictive training or holdout outcomes were used.
