# V6 hybrid retrieval and association review

This is association-method development, not a forecasting experiment or a source
certification. Keep all V4/V5 artifacts and protected forecast outcomes untouched.

## Completed release

`data/v6/hybrid_audit_20260916/`: 27,760 scored pairs across200 development and100
reserved articles. Dense retrieval contributes12,933 candidates absent from the
BM25 top50 sets; this is retrieval diversity, not evidence of improved recall.
All scores finite and manifest/output checks pass. Reserved packet:600 pairs,
165 provisional groups, zero shared event IDs or provisional groups with the
development packet's424 groups. Maximum reserved/development article cosine:
0.7897371915634985. Story independence remains unverified.

Start annotation with **`data/v6/hybrid_development_reviews_20260916/packet.jsonl`**.
It contains2,063 unique development pairs: original1,199 plus864 additional hybrid
top-five candidates. Two blank response files accompany it. No human labels exist.
Keep the600-pair reservation separate; do not use its labels for tuning.

## Implemented method

- Structured BM25 top50 plus neural dense cosine top50; deduplicate their union.
- Local cross-encoder reranks every union pair. Preserve raw logits, not purported
  probabilities or automatic direct/background labels.
- Named outcome, question, event title and available retrospective rule text enter
  contract representations. Truncation limits: encoder default256 tokens, joint
  cross-encoder384 tokens. This can omit long-rule information and needs review.
- Model artifacts are downloaded once, pinned by revision/file hashes, then loaded
  offline. No research text is uploaded. Current models are admitted for retrospective
  association exploration only; historical training-cutoff eligibility is unverified.

Local numerical workaround: float64 encoder and bfloat16 reranker with eager attention; dependency pins in
`requirements-neural.txt`. Float32 smoke failures and their limits are preserved
in `NUMERICAL_FAILURE_20260916.md`. No invalid score is replaced with zero.

Model sources: [MiniLM sentence encoder](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
and [MS MARCO cross-encoder](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2).
They are generic retrieval models, not trained or validated for contract relevance.
Neither cosine nor reranker score is sufficient proof of relevance, fact novelty,
timing compatibility or correct resolution semantics.

## Development and separate reservation

The original 1199-pair pilot remains development-only. No human response has been
received. Hybrid development retrieval is restricted to event/groups represented
in that pilot's reviewer packet. Reserved retrieval excludes those groups and event
IDs. Scores from these restricted indexes are not directly comparable to the
original unrestricted BM25 ranking as a performance estimate.

For the reservation, sample500 new article IDs from the opened discovery inventory;
verify exact source text hashes and clocks. Exclude articles with identical content
or encoder cosine >=0.8 to any of the200 development articles. Reserve100 survivors
under deterministic hash ordering. Per article select five reranked candidates plus
one random contract outside the retrieval union: target600 pairs.

This is a **provisional association-audit reservation**, not a certified independent
test. Family boundaries remain provisional, embedding similarity can miss related
stories, and the full development corpus has not received a human story audit.
The score threshold is an outcome-blind screen, not a validated story classifier.
Review and adjudicate story/event boundaries before freezing/evaluating link labels.
Do not tune on reserved relevance judgments. If groups must change, create a new
version and inspect overlap before evaluation.

Selection is enriched and story-screened. Overall population inclusion probabilities
are not claimed. Do not report unweighted precision as corpus-wide precision or use
the reserved packet to claim exhaustive retrieval recall. Independent deeper
event–day search tasks and design-aware precision inference remain outstanding.

## Reviewer workflow

Start with the combined development packet above, using the definitions in
`IMPLEMENTATION_STATUS_20260916.md`. Two real reviewers should work independently;
machine-generated suggestions are not human gold labels.

For the separate reservation, send only `reserved_review_packet.jsonl` plus one
blank `reviewer_A_responses.jsonl` or `reviewer_B_responses.jsonl` to each reviewer.
Do not share scored pools, selection ledgers, the other reviewer's answers or market
outcomes. Keep returned files separate and retain original blank templates.

Each response needs its pair ID, reviewer identifier, relevance class, outcome
applicability and exact article quotations supporting the judgment. Distinct IDs
alone do not prove independence; record that separately. Disagreements require
adjudication, not silent majority or automated replacement.

Validation command (does not score forecasts):

```bash
.venv/bin/python -m eventx.tasks.validate_v6_link_reviews \
  PATH_TO_PACKET.jsonl REAL_REVIEWER_A.jsonl REAL_REVIEWER_B.jsonl
```

The validator rejects blank/invalid labels, duplicate/missing IDs, identical reviewer
IDs and quotations absent from the supplied article. It cannot certify that a human
made a judgment or that a quotation supports the label; those require review.

## Remaining gates

Human link validity; story/event separation; historical metadata and active status;
news export/version reconciliation; model eligibility; independent recall audit;
novelty audit; calibrated thresholds and design-aware precision uncertainty. No
forecast model or association threshold is promoted by merely completing inference.
