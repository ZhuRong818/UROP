# EventX local research continuation

23 October 2026, Singapore. Evidence captured at 2026-10-22T16:04:14.991834+00:00.

## Local workflow is active

Following your instruction to work locally, the separately frozen background service `com.eventx.source-workflow.20261022` was registered and its process verified (PID74338). Its current phase is **waiting_for_original_rehearsal**. SSH is no longer a dependency. The previous failed SSH record and remote package remain historical artifacts.

The workflow will:

1. Wait for the original rehearsal to finish on **23October13:58:25Singapore** and verify its completed audit.
2. Run the separately frozen revised collector for24hours using the replacement trade API.
3. Write and review the final source audit, then stop before event activation or model scoring. If it starts promptly, the second run will finish around **24October14:00Singapore**. This is conditional on local execution, not a guarantee.

The three original collectors remain present (PIDs600,23793,39643). The41workflow dependency hashes and original production locks were verified. The Mac must remain powered, awake and connected; the prior lid-closed sleep gap remains part of the source record.

## New findings

|Diagnostic|Result|Meaning|
|---|---:|---|
|First-cycle provider rows|52|Bounded source sample, not52independent events|
|Exact decimal economic matches|42|Previous result reproduced|
|Additional matches explained by price precision|10|All from one liquid control; largest price difference2.69823×10⁻¹¹|
|Rounded economic matches with transaction prefix|52/52|Every provider row is compatible with retained direct data under this diagnostic|
|Ambiguous transaction-prefix matches|4|Unique execution identity remains unresolved|
|Extra direct rows after multiset matching|334|333in controls,1in prospective macro candidates|
|Different YES prices within the same second|9seconds|All in controls; ordering can affect last-trade features|

The ten-decimal rounding rule is an exploratory explanation, **not an adopted change to model inputs**. Across all31comparable market-cycle windows,54provider row occurrences comprise44exact matches and10precision-explained matches. Repeated occurrences are dependent.

### Maker/taker selection cannot by itself reconcile the provider

We compared the same retained time windows against the later paired maker-inclusive/taker-only probe. All22markets had a shared range. The earlier and later maker-inclusive snapshots were identical under transaction plus rounded economic keys in these windows.

|Source group|Provider rows|Direct maker-inclusive rows|Direct taker-only rows|Taker-only rows unmatched by provider|
|---|---:|---:|---:|---:|
|14prospective macro candidates|3|4|2|0|
|3legacy macro diagnostic markets|4|4|2|0|
|5liquid controls|45|378|88|63|

Among the52provider rows,29match retained taker keys and23match keys found only in the maker-inclusive response. Thus the provider sample cannot be reconstructed simply by selecting all taker rows. This suggests both differing participant accounting and incomplete/different provider coverage. Separately captured API snapshots and unknown filters prevent a claim about complete exchange history.

The distinction affects the candidate cohort too: one annual GDP candidate has2YES maker-inclusive rows/59.96tokens versus1taker-only row/29.98tokens in the paired probe. Selecting a mode can change activity counts and size features. No canonical mode was selected from this diagnostic.

## Research status and next review

**Zero predictive admissions; no new forecast-performance claim.** The market model remains fixed, protected evaluations remain untouched, and no labels or predictions were generated. Source accounting is now more clearly diagnosed: price formatting explains the earlier10unmatched records, while participant semantics, coverage and same-second ordering still require evidence.

The local workflow can complete its scheduled collection without another research decision. Before canonical trade mapping or event-study activation, review [the concrete source-accounting package](data/v7/local_continuation_20261023/REVIEW_PACKAGE.md). Provider clarification remains prepared and unsent. We have not described automated checks as independent human review.

## Reproducible artifacts

- [Execution accounting](data/v7/local_execution_accounting_20261022/report.json), frozen code/input hashes and row-level receipts.
- [Participant coverage](data/v7/participant_coverage_20261023/report.json), shared windows and row classifications.
- [Continuation snapshot](data/v7/local_continuation_20261023/report.json), timestamped process checkpoints and model/source locks.
- Live workflow status: `data/v7/source_workflow_20261022/status.json`; phase transitions also append to the monthly progress log.

No model retraining, protected evaluation, test-suite execution or external message was performed.
