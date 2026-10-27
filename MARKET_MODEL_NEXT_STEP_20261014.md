# EventX next-step results — 14 October 2026

**The current uncalibrated `condition_120k` model remains the development choice.** Fixed feature ablations support the added market-condition features. Global calibration selected on an earlier period worsens later performance. A broader macro-driver retrieval diagnostic also fails to recover a sufficiently informative later news sample.

## Feature-group ablations

The same training samples, random seed, tree settings, labels and forward splits were used for each ablation. Five removed groups × two folds produced ten new booster fits. The full model and same-size model without all nine extras reuse the canonical prior predictions. No ablation variant was selected from fold-5 scores.

| Feature group removed | Fold-4 increase in log loss | Fold-5 increase in log loss |
|---|---:|---:|
| All nine added condition features | 0.002914909917 | 0.001676059555 |
| Volatility ratio + three scaled momentum features | **0.001830314738** | **0.001156422153** |
| Short-versus-long momentum contrast | 0.000050355392 | 0.000197615990 |
| Trade-count and notional intensity ratios | 0.000538723467 | 0.000052425447 |
| Age–volatility interaction | 0.000037106148 | 0.000014804943 |
| Price uncertainty p(1-p) | 0.000160012282 | 0.000091078529 |

Positive values mean removing the group worsens loss. Every group is helpful in both development folds; volatility normalization produces the largest ablation difference. This supports retaining the feature set for this model. Correlation between features and changes to tree splits mean the differences are not additive or causal contributions.

## Calibration result

Identity, temperature scaling and monotonic Platt scaling were compared on a chronological 70/30 split inside fold 4, with a 30-minute purge. Calibrators fit on 72,462 earlier rows; 29,339 later rows selected the lowest log loss subject to Brier no worse than identity. The selected method was receipted before computing its new fold-5 forecasts, then refitted on all fold-4 predictions. The entire cycle remains adaptive opened development.

Platt scaling improved inner-validation log loss from **0.4352844371328941** to **0.43381098279636127**. It did not transfer to fold 5:

| Metric | Raw selected model | Selected Platt calibration |
|---|---:|---:|
| Log loss ↓ | **0.3429489298145635** | 0.3434057612588951 |
| Brier ↓ | **0.10905976503729453** | 0.10916166136368204 |
| Average precision ↑ | 0.3462485264100695 | 0.3462485264100695 |
| Descriptive ten-bin calibration error ↓ | **0.0057061809802710015** | 0.010697457050824316 |
| Mean forecast probability | 0.14165043209623474 | 0.1567520336024854 |
| Observed movement rate | 0.14607160616608653 | 0.14607160616608653 |

Later loss worsens by **0.00045683144433161793 nats/row**. Platt's positive monotonic transformation preserves ranking, so AP is unchanged. Its fitted slope is 0.9784104138944288 and intercept 0.10692884431528815. The correction raises probabilities too much in the later population; this is evidence of limited calibration transport, not a reason to choose another calibrator after inspecting fold 5.

Condition diagnostics show calibration is heterogeneous: loss worsens on the 46,519 freshest-price rows by 0.0017259685304193417 nats/row, but improves on the 30,648 rows with price age 15–30 minutes by 0.0009254268093167872. It also worsens in the higher-activity bins. These are post-result diagnostics, not a selected rule for deployment.

## News recovery and event yield

A separate fixed headline retrieval searches the existing candidate links for employment, payroll, CPI/PCE, consumer/producer-price, inflation and retail-sales coverage associated with Fed contracts. It preserves availability and existing 30-minute forecast keys. Country/report identity and material relevance remain unreviewed. Articles are selected by text and time only; movement labels are used afterwards for descriptive coverage counts.

| Fold | Candidate articles | Covered decision rows | Large movements | Non-movements |
|---|---:|---:|---:|---:|
| 1 | 12 | 113 | 28 | 85 |
| 2 | 10 | 96 | 26 | 70 |
| 3 | 0 | 0 | 0 | 0 |
| 4 | 7 | 39 | 6 | 33 |
| 5 | **1** | **4** | **0** | **4** |

Thirty distinct candidate articles have coverage across all folds, but only one appears in the latest fold. That article's publication-to-system lag is **128.77799461666666 minutes**. No later article from this retrieval is available within 30 or 60 minutes of publication. The packet contains no movement outcome labels and was not sampled to favor movement cases.

This extends retrieval beyond explicit policy decisions but does not fix later sample yield. Positive movement coverage exists in earlier folds; moving those observations into the later reporting fold would change the experiment rather than provide independent confirmation. No macro-driver forecast was fit.

## Research decision and next priority

Keep the raw selected booster as the strong development baseline. Its condition features have consistent ablation support, while the tested global calibration lacks later transfer. A future calibration experiment should explicitly model differences by trade age/activity and use a new earlier selection design; the current subgroup observations are hypotheses, not confirmed rules.

For news, the main problem remains obtaining distinct information arrivals overlapping sufficiently active markets in the reporting period. Improving retrieval alone did not supply both outcome classes. Plan a separately defined observable event cohort and independent relevance/episode review rather than widening historical splits or selecting articles because a movement followed them.

The previous fixed latest-market/news comparison remains in [the continuation report](MARKET_NEWS_CONTINUATION_20261014.md). V4 retains its original frozen protocol and collection window; consumed holdouts were not accessed. No calibrated or ablated candidate was promoted.

## Artifacts

- [Ablation/calibration results](data/v5/market_ablation_calibration_20261014/report.json)
- [Calibration selection receipt](data/v5/market_ablation_calibration_20261014/calibration_selection_receipt.json)
- [Calibration and ablation predictions](data/v5/market_ablation_calibration_20261014/predictions.npz)
- [Macro-driver coverage report](data/v7/macro_driver_recovery_20261014/report.json)
- [Outcome-hidden later candidate packet](data/v7/macro_driver_recovery_20261014/REVIEW_PACKET.md)

Checks confirm the later probability metrics, monotonic-ranking equality, parent-row sampling/parameters, persisted prediction keys and source/output hashes. No new software tests were added or run; these were opened research fits and artifact checks. No source fetch, protected evaluation or live deployment occurred.
