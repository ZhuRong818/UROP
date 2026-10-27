# Recovered trading-window reconciliation

The 40 targeted contracts have 438 subject-matched pairs in the fixed 500-article
development sample. Applying recovered opening and closing times gives:

| Recorded window status | Pairs |
|---|---:|
| Before opening | 129 |
| Within [open, close) | 242 |
| At or after close | 67 |

112/438 pairs have metadata ingestion at/before article availability. Only 45 pairs
satisfy both that timestamp check and the recorded trading window. These 45 are
not certified article links: timestamp ordering alone does not validate semantic
versions, source completeness, article relevance or family isolation. Zero admissions.

Inputs were hash-verified and target IDs match exactly. Reconciliation is retrospective,
using unchanged original cards plus separately recovered metadata; no frozen edits.
Evidence: `data/v6/window_reconciliation_20260921/`. 36 existing related tests pass;
runtime checks validate hashes, IDs and open-before-close for matched contracts.

A broader June 1 news probe included primary symbols, related-symbol arrays and
Reddit/SoFi headline mentions. It returned HTTP400 after approximately 30 seconds;
the cause is unverified. No news rows recovered. Receipt:
`data/v5/provenance_recovery_20260908/v6_targeted_news_broad_20260921.json`.
This failure does not establish that data is absent. No protected labels were read.

Next: use existing cached news to establish exact source IDs and symbol conventions,
then query those IDs or smaller indexed source partitions. Keep opening-time checks
in future eligibility versions; do not treat pre-close alone as active-market evidence.
Historical metadata/version certification and association validation remain required.
