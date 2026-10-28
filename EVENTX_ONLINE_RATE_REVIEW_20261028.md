# Review of the online-rate update and next-cycle proposal

28 October 2026. Review of the report sources, diagnostic implementation, stored JSON and unfrozen
next-cycle specification. No analysis was rerun, model fitted, protected outcome read or research cycle
started. Existing report sources and frozen artifacts were left unchanged.

## Assessment

The update improves the scientific credibility of the report while narrowing its performance claim.
The frozen booster beats the specified fixed references; incremental log-loss value over a simple
adaptive reference remains unestablished. Similar point estimates are not evidence of equivalence.
Persistent contract activity is a plausible explanation, not an identified mechanism.

The earlier publication-gap assessment still applies. Stronger baselines and broader independent
evidence now have even higher priority than a more complex learner. The most useful next question is
whether pooled quote features add information beyond each contract's own causally available history,
and whether that value changes with the amount of history. Neither transfer alone nor standard
boosting establishes algorithmic novelty.

## Evidence checked

Completed June consumption receipts were read before stored result JSON. Ten frozen log losses
(five models in each block) agree with the original evaluation artifacts within 1e-12. All eight new
claims referencing the diagnostic JSON match their artifacts and appear in both sources. The builder
passes `node --check`. This was not a rerun of the full 35-claim or reproducibility suite.

| Quantity | June 1–7 development50 | June 8–14 new identities |
|---|---:|---:|
| Known outcomes / contributing contracts | 16,453 / 18 | 35,218 / 35 |
| Booster log loss | 0.2930988249673845 | 0.4207686547802655 |
| Online-rate log loss | 0.3143108122960961 | 0.4230527841302451 |
| Rate minus booster, nats | 0.021211987328711573 | 0.0022841293499796193 |
| Relative reduction | 6.748729760123189% | 0.5399159243628581% |
| Contract-only 95% interval | [-0.006129649784564764, 0.05742363526062068] | [-0.028285100093127343, 0.03294878629158783] |
| Contract × date 95% interval | [-0.01776025004529445, 0.07318281793350175] | [-0.03960718276617395, 0.04131171734541459] |
| Brier gain, contract-only 95% interval | 0.009364475115383158 [0.0006580515453603057, 0.023126243614858745] | 0.007963945656289224 [-0.0016227952061370072, 0.01784755694405394] |
| Contracts / dates favouring booster | 11/18; 7/7 | 17/35; 3/7 |

Source: `data/v7/dependence_coverage_20261028/result.json`. Both point Brier scores favour the
booster, but the new-contract Brier interval includes zero. These added diagnostics are exploratory.

## Corrections needed in the report

1. **Cold start.** The Markdown says the rate needs matured outcomes while the booster can forecast
   from its first valid quote. In `adaptive_rate`, when k=n=0, `(k+20*g)/(n+20)=g`: the rate forecasts
   immediately using the global prior. It needs matured outcomes to *personalize*. The builder correctly
   mentions lack of history, but presents an untested cold-start performance advantage. Replace with:
   “Both methods can forecast at the first eligible decision. The online rate initially returns the
   global prior and personalizes after outcomes mature; the booster can use current quote features.
   Whether that improves cold-start accuracy has not been tested here.”
2. **Parameter description.** Replace “no fitted parameters” with “no additional offline fit or tuning;
   a fixed pseudocount of 20 and the stored training-derived global prior.” The rate estimates a
   contract probability online and has explicit design parameters.
3. **Mechanism.** The builder contribution says the result “locates much of the advantage” in contract
   activity. Replace this and similar wording with “is consistent with persistent contract activity
   explaining part of the gap; the comparison does not isolate the mechanism.” A similar aggregate
   score does not establish which information the booster uses or why the logistic reference loses.
4. **Uncertainty consistency.** Add the already-computed contract × date intervals against the online
   rate alongside Table 8. Do not call the models equivalent or infer the booster is unnecessary.
   Only seven dates per block inform this calculation, and adjacent-date dependence is not solved by
   independently resampling dates. This is a sensitivity analysis, not certification of all dependence.
5. **Coverage interpretation.** Current metadata locates many unissued grids after listed end dates;
   it does not establish historical closure or a causal explanation for missing coverage. The code
   measures contract-days with no *issued decision*, not days with no valid quote at any instant.
   The builder's “selection therefore does not appear to favour the booster” is stronger than the
   descriptive coverage-tertile comparison supports. Say: “Among issued forecasts with observed
   outcomes, lower contract-day coverage was not associated with a smaller mean gain. This does not
   identify performance on unissued decisions or eliminate selection bias.”
6. **Provenance wording.** No frozen forecasts were regenerated, but a new baseline forecast vector
   was computed retrospectively. Use this distinction in the script docstring, report and progress
   narrative instead of an unqualified “nothing regenerated.” Preserve the historical JSON; clarify
   the scope of `predictions_regenerated: false` in documentation.

## Implementation review and limits

The prefix sums use only same-contract eligible outcomes with decision times t' <= t-2100 seconds.
They pool earlier dates within each block and start each block from the stored global prior. Predictions
are assigned before restricting scoring to endpoint-eligible rows, so the comparison uses matching rows.
The upstream panel constructs the endpoint from states received by t'+1800, with source-age/validity
gates. I found no future-label inclusion in this code path under that historical receipt-time definition.
This does not certify archive/live equivalence or constitute a fresh row-level replay. The reported
300-row brute-force check was not rerun or independently evidenced by a saved check artifact in the
diagnostic output directory, which contains only result.json.

The script's `stored_check` records values but does not assert equality. Its June 1–7 stored CI is null
because that original interval is in a separate bootstrap artifact. Do not describe this field as a
successful automated reproduction of that interval. The independent lightweight log-loss comparison
above passed. Future diagnostic versions should assert agreement and explicitly locate each CI.

Metadata inspection found no shared event IDs across distinct contracts in either input cohort. Thus
event-ID grouping does not add independent grouping information here. Broader thematic/common-event
dependence is not excluded by distinct IDs.

The crossed bootstrap is a recognized approach under crossed-effect assumptions, not an exact universal
solution: see [Owen (2007)](https://arxiv.org/abs/0712.1111) and
[Owen and Eckles (2012)](https://arxiv.org/abs/1106.2125). The caution about seven dates and temporal
dependence is this review's application to the present design. No bootstrap was rerun.

## Next-cycle specification: useful draft, not ready to freeze

- Keep HGB plus online history versus online history alone as the primary contrast. Include the same
  rate and matured-outcome count in the matched logistic/GAM comparisons. Resolve whether the primary
  HGB uses both rate and count: the current candidate row is less explicit than the factorial row.
- Reconstruct online features causally during every training/validation fold. Specify the training-only
  global prior, initialization, carry-over/reset rules, maturity and actual availability, missing labels,
  and handling of contracts with no matured outcomes. A real deployment must update from available
  labels, not merely an assumed wall-clock lag.
- Define what the gain establishes: pooled information beyond personal history; conditional value in
  cold-start/sparse-history strata; and quote-state information beyond a smoothed activity estimate.
  Avoid “first quote” superiority before that stratum is measured.
- Finalize the feature set, tuning budget/search space, calibration variant, cohort separation, primary
  weighting and Brier guard. Clarify that test event families are disjoint from development, not just
  from the current project. Liquidity strata must use information available before test outcomes.
- Treat ~660 as an illustrative count of **contributing independent contracts**, not a validated
  recruitment target. Using the exact stored contract CI gives SE≈0.0156209 and ~670 contracts for the
  stated normal-approximation calculation; the difference is rounding, not an important error. The
  substantive limitation is scaling one-way variance from one seven-day block for a two-way primary
  analysis. Date-level shocks, unequal cluster sizes, inactive contracts and serial dependence require
  explicit planning. Increasing contracts alone does not guarantee the target precision.
- Re-estimate power over a grid of contract counts and time spans using development-only variance
  evidence before the confirmatory freeze. Model development and any new data collection remain
  subject to the separate cycle authorization; this review starts neither.

For the current report, correct interpretation now, preserve the frozen pass rules, and fill pending
results after the scheduled close-out. Further literature should frame the pooled-versus-personal
history question and distinguish duration/update-arrival targets from endpoint change. Citation volume
cannot substitute for the missing matched-baseline and independent-test evidence.
