# Proposition matcher 0.3: development readiness

## Decision

Not ready for predictive training or an independent accuracy audit. This is a
bounded engineering coverage check, not a successful association validation.
No new labels, reserved review packets, price outcomes or holdouts were read.
Earlier matcher versions and the failed finite-frame audit remain unchanged.

## Implemented

- Traceable exact-name, multiword company legal-suffix and full AI-model separator
  aliases. Aliases retain quoted evidence and article offsets, not verified identity.
- Six narrow relation adapters: market capitalization, net worth, album sales,
  index inclusion, peace agreements and announcements. Subject, relation and explicit
  period evidence are required. These are lexical candidates, not full entailment.
- Fifteen synthetic positive/hard-negative tests; all 97 related tests pass.
- Deterministic broader development census: exclude all 40 original article IDs
  from the 2,063-pair development packet, leaving 1,666 pairs / 160 articles.
  The selection receipt was written before matching, with input/code hashes.

The original 19 unsupported cases span price thresholds (6), event deadlines (4),
music sales (3), sports (3), corporate actions (2) and speech (1). New adapters cover
13 of those cases; six still have unsupported adapters. No asserted aliases were
found for the 16 unresolved-subject cases; they remain abstentions. Missing subject
text is not proof of global irrelevance.

## Results

| Output | Original 40 (regression) | Other development pairs |
|---|---:|---:|
| Pairs / articles | 40 / 40 | 1,666 / 160 |
| Direct candidates | 1 | 0 |
| Background | 3 | 39 |
| Insufficient evidence | 35 | 1,621 |
| Metric/period contradictions | 1 | 6 |
| Temporally ineligible | 11 | 437 |
| Eligibility uncertified | 29 | 1,229 |
| Predictive admissions | 0 | 0 |

Among broader pairs, 1,076 lack a supported adapter, 379 have unresolved subjects,
143 lack the extension subject in supplied text, and 23 have missing/conflicting
semantics. New adapters route 157 pairs but yield no direct candidates. Candidate
absence is neither a precision result nor a recall result: no gold was collected
for this check. Synthetic positives demonstrate code paths, not real-world quality.

## Next substantive step

Inspect development candidate-generation failures before expanding annotation:
separate absent contract identity/metadata, genuinely missing article subject, and
unsupported predicates. Build a bounded subject-first retrieval alternative using
traceable contract entities and supplied news text. Compare its candidate coverage
on a fixed development set; do not loosen evidence requirements to manufacture
matches. Sports, speech, mergers and other unsupported relations remain incomplete.
Only once credible real candidates exist should a separately specified independent
association audit be considered. Historical source/metadata eligibility remains a
separate gate regardless of semantic improvements.

## Reproduction and evidence

- Implementation: `eventx/v6/proposition_matcher_v03.py`
- Tests: `eventx/tasks/test_proposition_v03.py`
- Runner: `python -m eventx.tasks.check_proposition_v03_development`
  (fails if its output directory already exists; do not overwrite the release).
- Artifacts: `data/v6/proposition_v03_development_20260917/`:
  `selection_receipt.json`, `report.json`, `subject_diagnosis.json`,
  `broader_cases.jsonl`, `regression_cases.jsonl`, `manifest.json`.
