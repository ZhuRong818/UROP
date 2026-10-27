# EventX v3 historical primary study

Protocol ID: `eventx-v3-historical-primary-20260902`

This protocol makes the completed, point-in-time historical B0-versus-B1 comparison
the primary EventX news study. The frozen prospective v2.3 study remains unchanged as
a secondary replication; its October holdout and its 14-market cohort are not reused
to select this historical model.

The primary question is whether conservatively available, market-relevant Lumid news
adds predictive information about 30-minute absolute canonical-YES repricing beyond
executed-market history. This is predictive and incremental, not causal. It does not
test the deferred KOL hypothesis.

## Why the historical study is now admissible

Every one of 218,392 candidate news rows joined to a Lumid `provenance.runs` record,
and no `ingest_ts` preceded its joined run start. The primary availability clock is
the maximum of publication time, row ingestion time, run start and run end when one
exists. Rows available more than 24 hours after publication are excluded. This leaves
214,944 source rows and prevents a historical export from placing an article before
the Lumid run that observed it.

The cohort was then selected using development activity only. It contains 4,670
markets: 3,851 Kalshi and 819 Polymarket. The development prefix contains 147,377
deduplicated news documents, 218,523 frozen-rule associations, and 1,423 markets with
at least five associations. All label-blind support gates passed. The July 22–August
8 holdout did not affect selection.

## Confirmatory comparison

- B0: the twelve frozen market-history features.
- B1: B0 plus news counts over 60, 360 and 1,440 minutes and the frozen symbol-mapped
  indicator.
- Target: the inherited 30-minute absolute log-odds jump definition.
- Learner: the inherited standardized logistic SGD ensemble with fixed seeds.
- Development validation: five purged expanding-time folds, each with a disjoint
  deterministic market group.
- Selection: B1 must pass every H1–H5 condition; otherwise B0 is frozen.
- Final test: at most one selected specification receives one evaluation on the
  sealed historical holdout.

The exact machine-readable definitions in `protocol.json` control. No data-driven
change is permitted after label construction begins.
