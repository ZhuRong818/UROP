# Review of benchmark and v8 development changes

2 November 2026, Singapore. Assessment of current sources, committed protocols, logs and stored
completed results. No models trained, forecasts rescored, evaluation rerun, job altered or data fetched.
The process snapshot below is a review-time observation, not continuous monitoring.

## Assessment

These changes improve comparator breadth and turn earlier suggestions about pooling and adaptation
into testable model contrasts. The benchmark has high empirical value; v8 has useful development value
but does not yet add independent confirmation. Neither implementing recent models nor combining an
online logistic offset with boosting by itself establishes algorithmic novelty.

The strongest paper narrative now rests on completed tests, rather than the older June-only claim:

- History stack, June29–July12: LL0.3347989321486162 versus online rate0.38634564594943877;
  gain0.05154671380082259, two-way CI[0.03371463224384839,0.07127478599953387],51contracts.
- July13–21 segment confirmation: moved30 interaction0.11275672970529926 and wide-spread interaction
  0.0909208084441327; both Holm p0.0003999200159968006. Unchanged stack gain over rate
  0.03902781085607166, two-way CI[0.028139468272235867,0.051226434119458875].
- July22–August8 segment stack: LL0.3006201453003797 versus linear stack0.30826222200851733;
  gain0.007642076708137644, two-way CI[0.0023096333470807376,0.01382594474309573],52contracts.

Read the three completed consumption receipts before these result summaries. Sources are respectively
`data/v7/{history_stack_20261031,segment_confirm_20261101,segment_stack_20261101}/test/evaluation/`.
These checks do not redo full manifest/source audits. Preserve capture/missingness limitations and the
disclosed calendar-overlap deviation for the last test; the scores are not unrestricted deployment claims.

## Current execution evidence

Read-only process listing initially failed in the sandbox; the approved external check found TierC
PID24822 and v8 PID73522 running, TabICL/CatBoost37362 and Sundial18412 stopped/paused, and sequence
driver63989 sleeping. Orphan IDs92286/13327 were absent. No process was stopped or resumed here.
Moirai-MoE has seven output files; TabM and RealMLP each have seven TierA files. Sundial has one block;
TierC has no output yet. Benchmark result.json and v8 result.json were absent at inspection. v8's log
had two completed folds (May13–19 and June1–7), both outside its five-new-block selection score.
Finishing forecast files is not a scored comparison. Historical swap figures were not remeasured.

## Benchmark: useful, with explicit limits

1. **TierA is the cleanest model-family comparison:** same18features and9,212source training rows.
   TabM/RealMLP/TabICL/CatBoost provide relevant modern alternatives. However defaults are not matched
   tuning, and the wrappers do not pass chronological validation indices. Installed pytabkit defaults
   to a random internal split (sklearn_base.py, RandomSplitter), so neural epoch selection uses a
   different internal validation design from purged forward validation. This is not evidence of test
   label leakage, but report effective fit/validation rows and avoid claiming identical training procedures.
2. **TierC is resource-constrained, not matched-data superiority:** the amendment caps neural models
   at100,000random training rows while seg_hgb used all six blocks. Describe this as a bounded-resource
   benchmark. A future equal-data control would be needed to isolate learner performance.
3. **TierB tests one adaptation:** means/point forecasts from general time-series models are clipped
   into binary probabilities. This is a usable heuristic, not their native calibrated Bernoulli objective.
   Moirai uses missing masks; Sundial/Time-MoE use context-mean imputation. Their288-grid context differs
   from the cumulative online rate. Report these choices, fallback fractions, clipping and matched
   nonoverlap rows. Failure here would not demonstrate that foundation models generally cannot help.
4. Report memory/inference cost alongside scores if resource constraints are part of the motivation.
   Preserve all models/results and missing outputs; compute failure is not predictive inferiority.
   Benchmark CIs currently cluster contracts only; seven block wins are not seven independent studies.

TabM's published contribution supports its relevance as a strong tabular reference, not automatic
superiority on this task: [ICLR2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/c1ba41c694834aeef91ae161711d4939-Abstract-Conference.html).
Moirai-MoE targets broad time-series forecasting: [paper](https://arxiv.org/abs/2410.10469).

## v8: good comparisons, still exploratory

- `e2e → e2e_hx → e2e_hx_mkt` separates added history summaries from cross-contract activity under
  fixed learner settings. `pp_cp_seg` versus `seg_ref` is particularly useful because it isolates the
  specified online correction on the same refitted base predictions. `pp_cp` should also be contrasted
  directly with `e2e_hx_mkt`, its own uncorrected base, not only with seg_ref.
- LOBO fits every other block, including later dates for six of seven folds. It measures retrospective
  block generalization, not a deployable rolling forecast. Only the last fold trains strictly earlier,
  and that block was already opened before designing v8. All remain development evidence. Do not choose
  a winner from the two completed early folds or call the block-average selection score confirmatory.
- The posterior respects the t'<=t−2100maturity cutoff in source inspection. It is an approximate online
  logistic random-intercept filter, with fixed prior variance1 and process noise0.02/hour. Parameters
  exist even though no additional offline tuning is done. Overlapping labels are not independent
  Bernoulli observations, so posterior variance should not be sold as calibrated uncertainty.
- The change-history inputs are Hawkes-inspired decay/count summaries, not a fitted Hawkes intensity
  model or a likelihood-based point-process model. Their events are five-minute endpoint changes;
  within-grid reversals and unavailable grids are not fully observed event arrivals.
- Dynamic Bayesian logistic modelling has longstanding precedent. Position novelty in task-specific
  design and validated evidence unless a literature comparison establishes a distinct methodological
  advance. See [West, Harrison and Migon1985](https://www.tandfonline.com/doi/abs/10.1080/01621459.1985.10477131)
  and [dynamic logistic regression](https://pmc.ncbi.nlm.nih.gov/articles/PMC3831847/).
- Market activity is activity among the available block contracts, not a market census. Specify the
  live observable universe, simultaneous availability and cost before claiming deployability.

## Integrity, reporting and next actions

Commits5cc784f and9d32708 contain the protocol and added candidate; the working v8 script has no diff
against HEAD. The stopped first-run log is empty, consistent with no printed fold score but not proof
that no internal computation occurred. Retaining it and declaring amendments is appropriate; these
are development choices, not a reason to relabel opened data as untouched. Timestamp corrections before
scores are reasonable, but should have a small synthetic causal-time regression check in a later revision.

Concrete reporting/implementation issues to address without silently changing the running experiment:

1. v8 docstring says2,000bootstrap draws; imported `one_way` uses module-global B=5,000. Document the
   actual5,000 and the discrepancy, preserving this run. No evidence here that the numeric calculation fails.
2. v8 outputs log loss only; the current script does not supply Brier/AUC/calibration, all-issued missing
   bounds, two-way intervals or an aggregate selection-adjusted CI. Do not imply those checks passed.
3. Builder§2.6 still says Sundial/Time-MoE were excluded; amendments and running jobs supersede that.
   Its blanket dismissal of older MLPs is also too strong: RealMLP itself is an MLP with strong defaults.
4. Before the once-only evaluator, verify all expected files/keys exist. The sequence driver waits for
   process exit, not successful completion; v3 evaluate calls v1 evaluate before checking all B2 outputs.
   A failed late merge could therefore leave a partial result. This review did not invoke the evaluator.
5. Current-state historical commands contradicted completed close-out/new-cycle facts. Marked old runtime
   sections historical and replaced obsolete Next actions; retained a pre-edit handoff snapshot.
6. Use§6.10for the descriptive benchmark and§6.11for development, with evidence-class labels in Table1.
   Lead abstract/conclusion with completed historical confirmation, not a v8 winner or unfinished benchmark.
   Put detailed search/configuration/history in appendices; retain failed runs and compute amendments.

Recommendation: finish the existing benchmark and development run, then report their complete outcomes
without opportunistic expansion. Any selected v8 model needs a new frozen test. Keep the existing frozen
segment stack as the confirmed reference. November logging is correct; no PROGRESS.md pointer is needed
for the scientific assessment, and none was added.
