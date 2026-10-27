# EventX: paper roadmap and proposed next study

**Date:** 9 October 2026  
**Basis:** User-supplied research recommendations, the current handoff, frozen historical artifacts, and a targeted check of related primary research.  
**Status:** Concrete working roadmap and V7 design proposal. V7 has no collection launch, frozen protocol, selected cohort, model fit, new annotations, or evaluation. The existing V4 protocol remains controlling for its prospective study.

## 1. Recommended emphasis

Develop **Paper A first**, using the completed historical study and carefully scoped opened-development evidence. Prepare an event-based information-absorption study as the next research design. The contract-aware evidence benchmark is a prerequisite for that design and may become Paper C if it develops sufficient independent coverage.

The overarching question is:

> When, and under what measurable conditions, does external news provide incremental predictive information beyond observed prediction-market history?

“Why” is a research ambition. Existing forecast comparisons identify performance differences and measurement limitations; they do not establish the causal reason news failed. Availability, relevance, novelty, and assimilation provide an organizing framework and hypotheses for new comparisons.

Two distinctions should remain visible throughout the paper: stronger market modeling has improved opened-data performance, while additional news information remains unconfirmed; and a source feed becoming observable to EventX is different from information first becoming public.

## 2. Evidence that motivates the direction

| Evidence | Exact result, rounded | Permitted interpretation |
|---|---|---|
| V3.1 matched development | 1,460,454 rows; news AP difference −0.001916; Brier improvement −0.000284; all five gates failed | This frozen news-count representation failed promotion |
| V3.1 historical holdout | Only B0 evaluated; AP 0.171628; Brier 0.107107; 211,718 rows / 300 markets | Absolute performance of the selected market-only forecast, with the disclosed receipt-order deviation |
| V5 paired model diagnostic | 364,903 rows / 1,135 contracts; no-terminal logistic LL 0.451070 versus tree 0.407391; 9.683467% reduction | Nonlinear market modeling is promising on opened data |
| Latest V5 same-row news comparison | 5,388 observed-article fold-5 rows; market LL 0.243727, context 0.243985, news 0.244576 | Selected news did not beat either matched control; these are adaptive opened-data results |
| V6 strict link audit | 39/40 conservative relevance errors in its fixed strict top-one frame | The tested acceptance policy failed its specific audit; this is not a universal error rate for all retrieval |
| V6 relaxed review | 26 material-predicate pairs from five articles; 102 total reviewed pairs | Development evidence for a revised rubric; insufficient diversity or independence for a new benchmark claim |
| V4 prospective design | 470 Polymarket markets; `[2026-09-06, 2026-10-30)` UTC; primary B3 versus B0 | Independent prospective result remains pending under the frozen protocol |

Canonical sources: [V3.1 development](data/v3_1_historical/primary/development/selection_result.json), [completed historical manuscript](portfolio/EVENTX_HISTORICAL_PAPER_DRAFT_20261004.md), [V5 paired diagnostic](data/v5/no_terminal_baseline_diagnostic_20261009/report.json), [same-row comparison](data/v5/method_screen_observed_row_join_20261009/report.json), [V6 strict audit](eventx/release/v6/BOUNDED_AUDIT_RESULT_20260917.md), [relaxed review](data/v6/relaxed_adjudication_20260927/report.json), and [V4 protocol](eventx/release/v4/protocol.json).

No new current collector-status claim is made in this roadmap. The latest operational check is recorded separately in the [status report](MARKET_NEWS_RESEARCH_STATUS_20261009.md).

## 3. Paper A: controlled evaluation of incremental news value

**Working title:** *Does Timestamped News Improve Short-Horizon Prediction-Market Repricing Forecasts? A Controlled Empirical Evaluation.*

### Research contribution

The paper measures the performance of specific news representations under conservative information clocks and compares them with executed-market history. The baseline-strength and exposure-control findings explain why the choice of comparator matters. Gradient boosting is an established method; the contribution lies in the evaluation and empirical findings.

Use three clearly labeled evidence blocks:

1. **Completed historical study:** V3.1's prespecified development comparison, failed B1 promotion, B0-only one-shot holdout, and disclosed deviation.
2. **Opened development extensions:** V4 discovery and V5 market-model, context, timing, and semantic comparisons. Report adaptive search, future-text representation fitting, source limitations, and descriptive intervals explicitly.
3. **Prospective study:** include V4 only after its collection audit, receipt, and one-shot pipeline. If source requirements fail, record confirmation incompleteness. Its cohort, feature ladder, models, and primary contrast are those already frozen.

The blocks use different cohorts, representations, and selection histories. They should have their own tables and claims; they cannot be pooled into one estimated news effect or called equivalent replications. The V4 frozen market control remains its own comparator. The later V5 stronger booster supplies exploratory context, not a replacement V4 control.

### Claim discipline

| Tempting claim | Claim supported now |
|---|---|
| News does not improve prediction markets | The tested news-count candidate failed development promotion; the richer opened-data candidates have no stable increment over their controls |
| Nonlinear models are 9.68% better on new markets | The paired no-terminal tree reduced opened-development log loss by 9.68%; independent confirmation of that redesigned baseline is outstanding |
| Semantic matching caused the forecast failure | A strict linker failed its audit; its contribution to forecasting failure has not been isolated |
| Prices fully absorb public information | Current results cannot establish informational efficiency across all sources, horizons, or contracts |
| The historical holdout confirms the negative news effect | The historical holdout evaluated B0 only |
| A nonsignificant result establishes no useful news value | Useful-gain exclusion requires an appropriate upper confidence bound below a prospectively fixed effect threshold |

### Manuscript deliverables

Retain the existing historical draft and produce a separately versioned expansion. Prepare a matched-comparison table with cohort and evidence status in every panel; a baseline-strength figure; a documented information funnel; and a linking-error taxonomy. The funnel must use counts from a single defined sample at each stage. Counts from V3.1, V5, and V6 cannot be concatenated as though the same articles passed through all stages. Existing model intervals should retain their stated limitations; the word “valid” should be reserved for uncertainty appropriate to the declared claim.

Liquidity and information-role plots from a later study belong in that study's results. Existing descriptive strata may motivate hypotheses if they are marked exploratory and do not drive a protected-data selection.

## 4. V7 forecasting proposal: M / E / T / R / S

V7 is a proposed separate cycle that develops the V6 measurement work. Its name does not supersede V5/V6 controlling designs or release protected data. The new source, cohort, target, linker, features, model, inference, and untouched evaluation interval require a complete new manifest before launch.

### Population and feature ladder

Define the supported feed universe, active contracts, decision grid, market families, story episodes, and coverage policy before outcomes. All compared models use the same eligible rows.

| Arm | Definition | Information available at prediction time |
|---|---|---|
| M | Strong market-only model | Price level, momentum, trailing volatility, trade count/notional, trade age; additional fields only if their arrival and version are verified |
| M+E | Exposure-context correction | Coverage-qualified article occurrence and fixed feed/source/calendar context |
| M+E+T | Timing control | Time since observed arrivals and intensity within fixed trailing windows |
| M+E+T+R | Contract applicability | Exact subject, predicate, episode, period, evidence role, and explicit uncertainty |
| M+E+T+R+S | Signed new evidence | Supported direction and magnitude relative to an available prior, with novelty and duplicate/update lineage |

**Critical definition for E/T:** use a declared feed or a broad mapping fixed independently of semantic judgments. Preserve the same article opportunity set for controls and semantic models. E/T must not use the R classifier, its acceptance mask, gold materiality, or the surprise score to decide that an article “occurred.” An entity/category route fixed from contract metadata may be a practical control, but it is still a text-based route and must be described as such. A completely content-neutral feed control provides the cleanest reference.

Reliable coverage is an eligibility prerequisite for the primary comparison. An unknown feed interval is not coded `no article`. A separate operational analysis may study an explicitly defined missing-feed fallback, with the same fallback information supplied to every arm. Coverage certification and exposure features serve different purposes.

### What counts as signed surprise

Keep three quantities separate:

- **Evidence direction:** an exact supported claim favors YES, favors NO, or is ambiguous. Opinion and attributed forecasts keep their information roles; they do not become observed outcomes.
- **Text novelty:** the available claim differs from earlier available reporting, with duplicates and updates tracked. Text novelty alone does not measure unexpectedness.
- **Surprise:** the claim differs from a specified expectation recorded before the event. For a release with a numerical forecast, a candidate is a standardized actual-minus-expectation value. For a categorical event, surprise requires an explicit pre-event belief or likelihood model. If no defensible prior exists, call the feature signed new evidence and retain surprise as unknown.

The price of a canonical YES contract refers to its resolution probability. The market-only forecast `p_M` in the existing task refers to the probability of a future large repricing. Those are different probabilities. A YES-favoring information score must not be inserted mechanically into `logit(p_M)` as though it were an update to contract-resolution odds. A future repricing model can learn magnitude, direction, prior-price, and activity interactions using development data; the probability being forecast must be explicit.

### Primary and secondary contrasts

Proposed primary content contrast, on the full supported eligible grid:

```text
Delta_content = mean[LL(M+E+T) - LL(M+E+T+R+S)]
Delta_total   = mean[LL(M)     - LL(M+E+T+R+S)]
```

Positive values indicate lower candidate loss. Treat `Delta_content` as the primary scientific test and `Delta_total` as a prespecified overall-performance guardrail. Report exposure-subset loss, no-exposure loss, and event-balanced robustness as secondary results. Fix weighting and denominators before evaluation; long or very active episodes must not silently determine the scientific population. Population loss and event-balanced loss answer different questions.

Useful-effect threshold, allowable population degradation, confidence level, alpha allocation, and success logic remain pre-freeze decisions. V4's **0.001-nat** rule continues to apply only to V4; importing it into V7 without power and utility justification would be arbitrary. Choose one advanceable content candidate through a bounded development procedure, rather than selecting whichever semantic arm wins on confirmation.

## 5. Paper B proposal: information events and remaining repricing

**Working title:** *When Do Prediction Markets Incorporate Contract-Relevant News? Evidence on Remaining Repricing and Market State.*

This is a different sampling design from repeated five-minute grid forecasts. Select verifiable information episodes without inspecting their subsequent price movements. Begin with one domain whose source timing, exact contract predicate, active status, and event identity can be evidenced. Official numerical macro releases are a reasonable feasibility candidate; they still require prior expectations, suitable contracts, and usable price measurements. The domain is not selected or launched by this roadmap.

### Event and landmark clocks

Store separate times for source publication, official release if known, provider ingestion, local first observation, conservative availability, and later versions. Set `t0` to the declared system-availability clock for the prediction study. If an official release occurred earlier, retain that lag and distinguish remaining predictability after system access from total market response after public release.

A concrete draft default is a **five-minute landmark**: make the forecast at `t_decision = t0 + 5 minutes` and measure remaining 30-minute repricing after that time. The price reaction from `t0` through `t_decision` can then enter every arm's market controls. For a forecast made at `t0`, that later reaction is unavailable and cannot be a feature or define a “fast” versus “slow” subgroup.

Retain 30-minute absolute repricing probability as the proposed primary target for continuity. Directional remaining drift and 5/15/60-minute horizons are secondary diagnostics with prespecified multiplicity handling. Choosing directional drift as a different primary is possible, but requires a new target, scoring rule, threshold/density definition, and power design before evaluation. Do not choose the best horizon after seeing the results.

### Price measurement and liquidity

Measure trade age and trailing activity using information available by the landmark. Define activity proxies as activity proxies; a full liquidity claim additionally benefits from quoted bid/ask, spreads, depth, and reliable quote arrival clocks. Compare last-trade and quote-based responses where both exist, with a declared overlap population and alignment tolerance. Quote availability cannot be assumed from current trade data.

Specify stale or absent endpoint handling, suspended markets, intervening releases, terminal boundaries, and overlapping episodes in advance. Avoid eligibility filters requiring a future trade or visible future price jump, since they select the outcome being predicted. An unchanged carried-forward trade can mean no new execution rather than unchanged market beliefs.

Event-time curves describe observed response around the declared clock. Predictive patterns may be consistent with gradual assimilation; they do not establish causal news effects or underreaction relative to true value without an independent information-value benchmark and a suitable identification design.

## 6. Linking benchmark and measurement gates

Create a new development sampling specification before drawing or annotating cases. The existing strict audit remains failed and its cases are opened development. The relaxed sensitivity labels can help write a rubric; they cannot serve as a held-out benchmark or justify thresholds after label inspection.

The proposed benchmark records article/version hashes, exact evidence spans, contract/rule versions, subject and predicate, claim role, episode, period, direction, novelty/duplicate lineage, market-odds quotation, and unknowns. Source validity and semantic applicability remain separate axes. A retrospective relation can be semantically correct while being unavailable for prediction.

Sample accepted candidates, rejected candidates, hard negatives, and retrieval misses with known inclusion probabilities. Hard-negative enrichment is useful for stress testing but does not establish production precision or corpus recall unless weighting and the reference population are declared. Retrieve the full opportunity universe needed for a miss estimate; a sample selected only from top-ranked pairs cannot supply it.

Use independent outcome-blind reviews, retain both answers and uncertainty, record one adjudication, and group article versions, syndicated stories, contracts, and shared episodes in splits. Report class-specific agreement and errors, precision, missed-link evidence, abstention, coverage, and unique eligible event yield. A new frozen audit requires stable policy, independent sample, prewritten evaluator, and sample-size/stop logic. Repeated sampling until the linker passes is not permitted.

Paper C becomes viable only if this creates a sufficiently diverse independent benchmark with baselines, reliable held-out events, useful negative cases, and permitted release artifacts. It should not be promised on the current five-article material-evidence sample.

## 7. Dependence, power, and negative-result interpretation

Count independent information episodes and their family/calendar overlap before counting forecast rows as evidence. One release can affect several contracts; overlapping 30-minute labels and repeated stories create dependence. A nominal market-only cluster scheme need not account for common shocks or selection across methods.

Use development-only simulations to assess the eventual inference candidate under common calendar shocks, within-episode persistence, irregular arrivals, market-family dependence, concentrated activity, source missingness, and market-state regime changes. Check type-I error, interval coverage, useful-effect exclusion, and power with a predeclared simulation budget and acceptance criteria. No particular bootstrap, multiway cluster, or grouped-t method is selected here; prior coverage failures remain unresolved evidence.

For a prospectively fixed practically useful threshold `delta_star`, distinguish:

- **Confirmed useful gain:** the declared point-estimate and interval requirements plus population guardrail pass.
- **Harm:** the appropriate upper bound on improvement is below zero under the declared inference.
- **Useful-gain exclusion:** the upper bound is below `delta_star`; small benefit may still be possible.
- **Inconclusive:** the interval still includes useful gain, the sample is too weak, or required source/inference support fails.

The exact confidence levels and decision hierarchy must be frozen; this taxonomy is not a replacement for V4's existing success rule. More rows do not automatically resolve weak episode diversity or failed uncertainty coverage.

## 8. Related research checked

Nearby work makes the proposed positioning more specific:

- Angelini and De Angelis report incomplete immediate adjustment and subsequent drift in a real-time public-signal setting, with stronger underreaction in low-liquidity states. This motivates a hypothesis, not evidence that EventX's textual news behaves the same way. Paper B would need a contribution in contract-specific textual measurement, system availability, and independently evaluated remaining repricing. [*When Do Markets Fully Process Public Information?*](https://arxiv.org/abs/2606.07811)
- Gong and Dimitrov study AI-extracted text beyond price benchmarks for next-day downside-tail assessment. Their abstract describes a daily Polymarket text-measurement pipeline and rolling out-of-sample comparisons. This is related to Paper A but differs from EventX's 30-minute unsigned repricing task. A full comparison with the manuscript is still required. [*When Text Helps*](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7005158)
- Ibrahim and Zaki link Polymarket movements to later news citations, including extracted sentences quoting market odds. Their reported citation pattern supports tracking market-derived reporting as a separate information role. It does not prove that all odds-quoting articles lack external evidence or quantify feedback in EventX's feed. Keep mixed articles and identify their external versus market-derived evidence spans. [*Price Dislocations, News Citations, and Epistemic Leverage on Polymarket*](https://arxiv.org/abs/2609.06005)

These are working papers/preprints used for a targeted positioning check. This is not an exhaustive novelty review or independent replication of their findings.

## 9. Execution roadmap and deliverables

| Priority | Action | Concrete output / completion condition |
|---|---|---|
| P0, current cycle | Continue V4 operational monitoring without outcomes | Timestamped process/checkpoint/receipt/hash evidence; source gaps explicitly retained |
| P0, paper | Expand the historical manuscript in a new version | Claim ledger, artifact-backed tables, baseline/context discussion, limitations, literature comparison |
| P1, source readiness | Resolve the existing focused provider request | Exact historical delivery/version/status/coverage evidence or explicit unavailability; prepared request currently unsent |
| P1, measurement | Write benchmark rubric, sampling frame, and review protocol | Accepted/rejected/miss strata, evidence fields, independent episodes, fixed review budget and stop rule before new labels |
| P1, feasibility | Assess distinct episode yield and inference candidates | Coverage/type-I/power simulations and a defensible minimum detectable useful gain |
| P0, after close | Follow the frozen V4 sequence exactly once | Collection audit → consumption receipt → point-in-time preparation → sealed examples → evaluation; stop on failed gate |
| P2, next-cycle freeze | Complete the V7 M/E/T/R/S specification | Explicit source, cohort, neutral exposure, target, contrasts, weighting, models, transforms, inference, dates, stop logic, hashes |
| P2, Paper B | Freeze the event/landmark design if measurement feasibility passes | One primary outcome/horizon and a genuinely new evaluation sample; subsequent reaction diagnostics |

The source request is already concrete and ready for a recipient, but no destination has been supplied in this task. No external message was sent. If historical proof is unavailable, the [existing prospective capture proposal](eventx/release/v6/PROSPECTIVE_CAPTURE_PROTOCOL_DRAFT_20260927.md) is the starting point for a newly versioned development capture: immutable at-arrival article/contract bytes, bounded feed requests, active-status snapshots, quote/trade clocks where supported, and daily receipts. It is a proposal, not a running collector.

The suggested effort allocation—35% paper consolidation, 35% measurement validity, 20% event signals, 10% additional model work—is a planning preference. It does not estimate expected performance gain. New general boosting sweeps are lower priority than an independent strong-control test and reliable information episodes.

## 10. Decisions still required before a new freeze

Fix the pilot domain and observable source scope; choose the population and weighting; define neutral E/T; decide whether S is signed evidence or measured surprise; specify the pre-event prior; freeze the landmark and primary outcome; establish quote/endpoint handling; set candidate budget and transform-fitting rules; resolve family/episode/calendar dependence; define the useful-gain and harm criteria; and select a new untouched interval with an explicit exposure ledger. Fit learned representations only inside forward training windows.

For a subsequent V7 forecasting redesign, source selection, cohort choice, and tuning must not use V4's eventual performance to choose what will succeed. Use its operational/source audit findings for data engineering while preserving the evaluation boundary. All consumed holdouts remain consumed, and the original v1 test cannot be described as untouched.

This roadmap is a reviewable next-study proposal. It improves the definitions and work sequence; it adds no forecast result, source admission, independent labels, confirmation sample, or change to the frozen research artifacts.
