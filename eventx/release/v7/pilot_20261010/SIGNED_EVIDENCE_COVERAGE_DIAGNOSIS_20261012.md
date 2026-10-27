# Signed-evidence coverage diagnosis

**Date:** 12 October 2026  
**Status:** Completed on already opened development data. No model refitting, new forecasting evaluation, source fetch or holdout access.

## 1. Main finding

The original **1,559 automatic signed associations → 21 training rows → 0 evaluation rows** result is reproduced exactly.

Two problems require attention:

1. **Coverage:** article arrivals rarely coincide with eligible decision rows for the markets selected by the existing forward fold. Only 28 signed associations survive the evaluation-date and market-group restrictions; all 28 miss eligible decision rows.
2. **Evidence quality:** the six associations producing the 21 training rows do not establish their exact contract implications in the supplied text, according to this assistant inspection. Several have directly traceable extraction defects. This inspection is development error analysis, not independent annotation or a formal error-rate estimate.

The zero coverage is reproduced by independently tracing event-to-row membership and by the original feature aggregator. No discrepancy was found in that mapping. The narrow exposure mask removes zero signed rows, and opposite-sign cancellation does not explain absence.

## 2. What was traced

The diagnosis preserved the original deterministic extractor, market groups, forward-fold dates and 30-minute window:

`decision_at - 30 minutes < article_available_at <= decision_at`

Equivalently, a signed article may enter decisions in `[available_at, available_at + 30 minutes)`. Publication time is not substituted for availability time.

The trace covers:

`deduplicated articles → existing article–market associations → automatic exact nonzero direction → fold dates → held market group → eligible decision row → seven signed features → exposed comparison row`

Only market/time/fold keys were accessed in existing OOF records, and market/time/group keys in existing eligible examples. Outcome and forecast fields were not accessed. The existing examples already embody upstream target construction and a price-age filter of at most 30 minutes; the diagnostic does not relax their eligibility.

Twenty-six locked input/artifact hashes were checked before computation. All **479,179** association timestamps match their indexed source document's availability timestamp, and within-market event ordering passes. Original 1,559/21/0 counts and 4,577/5,388 exposed-row counts match exactly.

## 3. Initial information funnel

| Stage | Count | Interpretation |
|---|---:|---|
| Deduplicated development documents | 147,377 | Original source identity and conflict policy retained |
| Existing article–market associations | 479,179 | Legacy candidate links, not validated relevance |
| Automatic `none` | 437,447 | Unsupported predicate, context trap or period mismatch |
| Automatic `material` | 40,173 | Context retained descriptively; excluded from signed features |
| Automatic `exact` with nonzero direction | 1,559 | Heuristic labels, not validated exact evidence |
| Distinct articles behind those signed associations | 400 | Article IDs, not independent information episodes |
| Distinct markets behind those signed associations | 32 | Restricted macro predicate support |

The 1,559 signed associations comprise 363 Kalshi and 1,196 Polymarket links; 1,155 have positive direction and 404 negative direction. There are zero duplicate document/market/availability keys in this signed subset. Consequently, duplicate association records do not explain the large headline count.

The signed extractor emits 757 links from `commentary_or_other`, 255 from `general_market_expectation`, 322 from `observed_action`, 177 from `forecast`, and 48 from `observed_measurement`. An automatic exact direction therefore does not imply a newly reported factual observation or measured information surprise.

## 4. Exact training and evaluation funnels

These are counts of **associations**, with article and market counts reported separately.

| Stage | Training fold 4 | Evaluation fold 5 |
|---|---:|---:|
| All automatic signed associations | 1,559 | 1,559 |
| Availability window overlaps fold dates | 294 | 200 |
| Also matches held market group | 92 | 28 |
| Reaches an eligible decision within 30 minutes | 6 | 0 |
| Distinct contributing articles | 5 | 0 |
| Distinct contributing markets | 3 | 0 |
| Covered comparison rows | **21 / 4,577** | **0 / 5,388** |

Fold 4 spans **30 June–11 July 2026 UTC**, using market group 3. Fold 5 spans **11–22 July 2026 UTC**, using market group 4. Both end dates are exclusive. A preceding arrival can count if its 30-minute window overlaps the fold boundary.

### Exclusive reasons, applied in date → group → row order

| Reason | Fold 4 associations | Fold 5 associations |
|---|---:|---:|
| Outside fold clock window | 1,265 | 1,359 |
| In the clock window, different held market group | 202 | 172 |
| Correct dates/group, market has no eligible OOF rows in fold | 13 | 12 |
| Correct dates/group, market has rows but none within 30 minutes | 73 | 16 |
| Reaches signed features | 6 | 0 |
| **Total** | **1,559** | **1,559** |

This partition explains every signed association exactly once. The JSON report also includes overlapping flags; those flags must not be added together or interpreted as causal attribution.

### Why the last 28 evaluation associations disappear

- **12 associations across two June-meeting contracts:** neither market has eligible evaluation-fold rows. All 12 article arrivals follow both the cached terminal timestamp and last observed trade. This supports a historical window-mismatch diagnosis; cached timestamps do not certify historical trading status.
- **16 associations across three other contracts:** the market has evaluation rows, but no row falls within the article's 30-minute window. Eleven have a later eligible decision, with gaps of **55.156204–4,315.156204 minutes** and median **2,510.283654 minutes**. Five have no later decision in the fold. Sparse eligible decision support is observed directly; the trace does not establish whether each upstream gap arose from trade staleness, missing support or another eligibility condition.

For example, article `214103556`, available on 13 July at 08:02:33 UTC, is linked to the July 25 bp cut contract. Its first eligible evaluation decision is 18:00 UTC, approximately **597.44 minutes** later. That article cannot enter a 30-minute trailing window at that decision.

## 5. How much does market-group selection matter?

The original OOF scheme changes both date range and held market group between folds. It is not a purely temporal comparison of the same market population.

Using **existing eligible example keys** from all groups during the same dates, with unchanged clocks and 30-minute windows, gives:

| Descriptive coverage | Fold 4 dates | Fold 5 dates |
|---|---:|---:|
| Associations reaching any group's eligible examples | 11 | 12 |
| Distinct articles | 9 | 5 |
| Distinct markets | 7 | 7 |
| Unique covered example rows | **42** | **55** |
| Original held-group covered rows | 21 | 0 |

Thus the fold-5 group restriction excludes the 55 rows with signed features that exist elsewhere in the same historical date interval. However, coverage remains small even across groups. Removing the group restriction would not by itself establish a useful or valid news signal.

These are coverage counts only. No additional baseline predictions were generated, no labels were inspected and no replacement split was evaluated. Any future population or split redesign needs a separate version and evaluation plan.

### Coverage in every existing forward fold

| Fold | News-exposed OOF rows | Signed rows | Contributing articles | Contributing markets |
|---|---:|---:|---:|---:|
| 1 | 4,287 | 24 | 2 | 2 |
| 2 | 8,662 | 63 | 9 | 3 |
| 3 | 1,401 | 2 | 1 | 1 |
| 4 | 4,577 | 21 | 5 | 3 |
| 5 | 5,388 | 0 | 0 | 0 |

The earlier folds also have low article diversity. Multiple adjacent rows from one arrival should not be counted as independent evidence.

## 6. Semantic inspection of all training hits

All six associations responsible for the 21 training rows have positive signs. The supplied text does not establish the exact contract implication in any of the six under this assistant inspection.

| Article ID and supplied wording | Automatically supported contract | Rows | Identified problem |
|---|---|---:|---|
| `197135093`: “lower courts” in a Lisa Cook legal-case story | July **50+ bp cut** | 5 | Article-wide `lower*` action matching confuses courts with lowering rates; `50+` bucket is unparsed |
| `201331696`: “Fed rate cut odds” in crypto/payroll commentary | July **50+ bp cut** | 4 | Generic cut odds do not bind meeting or size; `50+` is unparsed |
| `199965294`: “Fed has cut its target rate to 3.75%” | **1 cut** in 2026 | 5 | Past rate level does not identify the exact annual count or period |
| Same article `199965294` | **2 cuts** in 2026 | 5 | Same generic statement gives YES to two different count buckets |
| `211002653`: “futures traders cut risk” | **1 cut** in 2026 | 1 | Wrong action subject/object; a separate Fed mention triggers the rate-cut rule |
| `202999082`: “Fed rate cut bets ease” | **2 cuts** in 2026 | 1 | Modifier/direction and exact count are not bound |

The original extractor accepts a contract with an empty parsed basis-point list as having no bucket restriction. Its parser misses `50+ bps`, so the generic-cut path can label that contract exact. It also does not parse annual rate-cut counts and matches action words across the full article instead of binding them to a Fed action clause.

The full supplied snippets, exact evidence spans, automatic decisions and assistant findings are preserved in `semantic_inspection.jsonl`. Independent reviewers must assess a new version before semantic accuracy is claimed. This inspection does not estimate precision over all 1,559 associations or retrieval recall.

## 7. Availability delay

Across the **400 distinct signed articles**, publication-to-availability delay is:

| Statistic | Minutes |
|---|---:|
| Minimum | 25.555901 |
| Median | 255.815510 |
| 90th percentile | 621.339704 |
| Maximum | 1,431.111920 |
| Articles delayed more than 30 minutes | **399 / 400** |

These are article-weighted statistics, distinct from the earlier 30-article pilot. They indicate that system arrival often occurs hours after publication. They do not prove that changing clocks would recover forecasting value, or identify first-public information time. No publication-clock backdating or window widening was performed.

## 8. What to do next

1. **Version the extractor before another forecasting fit.** Require subject/action/object binding, explicit meeting/reference-period binding, parsed `50+`/`>25`/exact-size buckets and exact annual counts. Unsupported predicates should abstain. Preserve the current v0.2 code and trial.
2. **Build a focused error/evidence packet.** Include these six training hits, the 28 evaluation-window candidates, independently checked exact positives and retrieval misses. Review original evidence spans and distinguish observed information, attributed forecasts, context and repeated coverage. The six failures alone are a useful debugging set, not a sufficient validation benchmark.
3. **Repeat coverage tracing before scoring.** Measure distinct supported article arrivals and contract episodes as well as rows. Keep availability clocks and price-freshness rules explicit. If valid coverage is still negligible, the forecasting comparison remains uninformative.
4. **Design a separate event-based pilot on opened data.** Diagnose whether verified arrivals have executable, fresh market observations at the intended landmark. Prespecify any new population or horizon; report observable-event yield and attrition before model selection. The current all-group counts justify investigating this design, not silently changing the existing split.
5. **Proceed to matched forecasting only when the new features reach both fitting and evaluation rows with enough distinct verified events.** Compare the strong market plus exposure/timing control with the same model plus evidence on identical keys. Set effect-size, event-yield and dependence-aware inference requirements before a new confirmatory freeze. V4 remains unchanged.

**Immediate deliverable:** a separately versioned predicate-binding extractor and a reviewed coverage pilot. The existing 0.0000044814-nat score difference cannot establish incremental news performance because the evaluated signed feature columns are all zero.

## 9. Reproducible package

- Data: `data/v7/signed_evidence_coverage_diagnostic_20261012/`
- Exact counts/funnels: `report.json`
- All 1,559 association traces: `signed_association_trace.jsonl`
- All covered OOF row traces across five folds: `covered_row_trace.jsonl`
- Field-access and source-hash receipt: `input_receipt.json`
- Semantic inspection: `semantic_inspection.jsonl`
- Interpretation and supplementary counts: `coverage_interpretation.json`
- Code: `eventx/tasks/diagnose_v7_signed_evidence_coverage_20261012.py` and `eventx/tasks/interpret_v7_signed_evidence_coverage_20261012.py`
- Hash manifests: `manifest.json`, `interpretation_manifest.json`, `publication_manifest.json`

The consumed OOT and historical holdouts and sealed V4 confirmation payloads were not accessed. No model was fit, no performance was recomputed and no original frozen source, feature, split or prediction artifact was changed.
