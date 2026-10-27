# EventX: usable quote-forecast prototype and research progress

Checkpoint: 2026-10-24T14:14:07.354854+00:00. This report is a frozen checkpoint; use the freshness-checking command below for current output.

## Result and meaning

The separate quote pipeline now has **1 timely prospective forecasts recorded**, with **0 observed endpoints** at this checkpoint. This is an operational forecasting prototype, not demonstrated predictive superiority. The reference forecasts the same YES-book midpoint30minutes later. Candidate regression forecasts are recorded separately; neither regression beat persistence in development.

The original condition_120k trade-movement classifier remains frozen and unscored on this capture. Quote-midpoint prediction is a different target and cannot inherit its historical log-loss improvements. No news effect, profitability or resolved-market outcome prediction is claimed.

## What failed and what changed

The first four-hour-history shadow finished with100decision opportunities:44abstentions,56missed,0forecasts,0endpoints. Every abstention lacked continuous240-minute history. Observed cycle gaps were4473.100816seconds and2159.973661seconds. These records establish interruption; this audit alone does not establish its cause. All closed artifacts are preserved.

The new experiment explicitly separates feature requirements:

1. **Snapshot reference:** current valid book and verified current market/status mapping. No past price history is needed to forecast an unchanged midpoint.
2. **Snapshot ridge:** seven current-book features, fixed ridge penalty100, fitted once on chronological development training data.
3. **Short-history ridge:** those seven features plus5-minute momentum,30-minute momentum and30-minute volatility. Available only with uninterrupted30-minute quote history.
4. **Weighted midpoint:** a size-weighted best-bid/best-ask comparator, not a fully estimated microprice model.

The current-book gates remain: receipt age<=120seconds, two positive sides inside(0,1), spread<=0.05, at least10tokens at each best side, exact condition/token/rules mapping, active and accepting orders, not closed, and unresolved/undisputed status. Status receipt age<=360seconds. Scheduled expiry must exceed the30-minute horizon. Future labels still require continuous quote/status coverage; failed or missing observations are never imputed. These are separately specified research eligibility rules, not certified economic thresholds.

Snapshot ridge inputs are midpoint,spread,log bid size,log ask size,imbalance,weighted-midpoint offset and log source-message age. Training-only mean/std normalization; ridge with unpenalized intercept predicts midpoint change and clips the resulting midpoint to[0,1]. No parameter search, live refitting, promotion or automatic trading.

## Development results: compare within each panel

Same previously exposed source snapshot,4032scheduled rows. Snapshot eligible1625,short-history eligible1418;1418complete snapshot observations versus686in the earlier240-minute-history design. This is a coverage improvement caused by different feature requirements, not an accuracy improvement or new independent events.

Snapshot:684training rows;614validation rows across11markets. Only23validation midpoints changed.

| Model | Matched validation rows | MAE | RMSE |
|---|---:|---:|---:|
| persistence | 614 | 0.0000627036 | 0.0005012200 |
| snapshot_ridge | 614 | 0.0001559460 | 0.0005324883 |
| weighted_midpoint | 614 | 0.0022850223 | 0.0031576902 |

Short-history panel:605training rows;588validation rows across11markets. Only23validation midpoints changed.

| Model | Matched validation rows | MAE | RMSE |
|---|---:|---:|---:|
| persistence | 588 | 0.0000654762 | 0.0005121815 |
| short_ridge | 588 | 0.0001106745 | 0.0005212904 |
| snapshot_ridge | 588 | 0.0001587700 | 0.0005435983 |
| weighted_midpoint | 588 | 0.0022677471 | 0.0031276423 |

Errors are in0–1 price units; lower is better. Multiplying by100 converts to percentage points. Rows differ between panels; compare models within a panel. Persistence remains best in both. The prior240-minute panel had444validation rows: persistence MAE8.445945945945952e-05,ridge MAE0.00018114435192817977,weighted MAE0.0019342785670910098.

Train endpoints precede24Oct00:00UTC; validation decisions start00:30UTC, with the intervening rows purged. The data were already exposed in related research. This is exploratory development, with overlapping30-minute horizons and one short shared calendar period; no confidence intervals or independent-confirmation claims.

## Why the learned forecasts lose

In the short panel,565/588validation endpoints are unchanged. Persistence makes zero error there; short ridge introduces MAE0.000047602735990905376. On23changed endpoints, short ridge MAE0.0016600457606747287 is slightly below persistence0.001673913043478262, but that does not overcome errors on unchanged rows. This is an **outcome-conditioned diagnosis**, not a deployable filter: we cannot select changed rows before forecasting.

The short-model training mean change is+0.000016528925619834755; validation mean change is−0.00005017006802721093. Drift direction changes, and the median change is zero in both. A useful next learned component would need to predict whether a change occurs, before predicting its direction/size. More independent changing episodes are needed before fitting and assessing that component. It is not added to the current frozen run.

## Live run and how to inspect it

SourcePID5099 started24Oct14:04UTC and is bounded to25Oct14:04UTC(22:04SGT). ForecastPID8023 started14:08UTC,first grid14:10UTC; last grid25Oct13:30UTC and scheduled stop14:03UTC(22:03SGT). A powered, awake, networked Mac with its lid open is required; the process cannot produce forecasts during a host interruption.

| Market | Decision UTC | Target UTC | Recorded state | Persistence midpoint |
|---|---|---|---|---:|
| Negative GDP growth in 2026? | 2026-10-24T14:10:00+00:00 | 2026-10-24T14:40:00+00:00 | abstained | None |
| US recession by end of 2026? | 2026-10-24T14:10:00+00:00 | 2026-10-24T14:40:00+00:00 | forecast_recorded | 0.08499999999999999 |

These are checkpoint examples, not permanently current prices. From the repository run:

```sh
.venv/bin/python -m eventx.tasks.show_v7_quote_forecasts_20261024
```

This reader suppresses forecasts when the service heartbeat is older than30seconds, the current five-minute display interval has expired, or no timely forecast was committed. `latest_forecasts.json` contains reference and candidate values, book timestamps, short-history availability and out-of-training-range flags. The frozen historical range is a diagnostic, not a calibrated confidence interval.

The append-only forecast journal records inputs available by the decision grid, model hashes, output, emission time, abstentions and missed deadlines. A forecast must be durably recorded by grid+30seconds. Its30-minute endpoint is adjudicated after a120-second operational delay, using only receipts available by the target time. No backdated forecasts or late-filled targets. The completion report will compare all models on matched eligible endpoints, with missing endpoints and coverage reported separately.

At this checkpoint, 61manifest entries and both journal chains were checked; 3used input payloads verified. Every committed forecast checked used pre-decision receipts and was emitted before its target. The original20file locks also match. No protected holdout was opened.

## Next research decision

1. Let the fixed run collect actual forecasts and endpoints; monitor receipt gaps and endpoint loss. No tuning from interim results.
2. Audit its completed journal and report coverage, MAE/RMSE, changed-endpoint count, per-market results and missingness. A few repeated predictions on two markets establish operation, not broad forecasting validity.
3. Collect across additional independent dates and the already reserved release episodes, with exact evidence/terminal checks for any news comparison.
4. After sufficient development evidence, freeze a separate change-occurrence plus conditional-movement experiment. It must beat persistence across all eligible rows, not just hindsight-selected changed rows.

## Reproducible artifacts

- New policy/code locks: `eventx/release/v7/memory_quote_20261024/`.
- Development receipt,models,observations,predictions,metrics and manifest: `data/v7/memory_quote_20261024/development/`.
- Error diagnosis: `data/v7/memory_quote_20261024/error_diagnosis/`.
- Prospective activation: `eventx/release/v7/memory_shadow_20261024/`.
- Live journal/status/output and eventual completion report: `data/v7/memory_quote_20261024/shadow/`.
- New source receipts: `data/v7/quote_source_20261024_v02/live/`.
- This checkpoint and audit: `data/v7/usable_forecast_progress_20261024/`.
- Preserved first-run diagnosis: `data/v7/quote_shadow_diagnosis_20261024/`.
