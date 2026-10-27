# ID-backed reconciliation and embedding-assisted review

## Completed

Incorporated 1,752 source-selected leg references as 728 unique parent-event to
underlying-event must-links. Retained 36 underlying event nodes outside the original
1,551-node inventory rather than dropping unmatched legs. Prior reviewed links
are preserved. The resulting graph contains **1,280 provisional components**,
down from 1,487. The largest contains 158 event nodes: multi-leg connectivity can
produce large groups and must not be interpreted as independent-event sample size.

All 728 intentionally split edges were rejected; graph order-invariance and
preservation of previous components passed. Exact parent IDs match the inventory;
underlying contract/event mappings are checked where present. Missing underlying
metadata remains explicitly unresolved. Edges constrain split isolation, not
payout equivalence, historical validity or news relevance.

## Embeddings implemented

Local word/bigram TF-IDF followed by 128-dimensional truncated-SVD/LSA and L2
normalization; seed73, top-five cross-component neighbors, cosine >=0.65.
This is a statistical semantic embedding baseline, **not a pretrained neural
sentence encoder**. No external embedding service or new dependency was used.

Embedded 1,551 event documents from cached questions/subtitles. Thirty-six external
nodes lack descriptive text and are retained in the graph but not embedded.
Produced **3,849 unique review candidates** with original texts, cosine scores and
explicit-year-disagreement flags. Dates without explicit years and semantic rule
differences still need manual review. Similarity scores are not calibrated
probabilities. **Zero embedding-only merges** were made.

The transform is fitted to the allowlisted metadata inventory for transductive
review assistance only. It is not a point-in-time news transform or predictor and
must not be reused as such. Review rules require entity/date/resolution checks.

## Artifacts

Canonical output: `data/v5/embedding_family_reconciliation_20260915_v2/`.

- `candidate_components.json`: updated graph.
- `market_family_mapping.jsonl`: mappings for original inventory contracts.
- `leg_edge_evidence.jsonl`: exact source-backed edge provenance.
- `semantic_review_candidates.jsonl`: pending embedding suggestions, no approvals.
- `external_nodes.json`: retained outside-inventory nodes.
- `embeddings.npy`, `lsa_transform.npz`, `vocabulary.json`, `document_index.jsonl`:
  saved representation and document order; configuration and hashes alongside.

The initial output directory without `_v2` is an incomplete attempt: serialization
of NumPy vocabulary integers failed before manifest publication. It is retained
for audit, not a release. Fixed integer serialization and reran into the new
directory. Use only the completed `_v2` manifest.

## Next / boundaries

Review candidate pairs and large components, recover the 44 missing underlying
contract records and validate cancellation rules/historical semantics. No final
families certified, cohort admitted, outcomes inspected, model fitted or frozen
protocol changed. Source and statistical-inference gates remain unresolved.
