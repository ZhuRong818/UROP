# Exploratory observed-news offset trial — 9 October 2026

## Question and scope

At the user's request, this run shows a forecasting result before the historical
V6 source-support gate is closed. It uses **already opened V5 development data**,
not the 8,844-day V6 support ledger, a consumed holdout, or the frozen V4
prospective interval. Only rows with at least one **observed** article in the
previous 30 minutes are evaluated. Unobserved or missing feed windows are not
interpreted as zero news.

## Method

The reference is the frozen, market-only `tree_no_terminal` out-of-fold
probability from the V5 algorithm audit. The new models fit a logistic correction
with that probability's logit fixed as an offset, using exposed rows only.
The correction intercept is unpenalized; standardized coefficients have a fixed
L2 penalty of 0.01. Three progressively larger arms were specified in
`data/v5/opened_news_offset_trial_20261009/contract.json` before this run:

| Arm | Correction features |
|---|---|
| Context | Baseline logit; the observed-article gate controls where correction applies |
| Timing | Context plus recent article count and latest article age |
| Semantic | Timing plus maximum and latest relevance × novelty scores |

Fold 4 is predicted from exposed fold-3 rows; fold 5 from exposed folds 3–4.
Both fits purge labels crossing the validation boundary and keep market IDs
disjoint. The evaluation contains 9,965 observed-article rows, 219 markets and
1,447 positive labels. No hyperparameter was selected on these validation
outcomes, and no model was promoted.

## Result

Lower log loss and Brier are better; higher average precision is better.

| Model on identical observed-article rows | Log loss | Brier | AP |
|---|---:|---:|---:|
| Market-only tree | 0.330591 | 0.107047 | 0.373627 |
| Context correction | **0.327533** | **0.105861** | **0.374094** |
| + news timing | 0.327942 | 0.105982 | 0.372586 |
| + relevance–novelty | 0.328787 | 0.106183 | 0.373029 |

The context correction improves log loss over the market-only tree by **0.003058
nats/row**, positive in both forward folds (+0.004507, +0.001828). Its
descriptive market-cluster interval is [0.000662, 0.005552]. This is a gain
from **exposure-gated recalibration**, not evidence that article content adds
predictive value.

Adding article timing to the context correction changes log loss by **−0.000410**
in the improvement direction; adding relevance–novelty to timing changes it by
another **−0.000844**. The full semantic arm is **0.001254 nats/row worse than
context**. The semantic-versus-timing fold differences are −0.002416 and
+0.000491; its descriptive market-cluster interval [−0.002080, 0.000199]
includes zero. Although the semantic arm is 0.001804 better than the uncorrected
market tree, it does not beat the matched context control.

## Interpretation and limits

The result is a real numerical comparison on opened historical labels and a
strong market-only baseline. It does **not** establish incremental news-content
lift. The article corpus used for historical relevance–novelty representation
was fitted with later development text. Feed completeness, exact article and
market versions, event-family independence and upstream eligibility remain
uncertified. The market bootstrap is descriptive and does not account for
model search, shared event or calendar shocks. The observed-article subset is
small and selected by the available feed; it does not estimate performance on
all market times or on truly news-free times.

Preserve this failed incremental-content comparison. Do not choose a different
penalty, threshold or subset based on these validation outcomes and call it
confirmation. The V4 prospective protocol and the V5-R future design remain
unchanged. Exact metrics, paired differences, folds, predictions, input hashes
and code hash are in `data/v5/opened_news_offset_trial_20261009/`.
