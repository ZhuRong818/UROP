# EventX: evidence review, missed signals and event coverage

**12 October 2026 — completed opened-development diagnostic**

Data package: `data/v7/event_coverage_pilot_20261012/`. Current automatic extractor remains **v0.3.3**. All original extraction, model, split and confirmation artifacts are preserved.

## Decision

The requested evidence review, missed-evidence diagnosis and event-to-market ledger are complete as **assistant development work**. The forecasting comparison gate fails: there are no usable signed-evidence landmarks, and none reach the original fitting or evaluation date blocks. No forecasting model was fit; new log loss, Brier and AP are unavailable.

The useful new finding is that **semantic coverage and market observability both fail**. Eleven plausible directional extraction misses were already retrieved. Recovering them manually still produces no eligible signed forecasting observations. One reported FOMC decision provides four observable downstream market-response proxies, of which three have positive historical volatility, but all reuse the same episode and have context-only evidence.

## 1. Evidence review

Inspected all 17 pairs in the existing packet, preserving its inputs and blank human response templates.

| Assistant judgment | Pairs |
|---|---:|
| Exact directional forecast, conditional on year/meeting assumptions | 10 |
| Material context without the required exact implication | 6 |
| Unresolved contract wording | 1 |

The six known bad links remain unsupported: “lower courts,” traders cutting risk, generic cut odds, easing cut bets, and past rate levels do not establish the requested policy action, size or annual count. This confirms the repair on those opened examples.

The unresolved pair is **KXFEDDECISION-26JUL-H0**, described as “Hike rates by 0bps.” The cached V7 metadata recovery also has **no rules or YES subtitle** for it. Treating it as a hold contract remains an assumption; it is excluded from the signed ledger pending clarification.

The accepted claims are attributed forecasts, not official decisions or measured surprises. Availability-year anchoring and exact meeting interpretation remain explicit assumptions. This is one assistant review with prior algorithm exposure; it does not satisfy independent human review or establish population accuracy.

Evidence: `selected_packet_assistant_review.jsonl` and `cached_rule_check.json`.

## 2. Fixed missed-evidence sample

Before reading market prices, fixed seed **20261012** selected 12 date buckets per macro route, then one article per bucket. The result is **36 articles across 29 dates**. Sampling probabilities and bucket sizes are retained. Reserved V6 audit article identities/content hashes are excluded without opening their labels.

| Supplied-text diagnosis | Articles |
|---|---:|
| Preview, general context or market reaction | 20 |
| Keyword collision | 11 |
| Foreign macro context | 2 |
| Jobs-report reaction without exact measurement fields | 2 |
| Forecast needing further binding | 1 |

Examples include **CPI Aero/CPI FIM**, ADP/payroll businesses, payroll taxes and a Fed banking stress test. These are domain-routing collisions. Two articles describe jobs-data reactions but omit the exact threshold/source/period needed for signed measurement evidence. The Goldman July “decent chance” forecast is potentially useful directional context, but it is not an unambiguous asserted meeting outcome.

These counts describe this sample. They are not production precision or recall estimates.

Evidence: `design_receipt.json`, `miss_sample.jsonl` and `miss_sample_assistant_review.jsonl`.

## 3. Targeted policy census and extraction misses

An outcome-blind headline rule found **188 policy-action candidates** across the opened corpus. Every supplied candidate headline/summary was inspected. This is a candidate census under that rule; it does not cover every possible policy article.

The census contains 15 reported policy-action articles, 15 official-comment/minutes articles, five prediction-market-odds reports, four unresolved/conflicting reports, 17 additional forecasts needing binding, seven attributed forecast extraction misses and 125 previews/context/market reactions.

The seven plausible misses support **11 directional article–contract hypotheses**:

- Four BofA articles describe annual hikes or the September quarter-point path. Nominal action wording and institution/agency attribution prevent extraction. They are repeated coverage of one candidate rate-path revision.
- Three Kashkari articles describe an expected hike “this year.” The Fed official is the forecaster, while the agency is the policy actor. The current grammar does not resolve this relationship. They reuse one candidate forecast episode.

**All 11 missed associations were already in legacy retrieval.** For these examples, candidate retrieval supplied the contract; the extraction/binding stage abstained. Checking all 36 Fed contracts independently of legacy retrieval recovered **zero additional automatically exact associations** in the sampled/census documents.

This identifies a concrete extraction repair opportunity. It does not establish that retrieval recall is generally adequate. Annual-count and negative-path forecasts also need past-versus-remaining-year interpretation; they were not automatically promoted into exact labels.

Evidence: `candidate_decisions.jsonl`, `policy_census_assistant_review.jsonl` and `extraction_miss_trace.jsonl`.

## 4. Event-to-market ledger

### Method

Use the conservative article `available_at`, one exact decision at **availability + 5 minutes**, and a **30-minute response horizon**. Keep one earliest supported arrival per candidate episode/contract; later articles cannot replace it because they have better trading coverage. Primary freshness is 30 minutes, with a separately reported 60-minute sensitivity.

Trace prior execution age, trailing 240-minute execution count and prepared size units, one-minute carried-forward historical log-odds volatility, cached terminal bounds and future execution timestamps. No future price values or outcome labels are read. Future execution availability is recorded as a denominator diagnostic and never used as a prediction-time feature gate.

Historical rule/status validity, trade-arrival availability and endpoint feed completeness remain unknown. The prepared count/size field is **not proved to be YES-price-times-size dollar notional**. These are development observability proxies; unknown windows are not converted to zero outcomes.

For the reported-decision pilot, the two primary reports explicitly identify the June meeting/date. Their earliest availability is **18 June 2026, 06:37:01.172352 UTC**. The announcement contracts are examined for closure losses; still-open downstream Fed contracts are screened as broad policy context. A June hold does not give an exact signed implication for a later July/September action.

### Results

| Stage | Signed forecasts | Reported decision context |
|---|---:|---:|
| Candidate episode hypotheses | 3 | 1 |
| Earliest episode–contract landmarks | 11 | 36 |
| Eligible under cached 30-minute freshness/activity proxy | **0** | **5** |
| Observed future execution and fresh endpoint proxy | **0** | **4** |
| Above with positive historical volatility | **0** | **3** |

The arrival-level screening ledger has **93 opportunities across 11 articles**; 72 are broad context opportunities, not exact semantic links. Collapsing repeated arrivals leaves **47 episode–contract landmarks across four candidate episodes**. They are not 47 independent events.

All 11 signed landmarks have fewer than three trailing executions and stale/missing prices. Five have no prior execution; nine also fail the prepared-size threshold. These losses overlap. Extending the freshness diagnostic to 60 minutes still yields **zero** eligible signed landmarks. No signed arrival becomes eligible even before episode deduplication.

Concrete examples:

- Yardeni's May 18 forecast precedes any observed execution in its five retained contracts.
- The earliest BofA annual-hike article has a last trade approximately **1,442 minutes** old. The retained September-path observations have last trades approximately **121–541 minutes** old.
- The Kashkari annual-hike observation has a last trade approximately **85 minutes** old, only two trailing executions and 32.346152 prepared size units.

The four observable decision-context proxies concern July contracts. One has zero historical volatility, so only three have a nonzero volatility scale for the established movement threshold. All four reuse one reported information episode; none carries exact downstream signed evidence.

An earlier undated “Fed Holds Rates Steady” headline arrives on **17 June, 22:37:01.887310 UTC**. Assuming it describes the same meeting yields six eligible contracts and three observable positive-volatility proxies. This sensitivity does not increase episode diversity, supplies no signed features and does not replace the primary dated-report analysis.

Evidence: `arrival_contract_ledger.jsonl`, `episode_contract_ledger.jsonl`, `undated_report_sensitivity_ledger.jsonl`, `report.json` and `supplement.json`.

## 5. Forecasting comparison gate

The intended comparison remains fixed strong **M + exposure + timing** versus the same model with signed evidence, on identical keys. A reviewed-evidence oracle would diagnose signal potential; automatic evidence would diagnose the deployable pipeline.

Both original date blocks have **zero signed landmarks**:

- Fitting: `[2026-06-30, 2026-07-11)` UTC.
- Evaluation: `[2026-07-11, 2026-07-22)` UTC.

Even the broader opened-period landmark ledger has zero eligible signed observations. Fitting another correction here would not measure the predictive value of signed evidence. The executable gate therefore records **no fit**, with null metrics. There is no new performance gain, significance claim or promotion.

## 6. What should happen next

1. Implement a separately versioned attribution/nominal-action adapter for the seven missed forecasts, retaining period/quantity checks and hard negatives. Measure episode and eligible-row yield alongside accepted-link count. This is a recall repair; these examples alone cannot recover forecasting coverage.
2. Prepare an event capture pilot with reports arriving promptly and overlapping active, observed downstream contracts. Retain official release, publication, provider availability, exact-version observation, execution and execution-arrival clocks separately. Multiple genuinely distinct episodes across development and evaluation are needed. Keep uncertain source intervals explicitly unknown.
3. Preserve the current 17-pair human review forms; add the new missed examples to a separate outcome-blind review packet if an independent measurement benchmark is pursued. Do not relabel assistant judgments as human gold.
4. Run the matched model comparison only when the ledger supports both fitting and evaluation. Keep the existing strong baseline fixed and measure log loss/Brier/AP on identical keys, with episode counts and the population guardrail. No replacement split, relaxed freshness rule or horizon was selected to rescue this pilot.

The existing Paper A can incorporate this diagnostic as failure-mechanism evidence. A delayed-repricing paper needs more distinct observable events; this one episode cannot support its central empirical claim.

## Integrity and checks

Preparation verified **53 input/artifact hashes**. Analysis verified **17 hashes**; supplementary publication checks verified **16 analysis artifacts**. Exact evidence substrings, complete review IDs, unique episode–contract keys, unchanged clocks/horizons, opened-date bounds and the zero-coverage comparison gate were checked. Separate manifests preserve every stage and the final delivery package.

No software tests were added or run. No protected/consumed holdout payloads, outcome labels or future price values were accessed. No new source fetch, model fit/promotion, human-review relabeling, external message or V4 change occurred.
