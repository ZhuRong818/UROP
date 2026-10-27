# Actions, opinions and event stages: unchanged-method comparison

## Scope and reproducibility

Ran `eventx.tasks.compare_v6_evidence_binding`: nine assistant-authored contrastive
triples (27 synthetic pairs), with scenarios saved in a receipt before inference.
Compared unchanged field-aware v0.1, document-role v0.2, unigram/bigram TF-IDF and
the pinned local cross-encoder. No matcher, threshold or model weights changed.
No outcome, reserved audit or external API accessed. Thirty-seven existing tests
pass; all comparison input/output hashes verified. Zero predictive admissions.

Artifacts: `data/v6/evidence_binding_comparison_20260921/` contains synthetic texts,
expected context roles, exact evidence outputs, raw scores, report, manifest and a
complete 70-article inventory of the existing 185 opened development pairs.

Synthetic expectations are assistant diagnostic judgments, not independent gold.
Scenarios are action (sale, passive purchase, price subject), opinion (thesis,
forecast, valuation), and event-stage (qualification, logistics, semifinal).
Each has one intended relevant context and two wrong relation/entity/episode
contrasts. Old-year sports facts are negatives for the specified current episode,
not proof they could never be background information for a later tournament.

## Comparison

| Category | v0.1 positive hypotheses / 3 | v0.1 negative hypotheses / 6 | v0.2 positive hypotheses / 3 | v0.2 negative hypotheses / 6 | TF-IDF ranking wins / 3 | Neural ranking wins / 3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Actions | 2 | 2 | 2 | 0 | 3 | 3 |
| Opinions | 0 | 0 | 0 | 0 | 2 | 2 |
| Event stages | 2 | 3 | 3 | 2 | 3 | 3 |

Ranking win means the intended positive scores strictly above both contrasts
(tolerance 1e-12). It does not mean the negative scores are sufficiently low to
reject, and is not comparable directly to the binary hypothesis counts. Neither
ranking method has a calibrated acceptance threshold. TF-IDF and neural each win
8/9 here: no demonstrated neural advantage on this small diagnostic.

### Actions: surface syntax remains a limitation

v0.2 rejects the same-asset software-company/furniture and stock-price distractions
that v0.1 retains. Both miss the passive purchase “Ethereum was purchased by a
pension fund.” Neural ranking handles this contrast, but attaching the unchanged
v0.2 hard gate would still discard it. This is a role/voice coverage problem.

### Opinions: missing representation, not evidence of irrelevance

Both rule methods abstain on bullish thesis, expected appreciation and overvaluation.
Neural and lexical ranking distinguish the first two but fail the valuation contrast.
For the neural model, Bitcoin-overvaluation scores -6.8125 while convention-ticket
overpricing scores -6.6875. General semantic similarity does not reliably bind the
valuation to the correct object. Raw negative logits are not rejection decisions.

Real opened examples corroborate inconsistency, not an accuracy rate:

| Article | Evidence | Observed method behavior |
| --- | --- | --- |
| 168034724 | Strategy sells Bitcoin holdings | Action context retained by both |
| 102500031 | Bitcoin bullish investment thesis, reasons to buy | v0.1 retains four pairs; v0.2 loses all four |
| 189518836 | Schiff predicts Saylor's Bitcoin bet will lose | Opinion still retained because `Bitcoin bet` satisfies a surface pattern |
| 152232532 | Mexico hosts Iran team's training base | v0.2 separates host Mexico from team Iran |
| 211869183 | Argentina late win; World Cup in headline | v0.2 combines two evidence spans, but exact fixture/stage remains unresolved |

These five examples were selected from known diagnostics, not randomly sampled.
The retained opinion versus rejected opinion distinction currently depends on
wording, not an explicit account of who believes what about which asset.

### Event stages: role binding is not episode binding

v0.2 retains qualification, team logistics and quarterfinal context, and removes
host-government distractions. It also retains 2022 qualification/quarterfinal facts
against 2026 questions. Neural ranks the correct year higher but by only 0.375 and
0.25 raw-score units; no general margin policy follows from these examples.
Neither implementation supplies a certified current-episode link or distinguishes
historical background from a current event update. Sports-context relevance also
does not establish the championship/semifinal settlement condition.

## Decision and next methodological step

Do not promote either binder or treat more ranking complexity as the solution.
Keep the method versions fixed and use this comparison as a specification for a
general evidence representation:

1. Separate entity/object identity, actor/speaker, action or asserted proposition,
   epistemic status (observed, forecast, opinion), event episode/time and stage.
2. Represent each field with quoted source spans and an unknown/conflict state.
   Passive voice and opinion attribution must not depend on a purchase verb being
   immediately adjacent to the asset name.
3. Compare a structured evidence extractor against existing binders with the same
   inputs. Treat neural output as a candidate explanation, not a certified fact.
   Explicitly separate current-episode updates from historical context.
4. Preserve strict unknown/contradiction handling for identity and episode, without
   excluding all opinions as a class. Keep predictive relevance separate from
   settlement entailment and temporal/source eligibility.
5. Before another independent audit, complete broader opened-data error analysis,
   retrieval/support ledger and a frozen class-specific evaluation policy.

No new regex exception, new annotation request, forecast fit or source admission
was introduced in this comparison. The study is still at development diagnostics.
