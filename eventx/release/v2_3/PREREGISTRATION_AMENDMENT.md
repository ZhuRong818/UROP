# EventX v2.3 news-availability and decision-contract amendment

**Protocol ID:** `eventx-v2.3-news-availability-clarifications-20260817`  
**Created:** `2026-08-17T07:55:29Z`  
**Deadline:** `2026-10-31T23:59:59Z`  
**Status:** preregistered before any v2/v2.1/v2.2/v2.3 development or holdout labels  
**Prospectively supersedes:** `eventx-v2.2-october-pilot-fixes-20260817`

## Reason for this version

The label-blind review of v2.2 found five remaining ambiguities after the August 8–17
Lumid rehearsal:

1. the response-cap and ingestion-gap rules for `/news/latest` were not operationally
   frozen for both development and holdout;
2. publication time and first source observation time did not have one conservative
   point-in-time feature rule;
3. the active B1-versus-B0 hypotheses were defined indirectly through substitutions in
   historical KOL hypotheses;
4. the effect of an undefined required fold metric on promotion was unspecified; and
5. the synthetic power simulation appeared after label generation in one execution
   list even though the controlling immediate-action list required it before labels.

This amendment resolves only those ambiguities. It was authorized and created while
development and holdout labels, prevalence, predictions and model metrics remained
uncreated and uninspected. The sealed v2.2 protocol, manifest, Lumid drill and incomplete
news finding remain unchanged evidence.

## Scientific positioning

The October report is titled and framed as:

> **A prospective protocol-validation study of incremental news information in
> prediction-market repricing**

Its primary conclusion concerns B1 market plus news versus B0 market-only on the frozen
14-market cohort. The EventX program's KOL-versus-market-plus-news question is deferred:
the preregistered KOL-v2 association rule did not meet its validation threshold. v2.3
does not run B2, B3, KOL nulls or T5 and cannot support a KOL incremental-information
claim.

## Inherited v2.2 decisions

v2.3 changes no cohort, taxonomy, association matcher, market or news feature family,
price rule, threshold formula, eligibility rule, learner, seed, fold assignment,
metric, bootstrap, promotion threshold, date, candidate limit or holdout rule. It
retains:

- the frozen 14-market cohort;
- development `[2026-08-08, 2026-09-28)`;
- the September 28–October 1 reconciliation/evaluation/freeze buffer;
- the October 1–22 half-open one-shot holdout;
- uniform latest canonical-YES last trade as the primary price;
- price-age and trade-arrival robustness diagnostics;
- the inherited heuristic absolute-jump threshold;
- B1 versus B0 as the only confirmatory comparison; and
- Lumid-only external observational data.

## Explicit active hypotheses

The active hypotheses are now stated directly:

```text
H1_v2.3: AP(B1) - AP(B0) > 0.
H2_v2.3: Brier(B0) - Brier(B1) > 0.
H3_v2.3: H1 and H2 improvements are both positive in at least 4 of 5 outer folds.
H4_v2.3: the paired moving-block-bootstrap 95% lower bound for
         Brier(B0) - Brier(B1) is > 0.
H5_v2.3: Brier(B0) - Brier(B1) is >= 0 separately in both venues.
```

All five conditions are required for B1 promotion. The old B3-versus-B1 H1–H6 are
historical lineage hypotheses and do not run in v2.3.

## Undefined confirmatory metrics

An undefined required confirmatory metric does not invalidate all descriptive output,
but it makes its promotion condition unsatisfied:

- if AP or Brier improvement is undefined in any outer fold, that fold does not count
  as one of the required four positive folds;
- if the aggregate AP difference, aggregate Brier improvement or its bootstrap lower
  bound is undefined, the corresponding H1, H2 or H4 condition fails;
- if venue-specific Brier improvement is undefined for either venue, H5 fails; and
- no undefined value may be dropped, imputed, converted to zero, or excluded from a
  denominator to promote B1.

Therefore one undefined fold can coexist with four defined positive folds for H3, but
an undefined required aggregate or venue metric prevents promotion. All undefined
metrics and their causes are reported. If B1 does not meet every condition, B0 remains
the frozen candidate.

## News response-cap and ingestion-gap contract

The frozen machine-readable contract is
`eventx/release/v2_3/news_collection_contract.json`.

For both development and holdout:

- `/news/latest` is polled every 60 seconds;
- the request limit and observed response cap are 200 rows;
- every request stores its parameters, start/completion times, row count, response
  hash, event-time diagnostics, prior-success gap and checkpoint decision;
- `returned_rows >= 200` is a censoring alarm, irrespective of plausibility;
- the checkpoint never advances on a capped or failed response;
- more than 300 seconds between successful requests is a gap alarm;
- an uncapped response from the unchanged pre-gap checkpoint may document recovery;
- otherwise the interval remains potentially censored until independent Lumid-only
  reconciliation proves it complete; and
- any potentially censored interval still unresolved at a data gate is unrecoverable
  for that gate: B1 is `incomplete`, never zero-filled.

The August 8–17 `/news/latest` cap remains unresolved. v2.3 does not retrospectively
convert that incomplete rehearsal into a pass.

The current legacy collector is not represented as compliant with this contract: it
polls every 60 seconds at `limit=200` but does not record a cap alarm and may advance
the cursor after a 200-row response. Its append-only records remain provenance evidence.
The separate v2.3 implementation is frozen in `eventx/tasks/collect_v2_3_news.py`.
Launching it or replacing the live daemon is a distinct, explicit operational action.

## Point-in-time news availability

For each stable news record:

```text
first_seen_at = earliest successful EventX retrieval time across valid Lumid endpoints
available_at  = max(published_at, first_seen_at)
```

The primary B1 rolling windows use `available_at`, not a later re-retrieval time and
not retrospectively backdated publication time. This means an article declared
published at 10:00 but first observed through Lumid at 10:17 cannot enter the 10:05
feature vector; its primary availability begins at 10:17.

`published_at`, `first_seen_at`, `retrieved_at`, ingestion latency and publication-time
quality flags are retained. Missing or invalid `published_at` rows are excluded from
primary B1. Conflicting publication timestamps for the same stable record are
quarantined until reconciled. A `published_at`-only reconstruction may be reported as
a separate oracle/public-availability sensitivity but cannot rescue the primary gate
or define the holdout candidate.

This rule is deliberately conservative under the Lumid-only source constraint. It
prevents outage recovery or historical backfill from placing information into feature
vectors before EventX first observed it.

## Label-threshold paper language

The formula remains unchanged:

```text
threshold_h(t) = 4 * sigma_1m_240(t) * sqrt(h / 30)
```

The report must state:

> The threshold is a preregistered heuristic event definition inherited from the pilot
> protocol and should not be interpreted as a Gaussian four-standard-deviation event.

No Gaussian tail-probability, conventional four-horizon-sigma or comparable claim is
permitted. The justification is inheritance and prospective consistency, not observed
label prevalence.

## Corrected execution order

The controlling order is:

1. close and reconcile the exact development source window;
2. pass and freeze the label-blind market/news data-sufficiency gate;
3. run the synthetic 14-market cluster power/precision simulation without empirical
   labels, prevalence or outcome paths;
4. freeze the simulation configuration, seed and output;
5. only then construct the primary price grid, eligibility rows and labels; and
6. run the already frozen B0/B1 development procedure once.

The simulation may disclose low power or wide intervals. It may not change the cohort,
target, features, folds, learner, gate or holdout.

## Sample-size interpretation

The final report must say that temporal row count provides precision conditional on
the selected markets and does not create hundreds of thousands of independent market
observations. v2.3 contains 14 market clusters, with only roughly two to three
validation markets per market group. Population-wide, category-complete and causal
claims remain prohibited.

## Integrity

Any subsequent change to news availability, polling, censoring, gap recovery,
hypotheses, undefined-metric disposition, execution order or scientific positioning
requires another protocol ID before affected labels or metrics are inspected. v2.2
and all earlier sealed artifacts remain immutable lineage.
