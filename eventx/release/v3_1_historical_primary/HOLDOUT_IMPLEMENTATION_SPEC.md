# EventX v3.1 frozen historical-holdout implementation

Frozen after development selected exactly one candidate and before any historical-
holdout trade price was queried.

## Candidate and data scope

- The development H1-H5 gate selected B0. The holdout therefore evaluates only the
  frozen 12-feature market-only ensemble. B1 is not scored on the holdout and cannot
  be rescued by holdout inspection.
- Retrieve canonical-YES Lumid executions only for the preregistered corrected cohort
  and `[2026-07-22T00:00:00Z, 2026-08-08T00:00:00Z)` interval.
- Reuse the frozen composite execution identity, exact-duplicate collapse, positive-
  notional rule, timestamp ordering, price construction, eligibility, label, and
  terminal-time rules. Use the final 240 development minutes solely as left-context
  for holdout features; no development row is scored as holdout.
- Do not construct or inspect holdout news features because the selected candidate is
  B0. Columns 12-15 remain zero only for binary schema compatibility and are never
  passed to the model.

## One-shot evaluation

- Hash-lock the complete holdout implementation before trade retrieval.
- Build and hash the holdout examples before metrics. Write an irreversible holdout
  consumption receipt before reading labels, producing predictions, or computing any
  metric. If a receipt or result already exists, refuse execution.
- Apply the three frozen development-fitted scalers and logistic models without
  refitting, and average their probabilities.
- Report AP, Brier score, ROC AUC, ten-bin equal-frequency ECE, calibration intercept
  and slope overall, by venue, for price-age <=30 and <=60 minutes, and for the
  <=5-versus->5-minute trade-arrival diagnostic.
- Freeze an alert threshold as the 90th percentile of development out-of-fold B0
  probabilities before holdout retrieval. Report alert rate, positive predictive
  value, sensitivity, and the nominal 30-minute forecast lead time.
- Report decision-curve net benefit at fixed probability thresholds 0.05, 0.10, 0.15,
  0.20, 0.25, 0.30, 0.40, and 0.50 against treat-all and treat-none references.
- The holdout estimates absolute predictive performance of the B0 fallback. The
  incremental-news conclusion remains the negative development selection result.
