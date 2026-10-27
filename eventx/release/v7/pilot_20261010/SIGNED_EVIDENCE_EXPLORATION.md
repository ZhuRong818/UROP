# Signed-evidence diagnostic and opened comparison

Status: **complete exploratory development analysis; no forecasting-improvement or surprise-signal claim**.

## Diagnostic queue

The 32 priority pairs cover 13 articles. The pair-level inspection is preserved in
`data/v7/signed_evidence_exploration_20261010/diagnostic_inspection.jsonl`.

The five jointly exact and signed pairs collapse to three articles:

- Article `173603179` reports May nonfarm payrolls of 172,000 against the >100K predicate. Its one exact link arrives after nominal close.
- Article `184027675` reports a general trader expectation that the June target range will remain 3.50%–3.75%. Its two exact links contain no explicit prediction-market odds and both arrive after nominal close.
- Article `189435511` attributes a rate-path forecast to Bank of America: first 25 bp hike in September. Its two exact links are nominally timely but describe one information event. One associated metadata snapshot follows article availability, the source run failed, historical active status is unverified, and first-public provenance is unknown.

The exact queue therefore contains two nominally timely contract links but only one candidate information event and zero source-certified timely events.

## Schema v0.2

`ANNOTATION_SCHEMA_V0_2.md` separates five objects that the original rubric partially conflated:

1. claim type: measurement, action, forecast, general market expectation, commentary, or mixed;
2. source attribution and reporting mode;
3. general market expectations;
4. explicit prediction-market odds, which require a named venue/contract plus a probability, price, or odds span; and
5. information-event identity, separate from the future contract event.

Direction remains relative to canonical YES. Public surprise remains unknown without an independent, timestamped pre-event expectation and a realized value.

## Event ledger

The jointly material/exact intersection contains 30 pairs and 14 article arrivals. Twenty pairs from ten article arrivals fit the nominal landmark/horizon bounds. Article `63246982` is a retrospective May 18 repetition of an April 3 official jobs release. Removing that known repeat leaves **nine candidate article-arrival events**. Six have at least one metadata snapshot no later than the article.

These are upper-bound candidate episodes. Zero have certified first-public provenance, and zero have verified historical active status. Repeated semantic information beyond the one identified retrospective release may remain. The detailed ledger is `data/v7/signed_evidence_exploration_20261010/event_ledger.jsonl`.

## Focused opened comparison

The fixed strong market baseline is the previously selected seven-leaf HGB with 600 iterations. Both offsets use 30-minute article count, latest-arrival age, and distinct-publisher controls. The augmented arm adds deterministic automatic signed-evidence summaries. Only exact, nonzero contract directions enter those features; the extractor never emits surprise.

Both arms fit on the same 4,577 news-exposed fold-4 rows and evaluate on the same 5,388 news-exposed fold-5 rows across 99 markets.

| Arm | Log loss | Brier | Average precision |
|---|---:|---:|---:|
| Strong market + exposure/timing | 0.2428284162 | 0.0779030061 | 0.3565169126 |
| Same + automatic signed evidence | 0.2428239348 | 0.0779047537 | 0.3564228730 |

The augmented-minus-control log-loss improvement is `0.0000044814` nats. The descriptive market-cluster interval is `[−0.0000675957, 0.0000779524]`; the market-balanced mean is `−0.0000021846`. Brier worsens by `0.0000017476`.

More decisively, signed evidence occurs on only 21 training rows and **zero evaluation rows**. The small prediction difference comes from jointly refitting the intercept and control coefficients after adding sparse training columns, not from signed evidence observed on fold 5. This comparison therefore diagnoses a transport/coverage failure. It provides no evidence of forecasting improvement and no evidence of a reliable surprise signal.

Canonical machine-readable results, predictions, input hashes, and artifact hashes are in `data/v7/signed_evidence_exploration_20261010/`. The consumed OOT holdout and protected V4 confirmation data were not read.
