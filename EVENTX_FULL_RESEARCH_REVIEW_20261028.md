# EventX: full research review and plan to raise its value

28 October 2026. Scope: the whole EventX programme (Track A news, Track B quote-change forecasting, live
runtime, integrity machinery, report). Based on `CURRENT_STATE.md`, the frozen results it links, the three
earlier reviews (`EVENTX_FINAL_REPORT_REVIEW_20261028.md`, `EVENTX_RESEARCH_GAP_ASSESSMENT_20261028.md`,
`EVENTX_ONLINE_RATE_REVIEW_20261028.md`) and two new descriptive analyses run for this review on
already-consumed data (§3). No protected data, live outcome, V4 input or unopened block was read; no model
was fitted; the live run was not touched.

## 1. Verdict

EventX is strongest as a **study in honest evaluation** and weakest as a **forecasting contribution**.

- Its evaluation discipline (frozen protocols, outcome-blind cohorts, evaluate-once receipts, hash-locked
  releases, preserved failures, claim-to-artifact checking) is well above what most published applied-ML
  finance work shows, and it is the project's most transferable asset.
- Its one positive predictive result, the quote-change booster, replicates against the *specified* baselines
  but, on new contracts, is not distinguishable from a contract's own online outcome rate once about an hour
  of outcomes exists. Post hoc, quote features look most useful when little contract-specific outcome
  history is available; their value after history accumulates remains uncertain on unseen contracts (§3).
  That is a narrower but sharper question than the headline "14.9% better than logistic".
- Track A's negative news result is credible for its representation (counts, conservative timestamps) and
  correctly scoped, but measurement quality (links, first-availability), not modelling, is what limits it.

As an undergraduate research report this is a good piece of work. As a paper it needs one focused question,
stronger references, and new data, all of which are achievable (§5).

## 2. Scorecard

| Dimension | Assessment | Main reason |
|---|---|---|
| Research question | Fair | Two tracks with different targets; Track B's target was chosen for forecastability, so its scientific motivation is thin |
| Evaluation integrity | **Excellent** | Frozen protocols, evaluate-once receipts, disclosed deviations, consumed-holdout discipline, claim checker |
| Strength of evidence (Track B) | Moderate | 18–35 contributing contracts per block, 7 dates, one venue; positive vs specified baselines, null vs online rate on new contracts |
| Strength of evidence (Track A) | Moderate (negative) | 4,651 markets, clear negative within representation; links/availability unverified |
| Baselines | Weak → improving | Primary comparator uses 9 of 18 inputs; online rate added post hoc; no matched-input or tuned alternatives |
| Novelty | Low (method), moderate (setting) | Standard HGB; expiring, thin prediction-market contracts and deployable timing are the distinctive parts |
| Prospective evidence | Pending | V02b runs to 29 Oct; laptop host; ~71% issuance at 28 Oct 11:12Z |
| Reproducibility | Good | Releases and code committed; claims 37/37; data/ is local only (not archived off-host) |
| Reporting honesty | Good | Limitations, post hoc labelling and failed attempts preserved; several overclaims already corrected |
| Practical value | Unshown | Activity forecasts lack a demonstrated decision use; no utility experiment |

## 3. New evidence from this review (descriptive, post hoc)

`eventx/tasks/analyze_v7_online_rate_replication_20261028.py` →
`data/v7/online_rate_replication_20261028/result.json`. Same online-rate definition as Table 8 (pseudocount 20
toward the stored global rate, 35-minute maturity), definitions fixed before the run, nothing refit.

**Booster vs online contract rate, three consumed blocks**

| Block | Contracts in booster training? | Booster LL | Rate LL | Gain | Contract CI | Contract × date CI |
|---|---|---:|---:|---:|---|---|
| May 13–19 (dev50, 30 contracts) | yes | 0.3583 | 0.3922 | 8.6% | [0.008, 0.060] | [0.002, 0.071] |
| June 1–7 (dev50, 18) | yes | 0.2931 | 0.3143 | 6.7% | [−0.006, 0.057] | [−0.018, 0.073] |
| June 8–14 (new, 35) | no | 0.4208 | 0.4231 | 0.5% | [−0.028, 0.033] | [−0.040, 0.041] |

**Gain over the online rate by the contract's matured outcome history at decision time (nats)**

| Matured outcomes | May 13–19 | June 1–7 | June 8–14 (new) |
|---|---|---|---|
| 0 (cold start) | 0.124 [0.011, 0.275] | 0.067 [−0.027, 0.164] | 0.138 [0.019, 0.261] |
| 1–11 (< 1 h) | 0.074 [−0.004, 0.156] | 0.087 [0.037, 0.143] | 0.098 [0.024, 0.173] |
| 12–47 (1–4 h) | 0.024 [−0.014, 0.066] | −0.003 [−0.076, 0.060] | −0.001 [−0.049, 0.039] |
| ≥ 48 (> 4 h) | 0.033 [0.008, 0.061] | 0.021 [−0.008, 0.060] | 0.001 [−0.031, 0.032] |

Reading (hypotheses, not findings; all strata are post hoc and the first two hold under 2% of rows: 473, 296 and 590 rows):
1. **Per-row gains are largest with little outcome history.** All six early-history cells (first two strata,
   three blocks) favour the booster by 0.07–0.14 nats; four of the six contract intervals exclude zero. Their
   weight in the aggregate differs sharply: early rows carry about 82% of the small aggregate gain on the new
   contracts, but only 4.5% (May) and 6.9% (1–7 June) in the familiar blocks, where the gain mostly comes after
   history has accumulated.
2. **The booster keeps a warm-period edge on its training contracts but not on the new ones.** One reading is
   that it partly learned contract-specific activity levels that do not transfer, which would fit the May
   training-excluded result (gain over logistic 3.5%, nonoverlap reverses). But the familiar and new cohorts
   differ in contracts and dates as well as training exposure, so this does not isolate a familiarity effect.
3. History strata restart at each block boundary, so "little history" means few matured outcomes in the
   analysed block, not a newly listed contract. The online rate forecasts from the first decision at its
   global prior; only its contract-specific part waits.

## 4. Main weaknesses, ranked by how much they limit the research's value

1. **No single sharp question.** The programme answers several loosely related questions. The data now point
   to one that is sharp and publishable: *when do pooled quote-state models add predictive value beyond a
   contract's own recent outcomes, and does that value transfer to unseen contracts?*
2. **Reference strength.** Every confirmatory comparison used references that do not learn from a contract's
   own outcomes. The online rate shows how much this matters. Future frozen studies must include it.
3. **Small, dependent evidence.** 18–35 contracts and 7 dates per block. A two-way interval against the
   online rate is ±0.04 nats; resolving 0.01-nat differences needs an order of magnitude more contracts and
   several more weeks (preliminary planning, `docs/EVENTX_NEXT_CYCLE_SPECIFICATION_DRAFT_20261028.md` §5).
4. **Selection by coverage.** 20–51% of scheduled decisions issued historically; most loss is inactive or
   expired contracts. Fine for a forecaster that abstains, but the target population must be defined
   explicitly (e.g. "active contract-hours") rather than inherited from gates.
5. **No demonstrated use.** Activity probability has no tested decision application, so "better forecasts"
   cannot be translated into value.
6. **Measurement limits in Track A.** Links reviewed only by assistant reviewers, zero exact-predicate links,
   median release-to-article lag ~3 h, Lumid PIT ingestion only from 17 May. Model changes cannot fix this.
7. **Infrastructure.** One laptop: swap stalls, sleeps, reboots and WS disconnects cost coverage and one
   whole run (V02). `data/` is not archived off-host, so the evidence base has a single point of failure.
8. **Breadth of branches.** V5/V6 news lines, KOL, the 120k trade classifier, Paper A and PORTEND dilute
   effort; several are closed or blocked by measurement gates.

## 5. Proposals to raise the value of the research

### 5.1 Before the 1 November report (no new data, no new cycle)

1. **Add the §3 results to report §6.4** as one paragraph and a small table, labelled post hoc. They turn a
   deflating null into a specific, interpretable pattern (outcome history; familiar vs new cohorts) and set up
   Further Work. Register the key numbers in `report/claims.json`.
2. **Reframe the Track B contribution** in the abstract and §1.3: "Post hoc analyses suggest that quote
   features are particularly useful when little contract-specific outcome history is available; their
   incremental value after substantial history accumulates remains uncertain on unseen contracts." Do not
   attribute the familiar/new difference to training familiarity.
3. **Lead the contribution list with the evaluation framework** (evaluate-once receipts, claim checker,
   preserved failures, clock-validated runtime); it is the most reusable output.
4. Fill the three pending evaluations exactly as frozen, whatever the sign, and keep their reporting
   separate from post hoc material.
5. **Back up `data/`** (results, ledgers, receipts; not raw archives) to an off-host location after
   close-out, and record its hash manifest. Without it the claims checker cannot be rerun anywhere else.

### 5.2 The next cycle: one focused confirmatory study (needs explicit authorization)

Study question: *when does information pooled across contracts add value beyond each contract's own
available history?*

- **Primary contrast:** booster given the online rate and its matured-outcome count (`hgb+rate`) versus the
  online rate alone, on genuinely new contracts and dates; two-way (contract × date) bootstrap. Include the
  rate and history count consistently in every arm, and add a recency-weighted rate prespecified on new
  development data (the current rate accumulates all eligible outcomes within a block).
- **Registered secondary contrasts:** (a) cold-start stratum (0–11 matured outcomes) where the booster is
  expected to win; (b) warm stratum, with an equivalence test against a margin justified in advance (for
  example from a practical-use criterion) and adequate power; this can show the difference is smaller than
  the margin, not that it is zero, and an inconclusive result remains possible (Lakens, 2017);
  (c) learner × input factorial
  (logistic, GAM, HGB; 9 vs full inputs; ± rate) with matched tuning budgets on purged forward folds.
- **Population:** define the target population as active contract-hours, select contracts from as-of
  metadata snapshots, one contract per event, prespecified strata (category, time to expiry, liquidity).
- **Size:** plan contracts, weeks and expected inactive losses jointly from development data; the
  one-week contract-only figure (~660) is a lower-quality starting point, not a plan.
- **Venue:** run historically on Polymarket first; add Kalshi as a registered transfer test only once
  semantics are harmonised.

This study would produce a result that is informative whichever way it comes out, which the current design
does not guarantee.

### 5.3 Make the forecasts useful: a decision experiment

Activity forecasts have a natural use: **allocating a limited monitoring or data-collection budget.**
Compare policies at equal total cost against uniform, round-robin, recent-activity and online-rate rankings.

Design trap: if the forecast needs fresh quotes from every contract to decide which to poll, those quotes have
already been bought. The experiment must therefore either (a) allocate expensive downstream monitoring or
analysis given an existing quote feed, or (b) simulate genuine polling with stale observations, charging each
feature refresh and updating outcomes only when the policy could observe them. Define "captured changes" in
advance (endpoint differences, distinct movements, or detection latency); overlapping 30-minute labels can
otherwise count one movement repeatedly. A credible gain would show monitoring utility, not trading profit.

### 5.4 Track A: fix measurement before modelling

- Build a small, independently human-annotated gold set of contract–event links (a few hundred pairs, two
  annotators, agreement statistics), sampled across many independent event episodes. Record event time,
  publication time and strategy availability separately: annotators cannot reconstruct historical
  availability without supporting records (feed receipts, archived timestamps).
- Use event types with precise timing (scheduled releases, sports events, court rulings) in the spirit of
  Croxson and Reade (2014) to test *information incorporation* with an identified event clock.
- Re-test news only against the strongest market-only reference (booster + online rate), on identical rows,
  with timestamp-shift and irrelevant-news falsification controls.
- Report V4 exactly as frozen; whichever way it lands, scope it to its representation.

### 5.5 Infrastructure and openness

- Run the live runtime on an always-on server with a disciplined clock (chrony/NTP), supervised restarts and
  monitoring; laptop runs should be treated as rehearsals.
- Package a **documented, legally distributable benchmark**: frozen cohorts, point-in-time quote features,
  targets, splits, the evaluate-once harness and the claim checker, with strong references including the
  online rate. To count as a research contribution rather than good engineering it must show what it detects
  or enables that existing workflows miss: e.g. controlled leakage and timing failures it catches, reproducible
  comparisons, and a successful independent replay. Keep server, benchmark and scope-narrowing as separate
  deliverables rather than expanding everything at once.

### 5.6 Narrow the programme

Close or park branches that are blocked by measurement gates or have no path to a claim: V5/V6 news
variants, KOL, the 120k trade classifier (keep its frozen record), and Paper A until the news measurement
gold set exists. Concentrate on one Track B study, one decision experiment and one Track A measurement study.

## 6. Suggested positioning after the next cycle

"In thin, expiring prediction-market contracts, a pooled quote-state model's predictive value over each
contract's own available outcome history is concentrated where history is short and does (or does not) transfer to unseen
contracts; under realistic availability and abstention constraints this translates into X% more captured
changes at a fixed monitoring budget." Target: an applied forecasting or market-microstructure venue, with
the evaluation framework and benchmark as secondary contributions.

## 7. Priorities at a glance

| Priority | Action | Cost | Value |
|---|---|---|---|
| 1 | Add §3 results and reframed contribution to the report (post hoc) | hours | high |
| 2 | Off-host backup of `data/` results with hash manifest | hour | high (risk) |
| 3 | Freeze the focused next-cycle study (§5.2) with an equivalence margin | days | very high |
| 4 | Monitoring-budget decision experiment (§5.3) | days–weeks | high |
| 5 | Human gold set for news links and availability (§5.4) | weeks | high for Track A |
| 6 | Server-hosted runtime and benchmark release (§5.5) | weeks | medium–high |
| 7 | Close dormant branches (§5.6) | hour | medium (focus) |

## 8. Revision note (29 October)

Revised after `EVENTX_ADDITIONAL_WORK_ASSESSMENT_20261029.md`: early-history gain shares added (82% new;
4.5% and 6.9% familiar), training-familiarity attribution withdrawn, "cold start" redefined as a block-reset
history, equivalence wording corrected (margin, not exact null), recency-weighted rate added, monitoring
design trap and cost accounting added, news-availability limits and benchmark evidence requirements added.
Priority order adopted: finish and preserve the current report; one pooled-versus-own-history study; one
credible monitoring experiment; defer richer news models and optional branches.
