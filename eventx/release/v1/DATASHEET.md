# Datasheet for the EventX v1 pilot

**Release ID:** `eventx-v1-pilot-20260731`  
**Development dataset:** `eventx-toy-ceea70842baa88753929`  
**Out-of-time dataset:** `eventx-oot-7c4fd487edb3928b9253`  
**Datasheet status:** internal pilot documentation; not a public data license  
**Last reviewed:** 2026-07-31

## 1. Dataset summary

EventX v1 is a frozen research pilot for 30-minute prediction-market jump
classification. It links Polymarket trade-derived market features with
point-in-time news and curated KOL-post activity features. It was created to test
whether those external information signals improve forecasting beyond market
history alone.

The release contains a frozen development extract and a separately frozen
out-of-time (OOT) holdout. The OOT holdout was evaluated once and is now consumed.
This datasheet documents the local research artifact; it does not authorize
redistribution of upstream content.

## 2. Motivation

The pilot was built to validate:

- canonical outcome normalization for binary prediction markets;
- point-in-time market, news, and KOL feature construction;
- deterministic document-to-market association rules with blind review;
- purged temporal model comparison;
- explicit model freezing and one-shot holdout consumption; and
- reproducible reporting of positive and negative findings.

It is not the full multi-venue, multi-horizon EventX benchmark proposed in
`research_plan.md`.

## 3. Composition

### 3.1 Market cohort

The cohort contains 20 canonical YES outcomes from Polymarket. Markets were selected
using training-period information only. To qualify, a contract had to span the
study window and, during the selection window, have at least 100 trades, 1,000 units
of notional, three active days, and no more than 72 hours of staleness. Fifty-eight
markets passed; the top 20 by the frozen density score were selected.

The frozen category tags are:

| Frozen category | Markets |
|---|---:|
| Politics | 10 |
| Other | 9 |
| Sports | 1 |

These tags are coarse automatically derived metadata, not reviewed ground truth.
There is one known error: the Karen Bass Los Angeles mayoral market is tagged
`sports`. The frozen cohort file is preserved unchanged for integrity, but the tag
must not support category-stratified claims. A corrected taxonomy requires a new
versioned metadata artifact.

Nineteen selected markets were marked active and one closed in the frozen cohort
snapshot. Status is extraction-time metadata and was not projected backward as a
point-in-time feature.

### 3.2 Development extract

| Item | Count |
|---|---:|
| Selected outcomes | 20 |
| Minute bars | 1,660,136 |
| Label rows | 1,658,936 |
| Eligible label rows | 114,905 |
| Eligible training rows | 87,699 |
| Eligible validation rows | 15,826 |
| Eligible original-test rows | 11,380 |
| OOF comparison rows at 5-minute cadence | 17,540 |
| OOF positive jumps | 2,027 |

The development window is 2026-05-22 through 2026-07-22. The original test block
was exposed by an earlier noncanonical B0 run and is descriptive only.

### 3.3 Replacement OOT extract

| Item | Count |
|---|---:|
| Fresh trades | 2,080 |
| Bars including warmup | 195,495 |
| Minute-level holdout label rows | 180,598 |
| Eligible minute-level holdout rows | 7,058 |
| Markets with any rows | 17 |
| Markets with eligible rows | 13 |
| Evaluation rows at 5-minute cadence | 1,410 |
| Positive jumps | 130 |

The OOT window is 2026-07-23 through 2026-07-30, with warmup beginning
2026-07-22. Seven of the 20 frozen markets contribute no eligible OOT evaluation
rows.

### 3.4 News and KOL coverage

| Signal | Coverage |
|---|---|
| KOL association rule v3 | 3,394 associations; 3,217 matched posts; 18 of 20 markets matched |
| News association rule v1 | 543 retrieved rows; 465 unique in-window articles; 149 associations; 8 markets matched |
| KOL 5-minute feature table | 331,785 rows |
| News 5-minute feature table | 331,785 rows |

The curated association tables contain identifiers, timestamps, hashes, match
reasons, and limited source metadata; they do not contain the full post or article
text. Local raw/audit inputs may still be subject to upstream terms and are not
covered by a public release grant.

## 4. Instance structure

The prediction unit is `(venue, market_id, outcome_id, timestamp)`. The canonical
outcome is YES.

Core row families include:

- selected market metadata;
- one-minute trade-derived bars;
- 30-minute forward jump labels and eligibility flags;
- frozen temporal split assignments;
- market-only features;
- 5-minute KOL activity features;
- 5-minute news activity features; and
- deterministic KOL/news association tables.

The public-release candidate should use precomputed features, identifiers, labels,
and split assignments. Raw social-media or news text should not be distributed
without an explicit rights determination.

## 5. Label and eligibility construction

Trade prices are clipped to `[0.0001, 0.9999]` and transformed to log-odds. A minute
without a trade uses the most recent trade price and is flagged as
`forward_filled_last_trade`.

For timestamp \(t\), the target is one when the absolute log-odds move from \(t\) to
\(t+30\) minutes is at least four times the trailing standard deviation of up to 240
one-minute log-odds changes.

Eligibility uses only information available at or before \(t\):

- at least three trades in the trailing 240 minutes;
- at least 100 units of notional in the trailing 240 minutes; and
- exclusion of terminal boundary-price rows near scheduled close or at/after a
  known resolution time.

Forward liquidity is not used for eligibility. The feature builders recorded zero
future-event timestamp violations.

## 6. Feature families

### 6.1 Market features

The retained B0 model uses 11 features: price log-odds; momentum over 5, 30, and 120
minutes; realized volatility over 30 and 240 minutes; trade count and notional over
60 and 240 minutes; and minutes since the latest trade.

### 6.2 KOL features

KOL features aggregate post counts, unique handles, author concentration/entropy,
recency, history availability, and activity bursts over trailing windows. Follower
counts, engagement counts, and sentiment were excluded because no independently
validated point-in-time histories were frozen for them.

Among eligible development rows, 5,929 training rows, 2,241 validation rows, and 396
original-test rows had nonzero KOL activity in the previous 24 hours.

### 6.3 News features

News features aggregate article counts, publisher/category diversity, publisher
concentration/entropy, recency, history availability, and activity bursts.
Structured ticker sentiment was not included because none of the 20 event markets
had a canonical financial-symbol mapping.

Among eligible development rows, 1,635 training rows, 128 validation rows, and 216
original-test rows had news activity in the previous 24 hours.

## 7. Quality controls

KOL rule v3 was accepted after blind adjudication on 299 scored cases:

- precision 0.8850;
- recall 0.9365; and
- F1 0.9100.

News rule v1 was accepted after blind review on 99 scored cases:

- precision 0.9286;
- recall on hard retrieval candidates 0.9701; and
- F1 0.9489.

One uncertain case was excluded from each rule's scored denominator. Association
quality does not imply predictive utility; the news and KOL model candidates failed
their development promotion gates.

## 8. Splits and integrity

Development comparison uses five expanding-window folds with a 30-minute purge.
Candidate models use identical rows and labels. The original test block is
contaminated by prior exposure and cannot support an untouched claim.

The later OOT dataset was frozen before label prevalence or metrics were inspected.
It was evaluated exactly once with frozen B0 and consumed at
`2026-07-31T03:31:03.495303Z`. The consumption receipt sets
`rerun_permitted` to `false`. No feature, model, eligibility, association rule, or
hyperparameter may be selected from the OOT result.

## 9. Collection and provenance

Data were fetched through the authenticated findata API and frozen locally.
Prediction-market records originate from the provider's Polymarket surfaces; news
and KOL records come from the corresponding indexed provider surfaces. Timestamps
are normalized to UTC/RFC3339.

The exact source rows, code inputs, byte counts, and SHA-256 hashes used in the
study are recorded in:

- `data/v1/toy/frozen_manifest.json`;
- `data/v1/curated/kol_rule_v3_frozen_manifest.json`;
- `data/v1/curated/news_rule_v1_frozen_manifest.json`;
- `data/v1_oot_20260723_20260730/frozen_holdout_manifest.json`; and
- `eventx/release/v1/release_manifest.json`.

The separate all-market bulk fetch documented in `PROGRESS.md` is not part of this
frozen pilot release.

## 10. Known limitations and biases

- The cohort is small, recent, and limited to one venue.
- Selection favors markets with sufficient retained trading activity.
- Frozen categories are coarse and contain a known misclassification.
- Last-trade/forward-filled prices substitute for unavailable historical L2
  midpoint data.
- Only one 30-minute horizon is evaluated.
- OOT coverage is 13 markets and 130 positive labels.
- News matches cover only eight markets and have no structured ticker sentiment.
- KOL features capture aggregate activity rather than post semantics.
- Deleted-post rate was not measured.
- Provider indexing, timestamping, deletion, deduplication, and upstream coverage
  may introduce unmeasured selection bias.
- Public-post handles can still be identifiable even when post text is omitted.
- Political and geopolitical topics dominate the cohort semantically, despite the
  coarse frozen category labels.

## 11. Intended uses

Appropriate uses include:

- reproducing the frozen v1 pilot result;
- auditing leakage controls and association quality;
- studying calibration and temporal stability on the development folds; and
- serving as an engineering reference for a separately preregistered v2.

## 12. Out-of-scope uses

The dataset should not be used to:

- claim causal influence by a KOL or news source;
- identify a deployable or profitable trading strategy;
- target, rank, or profile individuals;
- manipulate prediction markets or front-run public information;
- infer performance on Kalshi, other time periods, or other horizons;
- make category-specific claims using the defective frozen category field; or
- tune another v1 model against either exposed/consumed test result.

## 13. Distribution and licensing

The present package is **not cleared for public redistribution**. No explicit data
license has been granted, and upstream rights have not been reviewed. Before public
distribution:

1. determine which features, identifiers, labels, code, and source metadata may be
   redistributed;
2. document findata, Polymarket, news-provider, and social-platform constraints;
3. select explicit code and data licenses consistent with those constraints;
4. exclude raw text or other restricted fields unless permission is documented;
5. complete a privacy and dual-use review; and
6. create a clean public bundle and test it without private API access.

## 14. Maintenance

No public maintainer, support window, update cadence, DOI, or archival location is
assigned yet. The internal canonical handoff is `PROGRESS.md`. Frozen v1 evidence
must not be modified in place; corrections require a new version and manifest.

Run:

```bash
python -m eventx.release.verify_v1_release
```

to verify the local release and consumed-holdout guard.
