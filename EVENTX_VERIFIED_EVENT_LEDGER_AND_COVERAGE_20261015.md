# EventX: source verification, event ledger and coverage

15 October 2026 · Opened historical development only · Current package: `data/v7/verified_event_ledger_20261015_v02/`.

## Main result

**The 12 jointly reviewed articles cover 95 distinct forecast rows, including 27 large-movement labels and 68 non-movements.** Excluding the ambiguous Kalshi zero-basis-point contract leaves 48 rows (11 movements). Also excluding the article with the PPI summary discrepancy leaves 44 rows (11 movements). These are coverage counts, not forecasting performance.

The ledger identifies seven referenced event identities: six have an official release, statement or event programme; the Visser podcast is identified only by the original reporting. Three official releases have exact announced public clocks. Several article-to-event mappings remain contextual, four originals could not be recovered, and no historical first-version text is authenticated. The verification task is complete with these explicit unresolved fields; the evidence is not fully certified.

**Timing is the principal practical bottleneck:** none of the 12 articles arrives within an hour of its cached publication timestamp. The seven CPI/PPI-linked articles arrive at least 120.25 minutes after their most recent linked official release. This establishes delayed access, not the absence of any residual predictive value.

## 1. What was done

1. Preserved the two agents’ original judgments and selected their unchanged 32 agreed material-context links. Disputed links were not promoted.
2. Inspected original publisher pages and official BLS, BEA, Federal Reserve, ECB and CENTCOM evidence. Source findings are retrospective diagnostics; they do not replace the historical feed or change `available_at`.
3. Recorded release identities, reporting roles, source clocks, explicit uncertainty and mixed-event references in a separate versioned ledger.
4. Receipted ledger hashes, coverage rules and input hashes before the new counts. Prior development and aggregate outcome exposure is disclosed; this is not a new blinded preregistration.
5. Reconstructed eligible rows from the existing opened examples and deduplicated by contract and decision time. Every one of the 32 pair-level counts reproduces the earlier inventory.

Eligibility is inherited example eligibility plus price age ≤5 minutes, at least three trades in the preceding 60 minutes, and an article available within the preceding 30 minutes. This report covers 11–21 July across opened market groups. **None of the reviewed fresh rows belongs to original fold 5.** This broader population cannot replace the original held-market evaluation.

## 2. Event ledger and verification status

| Event identity | Public disclosure evidence | Status and interpretation |
|---|---|---|
| June CPI | [BLS archived release](https://www.bls.gov/news.release/archives/cpi_07142026.htm), 14 July 12:30 UTC | Release identity, values and clock verified: headline −0.4% monthly; +3.5% annually. Repeated CPI stories share this release. |
| June PPI | [BLS archived release](https://www.bls.gov/news.release/archives/ppi_07152026.htm), 15 July 12:30 UTC | Release identity, values and clock verified: −0.3% monthly; **+5.5% annually**. |
| May core PCE | [BEA release](https://www.bea.gov/news/2026/personal-income-and-outlays-may-2026), 25 June 12:30 UTC | +3.4% annually. The July article recaps an older release. |
| Warsh at Sintra | [ECB programme](https://www.ecb.europa.eu/press/conferences/html/20260629_ecb_forum_on_central_banking.en.html), 1 July | Official panel identity/schedule verified. The statement is attributed by [contemporaneous reporting](https://au.finance.yahoo.com/news/kevin-warsh-fed-will-not-be-comfortable-with-inflation-above-2-183000837.html/); original recording and exact utterance clock remain unverified. |
| Warsh congressional testimony | [Federal Reserve prepared remarks](https://www.federalreserve.gov/newsevents/testimony/warsh20260714a.htm), 14 July | Price-stability statement verified in official text. Identical prepared remarks submitted on 15 July; exact first-public clock unknown. |
| Visser forecast | [Original Benzinga article](https://www.benzinga.com/crypto/cryptocurrency/26/07/60418617/bitcoin-plummets-below-63000-why-is-btc-going-down-again), 13 July, referring to 12 July podcast | Prior podcast and 35–40% hike forecast identified in original reporting. Recording unavailable; reported date only. |
| US military strike statement | [CENTCOM release](https://www.centcom.mil/MEDIA/PUBLIC-RELEASES/Article/4540919/us-forces-finish-latest-round-of-strikes-against-iran/), 11 July | Official statement reports approximately 140 targets. Does not verify every conflict claim or a first-public clock. July article mixes later developments. |

“Verified” here describes the specific source fact in the table. It does not establish article novelty, an independent statistical event, information surprise or a causal effect on prices.

## 3. Article ledger

The complete [article ledger](data/v7/verified_event_ledger_20261015_v02/article_ledger.jsonl) preserves cached text, both clocks, source URLs, event references, delay calculations and flags. The [event ledger](data/v7/verified_event_ledger_20261015_v02/event_ledger.jsonl) records source evidence separately.

| Article ID | Referenced events | Publication → system (min) | Rows | Movement rows | Original access |
|---|---|---:|---:|---:|---|
| 214206137 | strike statement | 92.02 | 6 | 1 | Unrecovered |
| 214277524 | Sintra | 238.14 | 11 | 11 | Publisher page |
| 214380179 | Visser podcast | 621.31 | 10 | 1 | Publisher page |
| 214861512 | CPI, testimony | 80.87 | 10 | 0 | Unrecovered |
| 214994929 | CPI | 101.45 | 5 | 1 | Publisher page |
| 215055591 | CPI | 232.66 | 7 | 1 | Publisher search body |
| 215155309 | CPI, testimony | 183.76 | 12 | 3 | Unrecovered |
| 215383892 | May PCE | 236.43 | 9 | 6 | Publisher page |
| 215441179 | CPI | 211.02 | 12 | 0 | Unrecovered |
| 215472946 | PPI, CPI, testimony | 148.67 | 6 | 0 | Publisher page |
| 216490787 | CPI, PPI | 102.18 | 5 | 2 | Syndicated excerpt |
| 218417346 | testimony, Sintra | 176.93 | 2 | 1 | Publisher page |

Rows are deduplicated within each article. Article and event tables can overlap; their totals must not be added without a union of decision keys. Secondary event references recovered from full articles are conservative split safeguards; they are not newly validated predictive links.

## 4. Coverage after review and source flags

| Population | Articles | Links | Markets | Unique rows | Movements | Non-movements |
|---|---:|---:|---:|---:|---:|---:|
| All agreed material context | 12 | 32 | 4 | 95 | 27 | 68 |
| Also exclude PPI summary discrepancy | 10 | 18 | 3 | 44 | 11 | 33 |
| Exclude ambiguous H0 contract | 11 | 20 | 3 | 48 | 11 | 37 |

The all-agreed set spans five arrival/decision dates; removing H0 leaves four. Sensitivity exclusions are driven by contract/source uncertainty, not label balance. They do not redefine the original protocol.

### Reducing repeated observations

| Descriptive construction | Rows | Movements | Non-movements |
|---|---:|---:|---:|
| All reviewed arrival windows | 95 | 27 | 68 |
| Earliest reviewed arrival per conservative group and contract | 14 | 6 | 8 |
| Same earliest-arrival construction excluding H0 | 10 | 4 | 6 |
| Greedy 30-minute spacing within each contract, all agreed | 32 | 10 | 22 |

Earliest-arrival landmarks use the first eligible decision in the earliest reviewed article’s window, with no substitution of later arrivals. Thirty-minute spacing removes within-contract target overlap only. Neither procedure creates independent information events.

## 5. Event dependence and split safeguards

Mixed articles connect CPI, PPI and policy statements. Keep each connected group together in a later split. This deliberately conservative grouping can merge distinct economic events; **four groups is not an estimated effective sample size**.

| Group to keep together | Articles | Unique rows | Movements |
|---|---:|---:|---:|
| strike statement | 1 | 6 | 1 |
| May PCE | 1 | 9 | 6 |
| CPI, PPI, Sintra, testimony | 9 | 70 | 19 |
| Visser podcast | 1 | 10 | 1 |

All contracts concern the same July FOMC decision. Cross-contract observations and even these four groups can share calendar shocks. No valid effective sample size, minimum detectable effect or confirmatory confidence interval is established. The 95 rows and 27 movement labels must not be described as 95 events or 27 independent shocks.

## 6. Timing diagnosis

Across the 12 reviewed articles, publication-to-system lag is **80.87 / 180.34 / 621.31 minutes** (minimum / median / maximum). Zero arrive within 30 or 60 minutes; six within 180 minutes.

For the seven CPI/PPI-linked articles, delay from the most recent linked official release is **120.25 / 619.66 / 2185.54 minutes**. Mixed-release articles use the later verified release, so this understates the age of any older CPI component. None arrives within 30 minutes of that release.

The July 13 Warsh article recaps the July 1 forum. The July 19 article discusses earlier testimony and other prior statements; it is not a new July 19 policy announcement. The July 15 PCE article recaps the June 25 release. New article IDs cannot reset these information clocks.

### Were markets observable when the official releases occurred?

A separate hypothetical source-capture diagnostic applies the same freshness/trading screen in [release, release+30m) over all five original inventory contracts:

| Official release window | Fresh eligible rows | Movements | Non-movements |
|---|---:|---:|---:|
| CPI | 17 | 5 | 12 |
| PPI | 11 | 5 | 6 |

These 28 rows include both labels and occur on only two release dates; the candidate H0 contract is included in this observability diagnostic. They show opportunities for timely capture, **not news performance or usable historical feed observations**. Official sources were inspected retrospectively and are not inserted into historical features. A new capture protocol would be required to use them prospectively.

## 7. Data-quality findings

- **PPI summary discrepancy:** article `215472946` attaches a decline to the 5.5% annual figure. The [original publisher](https://www.investing.com/analysis/nasdaq-forecast-ndx-extends-gains-after-cooler-ppi-200683982) and BLS identify an annual increase. Flag the cached summary; do not silently repair historical input text or extract a signed annual surprise from it.
- **Ambiguous contract:** `KXFEDDECISION-26JUL-H0` still lacks official rules/subtitle. The read-only official market API request failed in the sandbox with DNS resolution, then returned HTTP 404 on an approved network retry. Unaffiliated descriptions suggesting “hold” are insufficient to establish the exchange predicate.
- **Market-odds contamination:** the Zacks CPI article quotes Polymarket; other articles mix independent economic observations and market expectations. Separate those evidence spans before any content feature comparison. Neither generic relevance nor the existence of a source citation proves external novelty.
- **Source access:** six original pages, one original-publisher search body and one syndicated excerpt were inspectable. Four exact originals remained unavailable. Present-day pages do not authenticate historical article revisions.

## 8. Research decision and next deliverable

**Use this set for descriptive event analysis and pipeline debugging. Do not use it to claim a confirmed news gain.** Both outcome classes are now represented, but repeated, delayed information dominates the evidence set and no independent evaluation population has been established.

The next useful experiment is a separately recorded cohort of original releases/statements captured promptly, across additional dates and preferably several FOMC cycles. Preserve original text and receipt times, record the first observed source version, and collect price/trade freshness at arrival. Check event yield before selecting the evaluation span.

Keep the selected raw `condition_120k` market model fixed. A subsequent unsigned-content development pilot should compare market → exposure/timing → reviewed evidence on identical rows. Exact YES/NO direction is optional for the current absolute-movement target; reliable event identity, text and timing are the immediate priorities. No additional model search was performed here.

V4 remains a separate frozen experiment. Its sealed future payload and one-shot consumption sequence were not accessed or changed. No consumed holdout was reopened.

## 9. Reproducibility and remaining uncertainty

- [Current package index](data/v7/verified_event_ledger_20261015_v02/INDEX.md)
- [Source findings and recovery attempts](data/v7/verified_event_ledger_20261015_v02/source_findings.json)
- [Coverage receipt before new counts](data/v7/verified_event_ledger_20261015_v02/coverage_receipt_before_new_counts.json)
- [Machine-readable report](data/v7/verified_event_ledger_20261015_v02/report.json)
- [Decision-row coverage and memberships](data/v7/verified_event_ledger_20261015_v02/row_coverage.jsonl)
- [Version correction](data/v7/verified_event_ledger_20261015_v02/VERSION_NOTE.md)

Version 1 correctly computed reviewed-arrival coverage but mislabeled a four-reviewed-contract release diagnostic as ALL_FIVE. Version 2 includes the fifth inventory contract there: CPI coverage changes 16→17 rows and 4→5 movement labels; PPI and all arrival counts are unchanged. Both versions are preserved. This correction is not model selection.

The ledgers are assistant source assessments, not independently adjudicated human gold. Forecast models fitted: **0**. New forecast metrics: **none**. All 32 inherited pair counts reproduce, ledger hashes remain unchanged after counts, and delivery checks reconcile the released tables and memberships.
