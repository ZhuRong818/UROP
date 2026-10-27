# EventX v3.1 historical-holdout protocol deviation

## What happened

After the B0 candidate and holdout implementation were frozen, the holdout builder
correctly constructed and hash-locked 211,718 examples. However, the builder also
summed the newly constructed labels and wrote `positives = 26,381` and
`prevalence = 0.12460442664298738` to its report before the evaluator wrote the
required consumption receipt. This contradicted the implementation specification's
stronger wording that the receipt precedes any label reading.

## What was not exposed

No frozen-candidate prediction, AP, Brier score, ROC AUC, calibration statistic,
freshness result, venue result, alert result, or decision-curve result was computed
or inspected. The single B0 candidate, its coefficients, all transforms, the holdout
example construction, the alert threshold, and every evaluation formula had already
been hash-frozen before holdout retrieval.

## Handling

- Preserve the original builder output and original implementation manifest.
- Do not rebuild, delete, or alter the holdout examples.
- Amend only the evaluator's receipt and result status so they truthfully disclose
  the pre-receipt label summary.
- Write the corrected receipt before producing any candidate prediction or
  performance metric, then evaluate exactly once.
- Qualify the final holdout as containing a receipt-order deviation. The development
  B0-versus-B1 selection result is unaffected because it was completed before the
  holdout was retrieved.

This amendment is procedural and does not change the candidate or any statistical
calculation after observing holdout prevalence.
