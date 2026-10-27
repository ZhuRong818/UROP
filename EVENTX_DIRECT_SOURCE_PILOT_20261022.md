# EventX: direct-source pilot started

**22 October 2026. The 24-hour source rehearsal is running; predictive evaluation has not begun.**

## Completed work

- Checked the two original collector processes and preserved their services and frozen code.
- Retrieved177 macro metadata records andfive new control candidates, excluding all470 protected V4 IDs before queries.
- Selected14 longer-lived US candidates from exact rules: six annual GDP, five annual any-month inflation thresholds, three annual any-month unemployment thresholds.163 metadata records have explicit exclusion reasons.
- Froze22 source-sample markets: those14 candidates, three previous macro diagnostics andfive activity-control candidates. Controls are not research observations.
- Froze a separate collector and completed its three-minute operational check. Seven integrity tests passed before the freeze.
- Started service `com.eventx.direct-source-pilot.20261022`, PID39643, at05:58:25UTC. Both original PIDs600/23793 remained present underlaunchd at the05:59 check.
- Reserved six future feasibility episodes, retained84 candidate-episode link plans, and prepared an observation dossier template. These are not completed event observations or a confirmatory sample.

## Initial measured result

The completed smoke run lasted181.350440 seconds including shutdown/audit overhead. Its declared observation duration was180seconds. It returned258 HTTP200 andsix404 REST responses. The404s were both book sides of one control, repeated across three cycles; not six failed markets. Venue WS delivered42 book events and974 price-change events; no trade events. Concurrent Lumid SSE deliveredone acknowledgement andfive heartbeats, zero market-data events. Its single recorded TimeoutError was at the bounded deadline; this is not evidence of a provider outage.

For the14 new macro candidates, the first common six-hour window showed:

|Check|Result|
|---|---:|
|Current venue YES mapping and rule text agree with selected metadata|14/14|
|Current accepting-orders flags true and closed flags false|14/14|
|Venue YES books with two sides|13/14|
|Markets with any venue execution print rows|2/14|
|Venue / Lumid print rows across these markets|4 / 3|
|Nonempty queried Lumid quote responses|2/14|
|Observed trade-activity screen passes|0/14|
|Complete predictive admissions|0|

This verifies current mappings and accessible books for the new sample, while revealing sparse executed trading. A two-sided book is not a fresh trade. Current metadata flags do not establish future survival or uninterrupted historical tradability. Two nonempty provider quote responses do not establish complete or fresh archive coverage.

Control comparisons continue to show source differences: Bitcoin90k venue150 versus Lumid3 print rows; Bitcoin74k33 versus1; Bitcoin92k154 versus154; Bitcoin80k211 versus13. The pre-ranked third control (Bitcoin74k) passed the source-control screen of fresh two-sided book plusfour YES prints in60minutes, but its latest YES print was8.466667minutes old and did not pass the forecasting freshness rule. Print counts are not unique economic transactions or a certified source-completeness percentage.

## Running collection and next checkpoint

The fixed live run ends **23 October2026 at05:58:25UTC /13:58:25Singapore**, subject to host availability. It attempts an automatic final audit into `data/v7/direct_source_pilot_20261022/audits/`. Current liveness does not certify24-hour continuity. The initial live snapshot at05:59:16UTC contained132 completed REST requests (130HTTP200/two404),199 verified payloads andzero predictive admissions; the24-hour run was only50.337973seconds old.

After the completed rehearsal, inspect per-market gaps, source discrepancies, pagination, terminal metadata and sustained activity. Freeze any forward-latency rule and a new event-period capture version only after that review. The rehearsal expires before the first reserved release and must not be mistaken for scheduled market capture through December.

## Reserved event study

Reserved dates:29OctoberGDP/PCE;6Novemberemployment;10NovemberCPI/realearnings;13NovemberPPI;25NovemberGDP/corporateprofits/PCE;4Decemberemployment. Administrative end5December00UTC. Simultaneous releases are grouped; distinct dates are not automatically independent. Schedules were checked against official [BEA](https://www.bea.gov/news/schedule), [BLS November](https://www.bls.gov/schedule/2026/11_sched.htm) and [BLS December](https://www.bls.gov/schedule/2026/12_sched.htm) calendars on22October.

The earliest reserved release is still in the future. The first complete dossier requires timely original evidence, extractor readiness, valid240-minute history, fresh prices, a valid30-minute endpoint and actual unresolved/tradable status. Annual threshold markets can resolve early. No future observation, predictive improvement or independent event count is claimed here.

## Evidence and limitations

- [Runbook and next actions](EVENTX_DIRECT_PILOT_RUNBOOK_20261022.md).
- [Frozen sample and implementation](eventx/release/v7/direct_source_pilot_20261022/implementation_manifest.json).
- [Completed smoke audit](data/v7/direct_source_pilot_20261022/audits/20261022T055710Z_33e647/report.json) and [paired market results](data/v7/direct_source_pilot_20261022/audits/20261022T055710Z_33e647/market_comparison.jsonl).
- [Initial live audit](data/v7/direct_source_pilot_20261022/audits/20261022T055916Z_322689/report.json).
- [Episode reservation](eventx/release/v7/direct_source_pilot_20261022/episode_reservation.json) and [dossier template](eventx/release/v7/direct_source_pilot_20261022/observation_dossier_template.json).

Delivery checked1344 artifact/payload references and20 original production locks. Model bytes match the original fixed hash. No model fit, calibration, forecast score, target label, protected V4 payload read or holdout consumption occurred. No external message was sent.

The earlier sandbox metadata fetch failed with ConnectErrors and is retained. Its successful retry's health snapshot used an initial timestamp across sequential reads, producing one negative0.189232-second checkpoint age; this is documented as a snapshot timing artifact, not erased or interpreted as future data. Per-checkpoint age timing was corrected before the new implementation freeze. Full history remains in `docs/progress/2026-10.md`.
