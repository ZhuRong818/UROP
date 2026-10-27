# EventX: progress toward usable forecasting

Updated 2026-10-24T07:47:28.199602+00:00. **No usable forecast has been issued yet.** This work advances source feasibility and fixes the prospective timing specification. The selected market model remains frozen.

## Completed work

### 1. Both source rehearsals completed

|Measure|Original24h run|Revised24h run|
|---|---:|---:|
|Journal records|588,233|380,142|
|Verified payloads|483,894|317,984|
|HTTP429 responses|52|0|
|Comparable macro activity windows|3159|2016|
|Activity passes|0|0|
|Maximum market trade-receipt gap|121.13min|443.80min|

The runs cover different periods. These are descriptive source results, not a controlled performance improvement. Original activity diagnostics use cash/inclusive boundaries; revised diagnostics use token quantity/inclusive boundaries. Neither is exact model eligibility.

The revised longest trade-receipt gap runs from23October10:01:38UTC to17:25:26UTC.62host power events occur in the bounded overlap check, including repeated sleep/dark-wake states; a full wake at17:25UTC precedes renewed trade receipts. This supports host sleep as a contributor, without attributing every source omission to sleep. The longest gap across *all* journal events is6895.002863seconds, distinct from the per-market trade gap.

All1441revised HTTP404responses came from venue book requests, not the resolution endpoint. We captured3182successful resolution responses. Repeated API success does not certify continuous trading status.

### 2. Prospective endpoint policy frozen

`eventx/release/v7/forecast_path_20261023/policy.json` was frozen before expansion data were fetched. For this new feasibility branch:

- Inputs must be durably available by the five-minute decision grid; any later shadow forecast must be issued within30seconds, otherwise mark a missed emission.
- Decision and target prices must be no more than5minutes old.
- The target uses the latest unambiguous trade at or before t+30minutes, durably captured by t+32minutes. Never use a post-target nearest trade.
- A receipt/status gap over120seconds blocks affected observations. Backfill cannot repair timely availability. A fresh valid240-minute warmup is required after interruption.
- Missing endpoints remain explicit, and every issued forecast stays in the coverage denominator.
- First establish one complete prospective feasibility observation, then separately activate predictions on later grids. Do not relabel retrospective scores as live forecasts.

The120-second operational limits and30-second issuance budget are prespecified design choices, not validated optimal thresholds. This policy does not modify V4 or earlier studies. The inherited source auditor still prints its generic 'forward policy pending' message; the new branch's policy exists, but source readiness and activation remain pending.

### 3. Metadata expansion completed; two candidates enrolled for source capture

The price-blind search returned204records without hitting its1000-row cap and excluded all470protected V4IDs. The first network attempt failed in the sandbox; the next returned HTTP400. A separately versioned query using `NOT (question ~* ...)` succeeded. The original400body was not retained, so the exact server-side failure cause is unknown.

The ledger retains14existing candidates,89own-release-terminal records,99other excluded records, and two new candidates:

|New contract|Why investigate it|Remaining rule issue|
|---|---|---|
|Negative GDP growth in2026?|A longer-lived US GDP predicate|Full-year/annualized wording requires exact BEA table binding|
|US recession by end of2026?|GDP component evidence and a longer-lived horizon|Either two negative quarters or NBER announcement can terminate it early|

These are source candidates, not predictive admissions. No liquidity ranking or price movements were used. Short-lived contracts were not promoted just because their metadata end date follows a release. Other-release contextual links remain a possible separately specified branch.

### 4. Expanded feature sensitivity to all22columns

From114retained source representations across22markets,11vectors across two markets could be reconstructed. The other histories remain unavailable. Seven paired comparisons were possible; three changed at least one column by more than1e-6. For the BTC74kcontrol, provider versus direct taker-only changed10columns, including volatility, counts, quantities, recency and derived ratios.

This establishes that source substitution can affect much more than counts. It does not establish production feature equivalence, complete source history, or forecasting improvement. No model was loaded or scored; no labels were computed.

## Running now

The separate two-market collector started24October07:27:27UTC (15:27SGT), PID31131; scheduled stop **24October13:27:27UTC (21:27SGT)**. It captures metadata/resolution every cycle, records long cycle gaps, and automatically produces a final source audit. It has no scoring or event-activation capability. Original collectors remain unchanged.

The first57.92seconds yielded14HTTP200responses,18verified payloads, and two-sided uncrossed books for both markets. Both mappings/rules matched venue metadata and both accepted orders at the sampled instant. The recession contract had12venue and12provider records in the bounded six-hour window, but0canonical YES records; negative GDP had0trade records. Both fail activity eligibility. Counts do not establish unique executions or source completeness. Initial retained trade windows are retrospective, not prospectively accumulated history.

**Operational requirement:** keep the Mac powered, connected, awake and lid-open through the six-hour capture. The recorded sleep states make this a concrete dependency. No settings override or SSH deployment was performed.

## Next gates

1. Read the new completed source audit after21:27SGT; preserve any failed/zero-yield run.
2. Determine whether enough fresh canonical YES observations exist, whether current metadata/rules remain consistent, and whether provider/venue counting can reproduce all22inputs.
3. Resolve the two explicit predicate/terminal caveats using source evidence; any human adjudication should receive this concrete package.
4. Activate a release-time feasibility window only after source readiness. The first existing reservation is29October12:30UTC, with six-hour warmup planned from06:30UTC. No event service is activated yet.
5. After one complete observation passes, freeze later shadow-forecast activation and comparator artifacts. A prospective baseline comparison remains outstanding.

If the broader sample still cannot support the trade-based target, preserve that result and specify a separate quote-based or alternate-horizon study. Do not silently transform NO trades into YES model inputs or substitute quote midpoints for historical trades.

## Evidence

- Completion reviews: `data/v7/source_workflow_20261022/{original,revised}_final_review.json`
- Gap diagnosis: `data/v7/completed_rehearsal_diagnosis_20261024/`
- Feature analysis: `data/v7/full_feature_compatibility_20261024/`
- New source package: `eventx/release/v7/expansion_source_pilot_20261024/`
- Runtime: `data/v7/expansion_source_pilot_20261024/live/`
- This report's manifest and operational snapshots: `data/v7/forecast_progress_20261024/`

Protected holdouts remain untouched. No new performance statistics, tests, model fitting, trading, or provider messages were produced.
