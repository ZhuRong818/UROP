# Independent review handoff

## Macro evidence annotation

Read [the rubric](ANNOTATION_RUBRIC.md) and use the [packet with recovered rules](../../../../data/v7/macro_metadata_20261010/REVIEW_PACKET_WITH_RULES.md). The authoritative machine packet is [packet_with_rules.jsonl](../../../../data/v7/macro_metadata_20261010/packet_with_rules.jsonl). Complete separate copies of [reviewer A](../../../../data/v7/macro_pilot_20261010/reviewer_A_blank.jsonl) and [reviewer B](../../../../data/v7/macro_pilot_20261010/reviewer_B_blank.jsonl). Use 120 unchanged pair IDs and Unicode code-point spans. Reviewer IDs must differ. Each reviewer records human identity, prior exposure, independence and outcome blinding.

Keep selection ledger, retrieval scores, source diagnostics, old judgments, prices and outcomes away from the semantic review. The two responses should be produced separately. Return both originals; do not merge them yourselves. A later source review remains separate from semantics. No reviewer has yet been assigned or response received.

The intake implementation is [intake_v7_macro_reviews_20261010.py](../../../tasks/intake_v7_macro_reviews_20261010.py). It checks hashes, ID coverage, attestations, labels and exact article/contract/prior spans, preserves both submitted files and writes a disagreement packet. It does not create final semantic gold, infer reviewer independence from filenames, or admit predictive rows.

Invocation after real responses arrive (replace filenames with actual paths and use a fresh output):

```sh
.venv/bin/python -m eventx.tasks.intake_v7_macro_reviews_20261010 \
  --reviewer-a /absolute/path/reviewer_A_completed.jsonl \
  --reviewer-b /absolute/path/reviewer_B_completed.jsonl \
  --output data/v7/macro_review_intake_UNIQUE_VERSION
```

## Paper A scientific review

The [expanded paper](../../../../MARKET_NEWS_PAPER_A_DRAFT_20261010.md) and [claim ledger](../../paper_a_20261010/CLAIM_REVIEW.md) are ready for a reviewer who did not develop the methods or select the models. Review chronology, cohort availability, target implementation, selection/adaptive search, inference assumptions, semantic transform fitting and scope of claims. The [paper review package](../../paper_a_review_20261010/REVIEW_REQUEST.md) supplies focused questions and a response form. Reviewer identity, assignment and the scientific judgment remain pending; an assistant audit is not a completed independent review.

No packet or source request has been sent externally. Raw article text and rule bytes remain local review materials; public redistribution rights are unresolved.
