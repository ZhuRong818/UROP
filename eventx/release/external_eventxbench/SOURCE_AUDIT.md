# EventXBench source audit

Date: 2026-09-07  
Source: `mlsys-io/EventXBench`  
Pinned revision: `0910574b61fba91139086a8b3a714564a652ea79`  
Decision: **conditional auxiliary source; not ready for confirmatory EventX use**

## Scope and leakage boundary

The audit used the full T2 training split and T3 gold audit pool. It read only
tweet IDs, instance IDs, candidate condition IDs and candidate metadata from T2
validation and test. It did **not** access their label or gold-condition fields.
Those evaluation labels remain sealed.

T3 gold grades were opened for this source audit. Consequently, this local copy of
T3 gold is an opened audit/development resource and cannot later be described as an
untouched EventX confirmation set.

The files and repository revision are recorded in the gitignored local manifest at
`data/external/eventxbench/MANIFEST.json`. The reproducible audit implementation is
`eventx/tasks/audit_external_eventxbench.py`; its machine-readable output is
`data/external/eventxbench/AUDIT_REPORT.json`.

## What passed

- All four requested JSONL files downloaded and hash-verified: 78,904,771 bytes and
  8,230 rows before adding the dataset card and loader documentation.
- T2 train contains 543 unique tweets: 402 `LINK` rows and 141 `NONE` rows. All label
  semantics are internally consistent; every `LINK` gold condition is syntactically
  valid and appears in its candidate set.
- T2 tweet Snowflake timestamps agree with explicit `post_created_at` values within
  0.998 seconds. Therefore validation/test tweet time can be reconstructed without
  opening their labels, although external post metadata remains desirable for an
  independent check.
- T2 train, validation and test have zero overlap in tweet IDs and candidate
  condition IDs. Validation and test also have zero instance-ID overlap.
- No validation/test candidate market was created after its tweet according to the
  available candidate metadata.
- T3 gold contains 2,687 unique tweet-condition pairs across 1,364 syntactically
  valid condition IDs, with no missing tweet text or invalid grade.
- The external pairs have zero overlap with the 300 KOL pairs in EventX's cumulative
  opened-pair exclusion ledger.
- Exact ID matching found 619 of the 3,228 distinct external tweets in the existing
  local Lumid KOL archive, spanning 364 handles. This supplies an immediately usable
  author mapping for 19.18% of the downloaded tweet set.

## What failed or remains unresolved

- T2 training supervision is small and mostly non-human: 377/543 rows are
  `dual_model_silver`; only 166/543 are marked `single_human_adjudication`. It is not
  enough by itself to establish production-grade association precision.
- T2 uses a `retrospective` candidate setting. In training, 95 candidate markets on
  54 rows were created after the tweet, including five positive gold links. These
  future-market candidates must be excluded from any point-in-time EventX task.
- The published card calls T2 human-annotated and documents a simple
  `tweet_text`/`market_id` schema, while the downloaded T2 v2 file contains mixed
  silver/human labels and candidate-ranking records. The card and physical data are
  not fully aligned.
- T3 gold is explicitly described by the loader as a rare-grade-enriched audit pool.
  It is useful for conditional grading quality, not for estimating natural pair
  prevalence. Individual A1/A2/A3 grades are absent on 1,200/2,687 rows. Among the
  1,487 complete rows, 727 have exact three-annotator agreement, 1,426 gold grades
  equal the annotator median, and 181 have an annotator spread of at least two grades.
- Only 19.18% of external tweet IDs currently map to the local curated KOL archive.
  The remaining author identities are unresolved without selective metadata recovery
  or the 5.31 GB post-metadata file.
- Condition-ID syntax and internal split separation passed, but pair content accuracy,
  event-family leakage, contract validity at tweet time and population selection bias
  still require independent checks.
- Dataset redistribution and use conditions must be reviewed before committing any
  downloaded row or derived text artifact. All downloaded data remain gitignored.

## Scientific use decision

EventXBench can support a **separately versioned future KOL association development
cycle**. It cannot be inserted into the news-only V5-R experiment, and it does not
reverse the failed KOL-v1/KOL-v2 audits.

The defensible first use is limited to:

1. use T2 train as auxiliary association supervision after removing every candidate
   that did not exist at tweet time;
2. use the already opened T3 gold pool for source diagnostics or development only;
3. keep T2 validation/test labels sealed until the complete association algorithm,
   point-in-time filters and success threshold are frozen;
4. evaluate separately on the 619 locally attributable tweets and report that this is
   a selected 19.18% KOL-covered subset;
5. require an independent manual precision audit on fresh pairs before any KOL model
   becomes eligible for an EventX outcome experiment.

## Next gate

Do not download the 605 MB silver T3 training file or 5.31 GB post-metadata file yet.
First freeze and run a stratified, content-level validation of T2 train covering
`LINK`/`NONE`, silver/human source, similarity score, time ordering and the 619
locally attributable tweets. Continue only if that audit establishes useful precision
and a clear incremental role beyond the existing failed association systems.
