# EventX research progress report

**As of:** 7 October 2026, 13:03 Asia/Singapore (05:03 UTC)  
**Research question:** Does information available from external news improve prediction of a 30-minute absolute prediction-market repricing event beyond executed-market history?  
**Status:** Historical primary study complete; prospective V4 collection in progress; V5/V6 redesign remains development work.

## Summary

The completed v3.1 historical comparison did not support adding the frozen news-count features. On 1,460,454 matched out-of-fold development rows, B1 (market history plus news counts) reduced average precision by 0.001916 and worsened Brier score by 0.000284 relative to B0 (market history). All five prespecified promotion gates failed, so B0 alone was frozen and evaluated once on the historical holdout. Its 211,718 holdout rows from 300 eligible markets produced average precision 0.171628, Brier score 0.107107 and ROC AUC 0.628037. There is **no holdout estimate of incremental news value**. The holdout has a disclosed receipt-order deviation: label prevalence was summarized before the consumption receipt, while predictions and performance were still unexamined. [Development selection](../data/v3_1_historical/primary/development/selection_result.json) · [Holdout result](../data/v3_1_historical/primary/holdout/evaluation_result.json) · [Deviation](../eventx/release/v3_1_historical_primary/HOLDOUT_PROTOCOL_DEVIATION.md)

The separate V4 prospective study remains sealed and unchanged. Its sole confirmatory interval is **6 September–30 October 2026 UTC**, across 470 Polymarket markets. It will compare frozen B3 (news volume, relevance, novelty and publisher diversity/diffusion) with frozen B0 on identical rows. The 7 October label-blind health check found the collector and sleep guard running, with 38 news days and 31 trade days checkpointed through 6 October, 38 news and 310 trade receipt sets present, no closed-day backlog, and all 15 frozen hashes matching. It did not certify source completeness or payload integrity. No consumption receipt, examples or evaluation artifacts exist. [Protocol](../eventx/release/v4/protocol.json) · [Current health receipt](../data/v4/health_checks/20261007T050341Z/report.json)

## Results and branch decisions

| Branch | Latest evidence | Decision |
| --- | --- | --- |
| V3.1 historical primary | B1−B0 AP **−0.001916**; Brier improvement **−0.000284**; paired 95% block interval **[−0.000341, −0.000230]** on 1,460,454 development rows. B1 failed H1–H5. | Completed negative model-selection result; B0 selected. |
| V3.1 B0 historical holdout | AP **0.171628**, Brier **0.107107**, ROC AUC **0.628037** on 211,718 rows; one-shot evaluation with disclosed receipt-order deviation. | Absolute market-only benchmark. B1 was never evaluated there. |
| V4 historical discovery | On 745,443 outcome-open Polymarket development rows, B3−B0 log-loss improvement **−0.006459 nats/row**, paired interval **[−0.007411, −0.005545]**. B1 and B2 also worsened log loss versus B0. | Exploratory negative evidence; frozen future evaluation remains pending. |
| V4 prospective confirmation | 470 markets; collection through 6 October verified from metadata, receipts and frozen hashes. Holdout ends 30 October. | No confirmatory result yet; continue sealed collection. |
| V5 redesign | Opened-history market-only nonlinear baseline beat the tested news additions; inference/dependence screens and source/family gates remain unresolved. | No V5 news candidate frozen or confirmed. |
| V6 contract-aware development | 134 contracts × 66 opened days = 8,844 contract-days; 3,803 had observed trades, but **0** have certified predictive support. The 102-pair relaxed review is development sensitivity only. | No admitted links, forecast fit or independent predictive evaluation. |

V4 historical discovery values come from its [frozen result](../data/v4/discovery/models/result.json). V6 support counts come from its [support ledger report](../eventx/release/v6/SUPPORT_AND_PIPELINE_READINESS_20260926.md); review status comes from the [adjudication report](../eventx/release/v6/RELAXED_ADJUDICATION_AND_NEXT_STEP_20260928.md). The older 14-market V2.3 study remains a separate pilot; the current handoff records no final replication result. KOL is deferred after its fixed association audits failed.

## Data and method blockers

1. **V4 source assurance.** The collector health check verifies process, checkpoints, receipt-file presence and frozen hashes. It does not establish complete upstream news windows or validate sealed payload hashes. Missing source coverage cannot be interpreted as zero news. The prior collector stop cause remains unconfirmed.
2. **V6 point-in-time source evidence.** Five of nine scoped news runs failed, historical page/symbol/cursor completion is unreceipted, and market status and article-version histories are unavailable to the current read role. The 268 unverified zero-export contract-days are two filtered-export days repeated across 134 contracts. The exact nine-article/15-contract [Lumid bug-triage request](LUMID_EVENTX_V6_SINGLE_FILE_REQUEST_20261002.md) is prepared but unsent. Certified V6 support remains 0/8,844 contract-days.
3. **V6 link and inference design.** The original strict relevance audit failed; the later 102-pair relaxed review changes the rubric and reuses a small set of articles. Its 26 material-predicate labels come from only five articles and cannot establish independent exposure or linker accuracy. Historical family boundaries, semantic acceptance rules, event yield, power and defensible dependence inference still require resolution.
4. **Claim scope.** Lumid's pre-17-May publisher-dated articles were ingested later and cannot supply point-in-time pre-May confirmation. The studies do not support causal, trading-profit, social-virality, Kalshi-wide V4 or universal “news has no value” claims.

## Next work

1. Monitor V4 process, closed-day checkpoints, receipts and frozen hashes without reading protected prices, labels, prevalence, predictions or metrics before the 30 October close.
2. After close, execute the frozen V4 sequence once: collection audit → consumption receipt → point-in-time preparation → sealed examples → evaluation. Stop if a gate fails.
3. Obtain the scoped Lumid feed, article-version and market-status receipts for V6. Keep uncertain intervals unknown; only then finalize a prospective semantic class policy, independent link audit and distinct event/support count before considering a predictive freeze.
4. Complete claim, artifact, reproducibility, rights and venue-format review for the [4 October historical paper draft](EVENTX_HISTORICAL_PAPER_DRAFT_20261004.md). This paper can report the completed source-bounded V3.1 result without waiting for V4, while keeping V4 prospective claims out of it.

This report summarizes frozen results and a label-blind collector check. It does not change a protocol, reopen a consumed holdout, admit V6 data or evaluate the protected V4 interval.
