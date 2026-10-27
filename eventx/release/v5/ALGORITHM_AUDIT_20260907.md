# EventX algorithm audit — 7 September 2026

Status: code review and exploratory model comparison complete.

This audit was explicitly requested by the user, including alternative models and
methods. It is a separate exploratory research artifact on already opened May–July
development data. It is not the proposed V5-R one-shot new-data experiment and does
not amend a frozen v4 artifact. No consumed holdout is rerun.

## Findings

### 1. Historical semantic preprocessing uses future development text

`prepare_v4_discovery_news_quality.fit_semantic_model` fits TF-IDF vocabulary/IDF and
SVD on the complete discovery corpus before building all historical folds. The
per-event novelty history itself uses prior articles, but its representation was
learned using later articles. This is unsupervised temporal preprocessing leakage
in historical OOF evaluation; label blindness alone does not remove it.

The v4 future confirmation uses a representation frozen before that interval, so this
finding does not itself invalidate the future evaluation. Historical semantic results
need the limitation disclosed. A future cycle must fit its representation inside each
training partition or use a separately dated, previously frozen representation.

### 2. Earlier residual experiments optimize another objective

`run_v5_residual_feasibility_v2.fit_converged` fits ordinary penalized logistic
regression to labels. `tune` then subtracts the baseline logit from this model's
decision function and shrinks the difference. This is a blend of a standalone expert
and the baseline, not penalized logistic loss with a fixed baseline offset.

The penalties differ: a genuine offset fit penalizes the correction; the old fit
penalizes a complete prediction rule. Including baseline probability as a freely
weighted predictor also permits its coefficient to change. Thus the old experiments
do not establish that the proposed true-offset residual architecture has failed.

The new audit includes a fixed-offset objective, analytic-gradient check, and a
synthetic calibrated-baseline test demonstrating this distinction. That test is a
numerical verification, not a fitted empirical residual-model result.

### 3. Terminal metadata are not joined as of prediction time

`run_v5_residual_feasibility.terminal_metadata` maps one terminal value per market
to all its rows. It checks terminal time against first trade time but never checks
metadata ingestion against each prediction timestamp. Of 745,443 opened OOF rows,
425,425 precede the recorded ingestion of their market metadata; no metadata ingestion
timestamp is missing.

This is an availability-proof gap, not proof that every deadline was unknown publicly
at that time. However, under the conservative Lumid clock, those values cannot be
asserted to have been observable without earlier provenance. Snapshot terminal times
may also be revised. The comparison includes a no-terminal variant for every model.
Future builders need versioned as-of metadata; removing the feature alone does not
repair any earlier use of metadata in eligibility, taxonomy or associations.

### 4. Historical meta-model partitions omit a horizon purge

The original v4 base-model split explicitly purges 30 minutes. The later v5 selection
and ablation code uses only `oof.fold < outer_fold`. It admits 483, 231 and 286 earlier
rows whose label horizons touch or cross the temporal boundary for folds 3, 4 and 5.
These are different held-out contract groups, so this count is a protocol mismatch
and possible shared-event leakage risk, not evidence of duplicate target rows.

The audit comparison explicitly requires `training_minute + 30 < validation_start`
in both inner and outer splits and checks market-ID disjointness.

### 5. OOF is not a complete guarantee of nested market separation

Stored baseline probabilities exclude their own validation market group. A baseline
that produced an earlier meta-training row can nevertheless have trained on earlier
observations from the later outer-held-out group. Reusing one global OOF vector does
not enforce strict outer-market exclusion at every level. Rebuild base cross-fits
inside the outer partition for any future stacked model.

The new direct-model comparison does not feed prior base predictions into learners.

### 6. Market groups do not identify independent event families

The builder computes `sha256(venue:market_id) % 5`. This separates contracts but does
not establish separation of related outcomes/contracts driven by one event. No verified
event-family identifier is present in the prepared market index. Future cross-market
claims need semantic event-family grouping and uncertainty that accounts for common
calendar shocks.

### 7. Earlier baseline improvements do not isolate architecture alone

The direct nonlinear selection task trains on earlier stored OOF rows. Its linear
reference is produced by another task trained on the larger original example pool,
with a different optimizer and feature treatment. Evaluation rows align, but the
reported direct-versus-linear difference is not a controlled nonlinearity-only ablation.
The new audit uses identical training indices and evaluation rows across model families.

### 8. The proposed news contrast combines timing with semantics

V5-R adds count, age and relevance–novelty, while C5-R contains only market context.
Beating C5-R would support that combined feature block; it would not isolate novelty.
The audit compares market → market plus exposure/count/age → the same inputs plus
relevance–novelty. Even the final contrast isolates the combined quality representation,
not novelty separately from relevance.

## Alternative-model experiment

The immutable pre-fit contract is saved in
`data/v5/algorithm_audit_20260907/contract.json`.

- Model families: converged L2 logistic regression, quadratic quantile-spline logistic
  regression, and shallow histogram gradient-boosted trees.
- Four input bundles per family: market without terminal, market with terminal,
  market plus recent-news timing, and timing plus relevance–novelty.
- Two inner-tuning configurations per family: C=0.01/0.1 for logistic models;
  100/200 boosting iterations with depth 3, seven leaves and strong regularization.
- Three forward outer folds (3–5), with the previous fold used for inner validation;
  30-minute purging and disjoint market identifiers at both levels.
- Deterministic uniform training/tuning caps of 60,000 rows; all outer validation
  rows retained. Results must not be directly ranked against earlier full-data runs.
- All preprocessing/caps learned on training rows; tree random early stopping disabled.
- Outcomes: log loss, Brier, AP, fold consistency, news-exposed and fresh-price subsets.
- Market-cluster bootstrap intervals are descriptive and unadjusted for the exploratory
  model search or common calendar shocks.

Inherited semantic embeddings and terminal metadata retain the limitations above.
Accordingly, this run cannot confirm incremental news value even if a comparison wins.

## Implementation evidence

- `eventx/tasks/audit_v5_algorithms.py`
- `eventx/tasks/test_algorithm_audit.py` — four synthetic checks passed before fitting:
  window boundaries/future invariance, temporal purge, offset gradient/objective,
  and training-only clipping.
- scikit-learn guidance on preprocessing leakage:
  https://scikit-learn.org/stable/common_pitfalls.html
- Histogram boosting configuration reference:
  https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html

## Completed model results

The run completed 108 fits (72 inner-tuning fits and 36 final fits) across three
outer folds. All final fits converged. Evaluation used 364,903 opened rows across
1,135 contracts, including 11,366 rows exposed to news in the last 30 minutes (3.11%).
Training and inner-tuning samples were capped at 60,000 rows with identical indices
across model families. These are algorithm-screening results, not a full-data rerun
of earlier baselines or a prospective V5-R result.

Lower log loss is better:

| Model family | No terminal inputs | Market | + exposure/count/age | + relevance–novelty |
|---|---:|---:|---:|---:|
| L2 logistic | 0.451070 | 0.448075 | 0.448139 | 0.448209 |
| Spline logistic | 0.425681 | 0.423706 | 0.423682 | 0.423749 |
| Shallow boosted trees | 0.407391 | 0.405075 | 0.405099 | 0.405099 |

The tree market-only model improved over the matched linear model by 0.043000
nats/row; the descriptive market-cluster interval was [0.039091, 0.046615]. Its
improvement was positive in all three folds. Brier was 0.130304 and AP was 0.343664,
versus 0.139952 and 0.245453 for the matched linear baseline. This effect persisted
without terminal inputs: tree log loss 0.407391 versus linear 0.451070.

Adding semantics on top of the timing control produced:

- Linear: -0.00006960 log-loss improvement overall; -0.00244427 on exposed rows.
- Spline: -0.00006686 overall; -0.00279161 on exposed rows.
- Trees: exactly identical predictions for timing and semantic variants on all
  evaluation rows. This is a model-specific failure to extract an incremental signal,
  not an information-theoretic null result.

The news timing block alone had no stable improvement: linear -0.00006490,
spline +0.00002370, tree -0.00002347; all three descriptive intervals included zero.

Additional interpretation limits:

- The inherited sparse representation, training subsampling and strong tree
  regularization can miss heterogeneous news effects. No claim about all possible
  semantic models follows.
- The training 99th-percentile article-count cap was 1 in every final fit. Thus the
  capped count duplicates the binary exposure signal. Future protocols must explicitly
  choose an all-row or exposed-row quantile before labels; this run is preserved as-is.
- Every evaluated row already satisfied price age <=30 minutes, so the requested
  <=30-minute freshness diagnostic is identical to the full sample and provides no
  additional robustness evidence here.
- Quantile splines with sparse inputs need their effective basis checked before
  treating nominal coefficient counts as equal model capacity.
- The no-terminal comparison removes terminal predictors only; it does not establish
  that upstream eligibility and news associations avoid snapshot metadata.

## Decision and required repairs

1. Preserve all historical and v4 frozen artifacts. Disclose historical preprocessing,
   metadata and nested-split limitations when reporting their discovery metrics.
2. Keep shallow boosting as a promising **exploratory market baseline**. No automatic
   replacement of B0-v5N and no news candidate promotion follows from this run.
3. Before future V5-R execution, enforce as-of semantic fitting and versioned market
   metadata, including eligibility and associations; add a 30-minute horizon purge
   at every training level and verified event-family grouping where claims require it.
4. Implement and test actual penalized fixed-offset training, with base probabilities
   rebuilt inside each outer fold. The synthetic offset test passed, but this audit did
   not empirically fit the full proposed residual model.
5. Include an exposure/count/age control before attributing incremental gains to
   relevance–novelty; novelty-specific claims require holding relevance constant too.
6. Freeze any resulting new architecture/version before an independent data test.
   The user-authorized exploratory comparison does not consume V5-R's new-data test.

Primary machine-readable evidence:
`data/v5/algorithm_audit_20260907/report.json`, `contract.json`, `predictions.npz`,
and `manifest.json`. The report preserves every tuning configuration and fold result.
