# EventX v1 pilot: frozen final research report

**Status:** final v1 pilot result; confirmatory holdout consumed  
**Development dataset:** `eventx-toy-ceea70842baa88753929`  
**Out-of-time dataset:** `eventx-oot-7c4fd487edb3928b9253`  
**Report date:** 2026-07-31  
**Editorial audit:** completed 2026-07-31

## Abstract

EventX tests whether observable news and posts from curated key opinion leaders
(KOLs) improve short-horizon prediction-market repricing forecasts beyond market
history alone. This frozen v1 pilot studies 20 canonical YES outcomes from
Polymarket, sampled at a 5-minute evaluation cadence, with a 30-minute binary jump
target. Candidate models were compared on identical five-fold purged,
expanding-window development splits.

The market-only B0 model was the only specification retained. Core news increased
development average precision (AP) by 0.001427 but worsened Brier score by 0.000772
and was temporally unstable. KOL features reduced AP and worsened Brier score both
alone and when added to news. The combined model's Brier deterioration relative to
news was −0.002533, with a 95% moving-block bootstrap interval of
[-0.003883, -0.001163].

After the original test block was disclosed as previously exposed, B0 was frozen and
evaluated once on a new July 23–30 out-of-time holdout. On 1,410 eligible rows from
13 markets with 130 jumps, B0 achieved AP 0.135527 versus 0.092199 for a constant
training-prevalence score. Its Brier score was 0.084190 versus 0.084310, an
improvement of only 0.000121. The result supports B0 as a useful ranking reference
in this pilot, but does not establish strong calibration, economic value, causal KOL
influence, or broad generalization.

## 1. Scope and research question

The pilot asks:

> Do point-in-time KOL or news activity features improve 30-minute
> prediction-market jump forecasting beyond market price and trading history?

The tested model ladder was:

- **B0:** market-only;
- **B1:** market plus news;
- **B2:** market plus KOL;
- **B3:** market plus news plus KOL.

This is an artifact-led pilot, not the completed benchmark proposed in
`research_plan.md`. It validates the ingestion, outcome normalization, temporal
feature construction, association audits, purged evaluation, model-freezing, and
one-shot holdout workflow. It does not complete the planned multi-venue,
multi-horizon, public two-track benchmark.

## 2. Data and frozen protocol

| Item | Frozen v1 specification |
|---|---|
| Venue | Polymarket |
| Prediction unit | Canonical YES outcome at timestamp \(t\) |
| Cohort | 20 binary outcomes selected using training-period information only |
| Development window | 2026-05-22 through 2026-07-22 |
| Final OOT window | 2026-07-23 through 2026-07-30 |
| Evaluation cadence | 5 minutes |
| Forecast horizon | 30 minutes |
| Development comparison | 17,540 OOF rows, 2,027 jumps |
| Final B0 training | 20,702 eligible pre-holdout rows |
| Final OOT evaluation | 1,410 rows, 13 markets, 130 jumps |
| Frozen category tags | 10 politics, 9 other, 1 sports |
| Primary metric | Average precision |
| Calibration metric | Brier score |

The category tags are coarse automatically generated metadata. The frozen file
incorrectly labels the Karen Bass Los Angeles mayoral market as `sports`. It is
preserved unchanged for hash integrity, but no category-stratified claim should use
this field without a versioned correction.

Minute bars use the last canonical-outcome trade price, forward-filled when a minute
has no trade. Price is clipped to [0.0001, 0.9999] before conversion to log-odds.
The jump label is one when the absolute 30-minute forward log-odds move is at least
four times the trailing 240-minute standard deviation of one-minute log-odds
changes.

Eligibility is determined using information available at or before \(t\): at least
three trades and 100 units of notional over the trailing 240 minutes, excluding
terminal boundary-price rows near scheduled close or at/after known resolution.
Forward liquidity is not used for eligibility. Features use only events timestamped
at or before \(t\).

Development evaluation uses five expanding-window folds with a 30-minute purge.
Paired uncertainty estimates use a 360-minute circular moving-block bootstrap
stratified by market. The same rows, labels, model class, and hyperparameters are
used for candidate comparisons.

## 3. Association quality

The semantic association rules were frozen before predictive comparison.

| Rule | Blind-review precision | Recall | F1 | Frozen coverage |
|---|---:|---:|---:|---|
| KOL rule v3 | 0.8850 | 0.9365 | 0.9100 | 3,394 associations; 18 of 20 markets matched |
| News rule v1 | 0.9286 | 0.9701 | 0.9489 | 149 associations; 8 matched markets |

KOL rule v3 was evaluated on 299 scored cases after excluding one uncertain case.
News rule v1 was evaluated on 99 scored cases after excluding one uncertain case;
its recall is defined over hard retrieval candidates. Both rules exceeded their
predefined precision and recall thresholds.

Association accuracy and predictive usefulness are separate questions. These audits
support the relevance of linked documents; they do not imply that the resulting
aggregate activity features forecast future jumps.

The point-in-time feature checks found no future-event violations. Potentially
unsafe KOL follower and engagement counts were excluded because they were
extraction-time snapshots rather than timestamped histories. Structured news
sentiment was unavailable for the pilot because none of the event markets had a
canonical financial-ticker mapping.

## 4. Reference model

B0 is a standardized logistic model trained by stochastic gradient descent. Its 11
features are:

1. price log-odds;
2. momentum over 5, 30, and 120 minutes;
3. realized volatility over 30 and 240 minutes;
4. trade count over 60 and 240 minutes;
5. notional over 60 and 240 minutes; and
6. minutes since the latest trade.

Trade-count and notional features receive a `log1p` transform; all others use the
identity transform. Frozen hyperparameters are 8 epochs, learning rate 0.02, L2
penalty 0.0001, and shuffle seed 11.

## 5. Development results

All metrics in this table use the same 17,540 out-of-fold rows. “Brier improvement”
is reference Brier minus candidate Brier, so positive is better.

| Candidate | AP | Brier | Incremental result | Decision |
|---|---:|---:|---|---|
| B0 market-only | 0.140883 | 0.102669 | Reference | Retain |
| B2 market + KOL | 0.130623 | 0.105419 | AP −0.010260; Brier improvement −0.002750 vs B0 | Reject |
| Nested gated KOL | 0.136126 | 0.102895 | AP −0.004757; Brier improvement −0.000227 vs B0 | Reject |
| Market + rich news | 0.121761 | 0.107002 | AP −0.019122; Brier improvement −0.004334 vs B0 | Reject |
| B1 market + core news | 0.142310 | 0.103441 | AP +0.001427; Brier improvement −0.000772 vs B0 | Reject |
| B3 market + core news + KOL | 0.133268 | 0.105973 | AP −0.009042; Brier improvement −0.002533 vs B1 | Reject |

The core-news AP gain was not sufficient for promotion. AP improved in three of five
folds and Brier in two of five; the Brier-improvement bootstrap interval was
[-0.001769, 0.000113]. Rich news was worse on both metrics.

The full KOL candidate improved both AP and Brier in only one of five folds. A nested
activity-gating experiment selected `360m` in the first outer fold and `off` in the
remaining four; its aggregate metrics still failed every promotion gate. Adding
KOL features to core news improved both metrics in only one of five folds. The B3
versus B1 Brier-improvement interval, [-0.003883, -0.001163], was entirely below
zero.

## 6. Why the KOL candidate failed

The failure was not explained by one removable fold or market:

- excluding any single market did not make Brier improvement positive;
- excluding any single fold did not make Brier improvement positive;
- 11 of 14 KOL coefficients changed sign across folds;
- five of 14 KOL feature-label correlations reversed in fold 3.

The Strait of Hormuz market contributed 84.2% of the net Brier loss. Removing it
made AP change slightly positive (+0.001756), but Brier remained worse (−0.000460).
In fold 3, among rows with KOL activity in the preceding 30 minutes, B3 raised mean
prediction from 0.145 to 0.188 against a prevalence of 0.144; Brier improvement was
−0.037041.

The evidence therefore points to temporal and cross-market instability rather than
a single correctable outlier. Further gate or feature selection on the same folds
would convert validation evidence into training data, so development stopped.

## 7. Holdout integrity

An earlier B0 run had already exposed the original test block on 2026-07-29. That
run was noncanonical: it trained on 17,538 original training rows rather than all
20,702 eligible pretest rows and did not log-transform trade-count features. Its
2,276-row AP of 0.131630 and Brier score of 0.112597 are descriptive only.

The response was to disclose the exposure, lock B0, fetch a later period, freeze a
new manifest before inspecting label prevalence or metrics, and authorize exactly
one evaluation. The replacement dataset contains 2,080 freshly fetched trades over
July 23–30. Its evaluator and input hashes were fixed before evaluation.

The one-shot evaluation was consumed at
`2026-07-31T03:31:03.495303Z`. Its receipt sets `rerun_permitted` to `false`.
Neither the original block nor the replacement result may be used for v1 tuning.

## 8. Final out-of-time result

| Metric | B0 market-only | Constant training-prevalence score | Difference |
|---|---:|---:|---:|
| Average precision | 0.135527 | 0.092199 | +0.043328 |
| Brier score | 0.084190 | 0.084310 | +0.000121 improvement |
| Mean prediction | 0.119406 | 0.116945 | — |

The holdout jump rate was 9.22%. B0's AP exceeded the constant-score reference by
4.33 percentage points, showing ranking information in the locked market-history
features. Calibration evidence is much weaker: the Brier improvement was only
0.000121, and mean predicted risk exceeded realized prevalence by 2.72 percentage
points.

This result does not reverse the development rejection of news or KOL candidates.
Those candidates were not authorized for the replacement holdout and were correctly
left unevaluated.

## 9. Findings and claim boundaries

The frozen evidence supports three conclusions:

1. The v1 pipeline can build point-in-time market, news, and KOL features and compare
   fixed candidates under purged temporal evaluation.
2. B0 provides useful out-of-time ranking discrimination relative to a constant
   score in this short pilot.
3. The tested news and KOL activity representations do not show sufficiently stable
   incremental value for promotion.

It does **not** support claims that KOL posts never matter, that KOL activity causes
market moves, that B0 is economically tradable, or that the result generalizes to
other venues, periods, horizons, categories, or representation methods. A null
result for these aggregate activity features is not a universal null result for
social information.

## 10. Limitations

- The pilot covers only 20 Polymarket outcomes and one short, unusually recent
  retained-trade window.
- Only 13 markets contribute eligible final OOT rows, and the holdout contains 130
  positive labels.
- The evaluation has one horizon and no Kalshi or cross-venue component.
- The frozen category metadata are coarse and include a known misclassification, so
  they do not support category-stratified conclusions.
- Bars use last trades and forward fills because historical L2 snapshots are not
  available; thin-market price measurement remains imperfect.
- News coverage is sparse: only eight markets have associations, and structured
  ticker sentiment is unavailable.
- KOL features are aggregate activity and diversity measures, not semantic text
  representations.
- The final OOT comparison lacks a confidence interval and tests only frozen B0
  against a constant score.
- No transaction-cost backtest, T5 per-KOL influence ranking, FDR analysis,
  category-stratified result, or public two-track dataset release is included.

These limitations make the result a credible frozen pilot and engineering
milestone, not the final empirical answer envisioned by the full research plan.

## 11. Reproducibility and evidence

Run the release verifier from the repository root:

```bash
python -m eventx.release.verify_v1_release
```

The verifier checks the SHA-256 and byte count of every canonical artifact listed in
`eventx/release/v1/release_manifest.json`, then confirms that the final result and
consumption receipt agree on the OOT dataset and that reruns are prohibited.
Dataset composition, known biases, intended uses, and distribution constraints are
documented in `eventx/release/v1/DATASHEET.md`.

Key immutable identifiers:

- development freeze:
  `db076d3b9bd48897c590bb933c9b619657201a2c168f954e76ef346af28c4f88`;
- final B0 freeze:
  `0d0f93b6f50c60381a38f19daf64123a5efccc9bfa5c6c36d7f99ad550ee37e4`;
- OOT authorization:
  `737624dffdaac0b65ca78700c35a116235efb74d4032818ef1f7320345db4e17`;
- final result:
  `18306a8b814cec48f2acdce3fe93e06f33ee5c0d3cf41344d11339bb5e102a6a`.

The evaluator must not be rerun. Any v2 claim requires a new preregistered
development cycle and another later untouched holdout.

## 12. Conclusion

EventX v1 establishes a leakage-aware, auditable pilot workflow and a frozen
market-only reference. Market history contains modest out-of-time ranking signal,
while the tested news and KOL aggregate features do not provide stable incremental
value. The scientifically correct outcome is to retain B0, archive the negative
candidate results, preserve the consumed holdout, and treat richer KOL/news modeling
as a new preregistered research cycle rather than a post-hoc v1 rescue.
