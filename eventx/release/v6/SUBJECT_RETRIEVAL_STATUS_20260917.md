# Subject-first retrieval: development implementation

## Outcome

Implemented and run on the same fixed 160 development articles, searching all 4,651
cached contract cards rather than only their previous retrieved pairs. No annotation,
network fetch, model fit, reserved article inspection or holdout access occurred.
No source or family certification was granted.

Subject extraction now covers 1,742 contract cards. It supports additional question
forms for company reports, earnings-call speakers, sports participants, album/artist
pairs and named event actors, alongside the previous adapters. Each retrieval includes
contract field offsets, article field offsets and the exact matched alias. Short
abbreviations are case-sensitive; no inferred ticker or surname aliases are added.
These are retrieval hypotheses, not verified entity identities or proposition links.

## Measured coverage

| Stage | Pairs | Articles |
|---|---:|---:|
| Subject mentions across all cards | 463 | 35 |
| After generic-subject and domain-context filter | 155 | 25 |
| Direct candidates from unchanged proposition matcher | 0 | 0 |

First-pass retrieval found 402 pairs absent from the previous 1,666-pair packet.
After filtering, 111 previously absent pairs remain (44 overlap the earlier packet).
The filter rejects 15 generic-subject matches and 293 missing-domain-context matches.
Retained pairs: 73 background / 82 insufficient evidence; 138 uncertified / 17
temporally ineligible; zero predictive admissions.

The first pass exposed common-word and cross-domain mistakes, such as artist Future
versus financial prose and Iran football contracts versus geopolitical reporting.
The separate context filter was designed **after inspecting those development
outputs**. Both releases remain preserved; this is explicitly exploratory adaptation,
not an independent confirmation. Context word overlap can still be incidental.

## What improved and what did not

- Retrieval is no longer restricted to the old ranked packet or forced top-one.
- Additional subject and domain evidence makes candidates inspectable.
- 2,909 cards still have no extracted subject; these remain coverage gaps, not
  discarded markets or certified irrelevant contracts.
- New candidates have not passed predicate, period, resolution-source or historical
  metadata validity checks. More retrieved pairs do not establish better precision,
  recall, useful news coverage or predictive value.
- Only 25/160 articles retain candidates; news/contract universe overlap remains a
  plausible limitation, not something this unlabelled check can quantify reliably.

## Next work

Use retained development candidates to distinguish relation/period extraction gaps
from incidental subject mentions. Prioritize generic relation extraction with exact
evidence for those observed contract types, while keeping retrieval and acceptance
separate. Inventory the 2,909 uncovered cards before expanding adapters. Do not
request bulk labels, relax certification, or train news models from this release.
An independent accuracy audit requires a stable acceptance policy and credible yield.

## Evidence and reproducibility

- `eventx/v6/subject_retrieval.py` and `eventx/v6/subject_context.py`
- `eventx/tasks/check_subject_retrieval.py` and `check_subject_context.py`
- `data/v6/subject_retrieval_20260917/`: selection receipt, subject registry, article
  coverage, candidates, report and output hashes.
- `data/v6/subject_context_20260917/`: receipt, all filtered decisions, report and hashes.
- 16 new synthetic tests pass (10 retrieval and six context); previous 97 passed
  alongside retrieval tests in this task. No frozen earlier implementation was edited.
- Runners refuse to overwrite existing output directories.
