# EventX: usable quote-forecast prototype and research progress

Checkpoint: 2026-10-24 T 14:14:07.354854+00:00. This report is a frozen checkpoint; use the freshness-checking command below for current output.

## Result and meaning

The separate quote pipeline now has **1 timely prospective forecast recorded**, with **0 observed endpoints** at this checkpoint. This is an operational forecasting prototype, not demonstrated predictive superiority. The reference forecasts the same YES-book midpoint 30 minutes later. Candidate regression forecasts are recorded separately; neither regression beat persistence in development.

The original condition_120 k trade-movement classifier remains frozen and unscored on this capture. Quote-midpoint prediction is a different target and cannot inherit its historical log-loss improvements. No news effect, profitability or resolved-market outcome prediction is claimed.

## What failed and what changed

The first four-hour-history shadow finished with 100 decision opportunities:44 abstentions, 56 missed, 0 forecasts, 0 endpoints. Every abstention lacked continuous 240-minute history. Observed cycle gaps were 4473.100816 seconds and 2159.973661 seconds. These records establish interruption; this audit alone does not establish its cause. All closed artifacts are preserved.

The new experiment explicitly separates feature requirements:

1. **Snapshot reference:** current valid book and verified current market/status mapping. No past price history is needed to forecast an unchanged midpoint.
2. **Snapshot ridge:** seven current-book features, fixed ridge penalty 100, fitted once on chronological development training data.
3. **Short-history ridge:** those seven features plus 5-minute momentum, 30-minute momentum and 30-minute volatility. Available only with uninterrupted 30-minute quote history.
4. **Weighted midpoint:** a size-weighted best-bid/best-ask comparator, not a fully estimated microprice model.

The current-book gates remain: receipt age<=120 seconds, two positive sides inside (0, 1), spread<=0.05, at least 10 tokens at each best side, exact condition/token/rules mapping, active and accepting orders, not closed, and unresolved/undisputed status. Status receipt age<=360 seconds. Scheduled expiry must exceed the 30-minute horizon. Future labels still require continuous quote/status coverage; failed or missing observations are never imputed. These are separately specified research eligibility rules, not certified economic thresholds.

Snapshot ridge inputs are midpoint, spread, log bid size, log ask size, imbalance, weighted-midpoint offset and log source-message age. Training-only mean/std normalization; ridge with unpenalized intercept predicts midpoint change and clips the resulting midpoint to[0, 1]. No parameter search, live refitting, promotion or automatic trading.

## Development results: compare within each panel

Same previously exposed source snapshot, 4032 scheduled rows. Snapshot eligible 1625, short-history eligible 1418;1418 complete snapshot observations versus 686 in the earlier 240-minute-history design. This is a coverage improvement caused by different feature requirements, not an accuracy improvement or new independent events.

Snapshot:684 training rows;614 validation rows across 11 markets. Only 23 validation midpoints changed.

| Model | Matched validation rows | MAE | RMSE |
|---|---:|---:|---:|
| persistence | 614 | 0.0000627036 | 0.0005012200 |
| snapshot_ridge | 614 | 0.0001559460 | 0.0005324883 |
| weighted_midpoint | 614 | 0.0022850223 | 0.0031576902 |

Short-history panel:605 training rows;588 validation rows across 11 markets. Only 23 validation midpoints changed.

| Model | Matched validation rows | MAE | RMSE |
|---|---:|---:|---:|
| persistence | 588 | 0.0000654762 | 0.0005121815 |
| short_ridge | 588 | 0.0001106745 | 0.0005212904 |
| snapshot_ridge | 588 | 0.0001587700 | 0.0005435983 |
| weighted_midpoint | 588 | 0.0022677471 | 0.0031276423 |

Errors are in 0–1 price units; lower is better. Multiplying by 100 converts to percentage points. Rows differ between panels; compare models within a panel. Persistence remains best in both. The prior 240-minute panel had 444 validation rows: persistence MAE 8.445945945945952 e-05, ridge MAE 0.00018114435192817977, weighted MAE 0.0019342785670910098.

Train endpoints precede 24 Oct 00:00 UTC; validation decisions start 00:30 UTC, with the intervening rows purged. The data were already exposed in related research. This is exploratory development, with overlapping 30-minute horizons and one short shared calendar period; no confidence intervals or independent-confirmation claims.

## Why the learned forecasts lose

In the short panel, 565/588 validation endpoints are unchanged. Persistence makes zero error there; short ridge introduces MAE 0.000047602735990905376. On 23 changed endpoints, short ridge MAE 0.0016600457606747287 is slightly below persistence 0.001673913043478262, but that does not overcome errors on unchanged rows. This is an **outcome-conditioned diagnosis**, not a deployable filter: we cannot select changed rows before forecasting.

The short-model training mean change is+0.000016528925619834755; validation mean change is−0.00005017006802721093. Drift direction changes, and the median change is zero in both. A useful next learned component would need to predict whether a change occurs, before predicting its direction/size. More independent changing episodes are needed before fitting and assessing that component. It is not added to the current frozen run.

## Live run and how to inspect it

Source PID 5099 started 24 Oct 14:04 UTC and is bounded to 25 Oct 14:04 UTC (22:04 SGT). Forecast PID 8023 started 14:08 UTC, first grid 14:10 UTC; last grid 25 Oct 13:30 UTC and scheduled stop 14:03 UTC (22:03 SGT). A powered, awake, networked Mac with its lid open is required; the process cannot produce forecasts during a host interruption.

| Market | Decision UTC | Target UTC | Recorded state | Persistence midpoint |
|---|---|---|---|---:|
| Negative GDP growth in 2026? | 2026-10-24T14:10:00+00:00 | 2026-10-24T14:40:00+00:00 | abstained | — |
| US recession by end of 2026? | 2026-10-24T14:10:00+00:00 | 2026-10-24T14:40:00+00:00 | forecast recorded | 0.0850 |

These are checkpoint examples, not permanently current prices. From the repository run:

```sh
.venv/bin/python -m eventx.tasks.show_v7_quote_forecasts_20261024
```

This reader suppresses forecasts when the service heartbeat is older than 30 seconds, the current five-minute display interval has expired, or no timely forecast was committed. `latest_forecasts.json` contains reference and candidate values, book timestamps, short-history availability and out-of-training-range flags. The frozen historical range is a diagnostic, not a calibrated confidence interval.

The append-only forecast journal records inputs available by the decision grid, model hashes, output, emission time, abstentions and missed deadlines. A forecast must be durably recorded by grid+30 seconds. Its 30-minute endpoint is adjudicated after a 120-second operational delay, using only receipts available by the target time. No backdated forecasts or late-filled targets. The completion report will compare all models on matched eligible endpoints, with missing endpoints and coverage reported separately.

At this checkpoint, 61 manifest entries and both journal chains were checked, along with three input payloads used by the forecast. Every committed forecast checked used pre-decision receipts and was emitted before its target. The original 20 file locks also match. No protected holdout was opened.

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
