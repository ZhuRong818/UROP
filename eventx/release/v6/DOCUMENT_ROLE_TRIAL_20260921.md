# Document-role follow-up: development only

Separate implementation: `eventx/v6/document_roles.py`; replay task:
`eventx.tasks.trial_v6_document_roles`. Previous code and artifacts unchanged.
Evidence: `data/v6/document_role_trial_20260921/` (cards, scores, changes, report,
manifest). All input/output hashes verified; 37 targeted tests pass, including
12 new synthetic regressions/variants. No independent accuracy estimate.

Explicit team-role/action patterns now permit headline/summary context sharing.
Local asset-object/property patterns replace arbitrary sentence-level buy/price
cues. Evidence offsets preserved. These are bounded heuristics, not a general
coreference model. Identical query/article inputs allow exact reuse of earlier
neural scores: no new neural run, API access, audit labels or predictive training.

## Fixed 185-pair / 70-article results

| Metric | Previous | New |
| --- | ---: | ---: |
| Context hypotheses | 34 | 25 |
| Asset / event pairs | 32 / 2 | 22 / 3 |
| Abstentions | 151 | 160 |
| Articles / contracts with hypotheses | 8 / 12 | 7 / 9 |
| Predictive admissions | 0 | 0 |

Two pairs added, eleven removed. All changes inspected:

- 152232532: Mexico host-country match removed; Iran team context retained.
- 201756152: six Bitcoin threshold hypotheses removed. “Buying Time” no longer
  counts as literal asset buying; this does not establish that the whole article
  lacks contextual information.
- 211869183: two Argentina contexts recovered (World Cup win and semifinals),
  using summary team-win evidence plus headline World Cup context. Exact fixture,
  stage and date remain unverified; the differently phrased final question remains
  unsupported. These are not certified outcome-specific links.
- 102500031: four Bitcoin investment-thesis hypotheses lost (“39 Trillion Reasons
  To Buy”). Potential recall regression: local-action grammar misses investment
  opinions. Preserve this failure rather than claiming unqualified improvement.

Fewer hypotheses is not an accuracy metric. Document sports context can still refer
to a different event; grammar is incomplete and no independent links are admitted.
Source/version/family/inference gates remain unchanged.

Next: bounded contrastive inventory across action, opinion, logistics and event
stage, then complete field-aware/neural evidence-binding and retrieval comparison.
Avoid repeated single-headline regex exceptions. Complete the support ledger before
fresh annotation or predictive training; retain all prior failures.
