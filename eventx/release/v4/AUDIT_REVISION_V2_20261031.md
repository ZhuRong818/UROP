# V4 collection audit revision (v2), 31 October 2026

Status: **disclosed deviation from the frozen holdout implementation**, written and hash-locked before the V4
holdout was consumed and before any V4 label, prediction, prevalence or metric was read.

## What happened

At close-out (2026-10-30 01:57:22Z) the frozen audit `eventx/tasks/audit_v4_confirmatory_collection.py`
(sha256 `4b430894019c20e02120d1626e991bf2e7950f4c746211e9bed6605c58c1cf08`, listed in
`holdout_implementation_manifest.json`) stopped with `non-ok news provenance run` on the first news partition
(2026-08-30). Consume, prepare, build and evaluate did not run. The v1 script is unmodified.

## Why the v1 rule cannot be the intended one

- `run_status` is the status of the upstream news-ingestion run (`provenance.runs.status` joined in each sealed
  partition's SQL), not a property of the article.
- Counted from that column alone, across all 61 sealed news days: ok 74,119; partial 90,630; completed 16,220;
  failed 5,521; running 263 (186,753 rows). Every day has non-ok rows, so v1 could never pass on this collector.
- The September discovery log (`docs/progress/2026-09.md`) recorded the same mix in the discovery news on which
  the frozen V4 models were trained (ok 49,992; completed 3,561; partial 26,892; failed 68,037; aborted 61) and
  concluded these rows "are not automatically invalid articles". No V4 discovery, feature or confirmatory
  prepare/build code filters on run status, so the frozen models and the frozen feature pipeline treat every
  status alike.

## The v2 rule

`eventx/tasks/audit_v4_confirmatory_collection_v2_20261031.py` is a copy of v1 with one change: a news row must
have a recorded run status (any value) instead of status `ok`. Every other check is unchanged: receipts and
hashes, row counts, partition coverage, publication-to-ingest lag within 24 h, ingest at or after run start,
duplicate article ids, and all trade checks. The report records per-status counts, `audit_version` and this
deviation. It writes the same gate path the frozen consume step reads.

Consequence: news features are computed from all sealed articles, as in discovery. The alternative of dropping
non-ok rows would require modifying the frozen prepare step and would make the test data differ from the
training data, so it was rejected.

## Authorization and order

Explicitly authorized by the user on 31 October 2026. Order: write and hash-lock this note and the v2 script →
run v2 audit → frozen consume → prepare → build → evaluate, each once, stopping at the first failure. The
result is reported whatever the sign, with this revision disclosed beside it.
