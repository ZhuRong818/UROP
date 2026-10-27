# Bounded association audit — final result

The approved audit cycle is complete and did not establish bounded feasibility.
Canonical results: `data/v6/bounded_final_audit_20260917/report.json`.

| Endpoint | Conservative errors | Upper error bound | Decision |
|---|---:|---:|---|
| Family separation | 3/74 | 11.4338% | Inconclusive |
| Story separation | 0/72 | 4.8499% | Pass |
| Direct article–contract relevance | 39/40 | 99.5% | Fail quality target |

Bounds invert the exact hypergeometric distribution at alpha=0.05/3, for frozen
finite populations of 551, 433 and 200 respectively. They are conditional on the
submitted reference judgments, not universal independence or predictive accuracy.

The relevance sample has one agreed direct/yes-proposition success, 37 agreed
failures of that strict criterion and two disagreements closed unresolved by user
approval. Those two count conservatively as errors, not proven false links. All
40 cases remain in the denominator. No extra adjudicator judgments were invented.
Agreement alone is not evidence of relevance: background or event-only agreement
does not pass the contract-specific criterion.

Three discovered family dependencies are preserved in
`discovered_dependencies.jsonl`; no graph release or removal of quarantine occurs.
The 335 reserved preview pairs remain unadmitted. Protected forecast outcomes were
not read, and this association result does not show that news lacks predictive value.

## Integrity and next step

Input/output manifest hashes were checked before the one-shot run, which records
a consumption receipt. The evaluator was implemented after annotations, contrary
to the intended prewritten-code sequence; the mathematical specification was
prefrozen and unchanged. Seven synthetic test groups checked acceptance anchors,
census/extreme cases and combinatorial probabilities before the run. This deviation
must accompany reporting. Reviewer independence remains user-attested rather than
verified from filenames or identifiers.

Stop this audit cycle: no replacements, additional annotation batches, threshold
relaxation or revised denominators. The next useful work is a development-only
failure analysis of contract entity, predicate, period and measurement mismatches.
Any revised matcher needs a separately approved version and untouched audit evidence;
these 40 cases cannot be reused as independent confirmation. Do not begin a news
prediction experiment using this matcher as though its association gate passed.
