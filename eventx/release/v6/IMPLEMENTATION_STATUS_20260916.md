# EventX V6 — adopted design, first implementation milestone

Date: 16 September 2026. User authorized proceeding with the separate proposal.
Status: **design/build stage; no research freeze or forecast evaluation**.

Design reference: `eventx/release/v5/EXPERIMENT_REDESIGN_PROPOSAL_20260915.md`.
Its original proposal-only status and hash are preserved as historical evidence.
This record documents adoption; it does not overwrite V5 v1.1 or V4.

## Implemented and run

Release: `data/v6/contract_link_pilot_20260916/`.

| Artifact | Result |
|---|---:|
| Contract cards | 4,651 |
| Named YES subtitles retained | 4,546 |
| Cards with recovered rule text | 43 |
| Single-event candidates, still unverified | 4,254 |
| Known combo parents, separate extension | 397 |
| Explicit parent/leg evidence records | 1,752 |
| Opened-discovery article sampling population | 148,543 |
| Articles selected | 200 |
| BM25 top-50 candidate pool | 9,911 pairs |
| Unlabelled development review shortlist | 1,199 pairs |

Structured BM25 uses question, YES subtitle, event title and available retrospective
rule evidence. This is a lexical retrieval baseline, not dense embeddings or a
cross-encoder. No claim of improved link accuracy is possible before annotation.

Cards distinguish contract IDs, candidate event IDs and provisional split groups.
Explicit dependency edges retain original line references and parent/leg polarity;
they do not modify existing family graphs. Entities, dates, metrics and resolution
sources remain null where no validated extraction exists. Token mappings are not
invented; the parser is implemented and tested but this release has no verified
mapping inputs. Rules available only retrospectively stay review-only.

The predictive-text API rejects every currently uncertified card. A future explicit
certificate must cover the exact representation hash, availability and half-open
validity interval. A certificate is evidence, not a field to toggle to bypass review.

## Pilot sampling and interpretation

Seed 20260916 selects 200 articles uniformly without replacement from the existing
clock-consistent discovery inventory. Only whitelisted source lines are decoded;
article identity and exact headline/summary hashes are checked before use.
No new source data were fetched.

For each selected article, retain up to 50 BM25 contract candidates among the 4,254
non-combo candidates. Shortlist up to five highest-ranked contracts and one uniform
contract outside that top-50 pool. One article has fewer than five positive-score
candidates, so the shortlist has 1,199 rather than 1,200 pairs. Do not pad with
fabricated matches. Sampling probabilities and stratum membership are in the
separate selection ledger; reviewers should not see it or the scored pool.

This is **retrospective development material**, not the proposal's final 600/600
event/story-disjoint audit. It samples article–contract pairs; event-level review
and shared story grouping are still required. Contract status is not certified at
article arrival, so candidate retrieval is not a simulation of active-market PIT
matching. Reviewers must flag temporal/identity incompatibility.

Raw precision on these enriched pairs would not estimate overall population
precision. Rank 6–50 pairs are not annotated by this shortlist; the probability
ledger does not repair that support gap or establish recall. No acceptance threshold
may be evaluated on these development labels as though they were held out.

## Review rules

Review `development_review_packet.jsonl` independently before seeing another
reviewer's labels. Keep separate response copies and preserve pair IDs. Do not
share `selection_ledger.jsonl` or `retrieval_pool.jsonl` with reviewers.

- `direct`: article contains evidence bearing directly on the specified event,
  measurement, time period and contract proposition. It need not support YES.
- `background`: relevant context, but not direct evidence for that event/period.
- `unrelated`: wrong entity/event/date/stage, or merely similar vocabulary.
- `abstain`: insufficient or conflicting contract/article evidence.
- `outcome_applicability`: `yes_proposition`, `event_only`, `not_applicable` or
  `uncertain`. This describes specificity, never the observed settlement result.
- Include quoted evidence spans and explain `identity_problem` when present.
  Leave missing facts unknown rather than expanding ticker abbreviations by guess.
- Record a real reviewer identifier. Automated retrieval output is not a review.

Two independent reviews plus adjudication are required for final audit labels.
No human labels have been generated in this task.

## Remaining implementation order

1. Recover more Polymarket descriptions and exact outcome/token mappings; resolve
   historical validity separately from retrospective semantic review.
2. Check this pilot's relevance and identity failure modes. Implement dense retrieval
   and local cross-encoder candidates with model provenance; retain BM25 and legacy
   lexical comparators. No forecast-outcome tuning.
3. Group stories and events, then publish a separate disjoint held-out link audit,
   independent recall-search tasks and the 300-pair novelty audit. Do not reuse this
   entire development shortlist as independent validation.
4. Reconcile news export/availability, then build the full seven-day novelty index.
5. Validate inference and source admission; freeze M/T/R/N, shared rows, splits,
   baseline selection, capped corrections and one untouched confirmation scope.

No price files, labels or protected outcomes were read; no forecast model was fit.
Existing V4 remains frozen and its reserved interval unavailable to V6.

## Reproduction

```bash
.venv/bin/python -m unittest eventx.tasks.test_v6_contract_link_pilot
.venv/bin/python -m eventx.tasks.build_v6_contract_link_pilot --output /tmp/eventx-v6-pilot-new-version
```

The builder refuses an existing output directory, checks the prior reassessment
hashes, preserves source hashes and publishes from staging. It does not contact an
external model or API. Six unit tests cover namespaces, outcome mapping, named-outcome
retrieval, fail-closed admission, exact version/time checks and deterministic ranking.
