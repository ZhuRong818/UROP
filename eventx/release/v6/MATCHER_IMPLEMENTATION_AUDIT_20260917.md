# Matcher implementation audit — development only

Scope: the 40 opened relevance cases; no reserved labels, new human judgments,
predictive outcomes, model fitting or repeated final evaluation. Canonical diagnostics:
`data/v6/matching_diagnosis_20260917/report.json`, `cases.jsonl`, `FAILURE_ANALYSIS.md`.
Classifications below are assistant interpretations, not independent reference gold.

## What passed

- 40/40 article and contract objects match original pilot artifacts exactly.
- 80/80 embedded reviewer evidence objects match the frozen packet.
- 40/40 pair IDs reproduce the article-ID/contract-ID hash.
- All 40 selected contracts have the maximum stored development-pool reranker score
  for their article and stored rank 1. No observed reversed sort or wrong-ID join.
- All 40 have subtitles; `review_text` includes them and any available rules.
- Local frozen tokenizers show no selected pair exceeds the 384-token reranker
  budget, nor either text the 256-token encoder budget. This does not rule out
  truncation among alternative candidates or elsewhere in the corpus.
- Two cases have tied top scores; no observed non-maximum selection. Numerical
  precision may affect ordering, but these checks do not establish numerical failure.

## Verified gaps and their interpretation

| Finding | Evidence | Interpretation / proposed remedy |
|---|---|---|
| Always chooses a match | Dense top50 and reranked top5; audit top-one has no abstention | Method gap, not a violated frozen specification. Add reject/no-match capability in a new version. |
| Unpopulated semantics | All 40 `semantic_fields` entirely null | Contract cards preserve text but do not implement predicate/entity/time matching. Build evidence-backed structured fields. |
| Sparse resolution evidence | 19/40 have rules, 21 do not | Source/representation limitation. Recover or abstain where interpretation materially depends on missing rules. |
| Missing temporal eligibility | 11/40 articles arrive at/after recorded close | Existing pilot explicitly documented no active-status filter. Incompatible with predictive use; add certified as-of validity, not retrospective guessing. |
| Thin article text | 17/40 summaries blank/missing | Cannot infer absence of relevance in the full article; current experiment observes headline/summary only. Abstain on insufficient supplied evidence. |
| Rank is not acceptance | 33/40 top scores negative | Descriptive only; raw logits are not calibrated contract relevance probabilities. Do not select a zero cutoff post hoc and claim validation. |
| Restricted candidate universe | Development groups come from original BM25 review selections | Valid protocol separation, but coverage limitation. An appropriate contract may be outside that subset or absent entirely. |

Source code inspected: `eventx/v6/contracts.py`, `retrieval.py`,
`eventx/tasks/build_v6_contract_link_pilot.py`, `build_v6_hybrid_audit.py`,
`prepare_v6_hybrid_development_reviews.py`, `freeze_v6_bounded_audit.py`.

No reproducible join, score-direction or selected-input-truncation bug was found
that warrants editing the frozen implementation. Missing acceptance/semantics/time
filters are method extensions, not retroactive bug fixes. Existing code is preserved.
This is not an exhaustive numerical-model audit: no forward-pass reproduction or
dtype comparison was performed. Stored finite scores alone do not prove model quality.

## Failure categories

Primary, mutually exclusive diagnostic categories: 25 wrong entity-or-event,
5 wrong entity, 4 wrong event, 3 predicate mismatch, 2 wrong period and 1 reference
success. Secondary tags include measurement mismatch and background-only coverage.
The two user-closed unresolved cases retain their audit status; diagnostic reading
does not replace their labels. Missing evidence is recorded separately, not inferred
to be the sole cause of a known unrelated match.

Examples: Duluth transcript → United Airlines earnings speech; Banco BBVA Argentina
→ Argentina football; Musk/SpaceX wallet → Musk tweet count; Vail Q1 earnings preview
→ Q3 skier visits. A repeated song contract received eight selected articles; one
AI-model contract received six. This suggests generic fallback attraction, not proof
that the candidate generator contained a correct alternative.

## Retrieval versus ranking

Each case artifact includes the five highest stored candidates and their scores,
explicitly marked unreviewed. We can establish bad selected outputs, but cannot
identify retrieval recall or distinguish a missing correct candidate from a misranked
correct candidate without reference evidence for alternatives. Do not invent a gold
alternative or interpret top5 membership as relevance. No new review queue is opened.

## Important target distinction

Relevance is not settlement entailment. Current Bitcoin price can be relevant to a
future price threshold without proving it will be crossed. A redesigned gate must
reject wrong entities/periods while allowing justified evidence for or against the
future proposition. Requiring the article to quote every threshold would bias the
task toward already-resolved news and undermine the forecasting question.
