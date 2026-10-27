# V6 support ledger and fixed L0/L1/L2 development comparison

Date: 26 September 2026. This work uses opened historical development inputs only. It does not open reserved reviews, protected V4 prices or outcomes, or consumed holdouts. It creates no predictive labels, links, training examples, or model promotion.

## Contract-by-day support ledger

The fixed frame is the 134 enriched review cards from the earlier corrected queue and all 66 UTC days in `[2026-05-17, 2026-07-22)`: 8,844 contract-days. The runner was separately receipted before computation. It verifies the frozen development trade and legacy-association arrays, V5 daily news inventory, article sample, and card artifacts. Only market index and timestamp are read from the trade array; prices and outcomes are ignored.

| Observed quantity | Count |
| --- | ---: |
| Contract-days with at least one recorded trade | 3,803 / 8,844 |
| Recorded trades in these 134 contracts | 1,441,723 |
| Contract-days with at least one legacy news association | 2,505 / 8,844 |
| Legacy associations, not validated V6 links | 19,714 |
| Contract-days with a screened article pair | 169 / 8,844 |
| Screened pairs on the 70-article retrospective subset | 185 |
| Contract-days whose metadata snapshot postdates the day | 4,023 / 8,844 |
| Contract-days whose cached rules are missing | 396 / 8,844 |
| Days with zero exported news rows, not proven source-empty | 2 / 66 |
| Certified V6 predictive-support days | **0** |

The remaining 4,821 contract-days have a metadata snapshot observed by day end, but historical text validity and trading status remain uncertified. All 66 news days lack complete feed reconciliation. The 185 screened pairs are a retrieval-selected subset, not full overlapping news windows or reviewed relevance. The ledger records observed, retrospective-only, missing, and uncertain states separately; zero exported rows are never interpreted as zero news. The 1,441,723 trade count independently matches the sum of the frozen market-index counts for the 134 contracts.

## Fixed development comparison

The preregistered frame was 70 opened articles and the same 134 retrospective cards. For each article, the candidate union contains all 185 legacy screened pairs, up to five positive full-rule lexical candidates, and five dense candidates from the pinned local encoder. L0 ranks by full-rule TF-IDF. L1 uses question/subtitle TF-IDF only for the unchanged field-aware typed hypotheses. L2 reranks the same typed union with the pinned local cross-encoder. Dense expansion is measured separately against the legacy-plus-lexical base union. All 185 old lexical scores were reproduced before model inference; candidate and model input/output hashes verified.

| Development diagnostic | Result |
| --- | ---: |
| Base-union pairs | 468 |
| Dense-only additions | 201 |
| Common-union pairs | 669 |
| Typed hypotheses on common union | 52 (49 asset context, 3 event context) |
| Typed hypotheses added by dense expansion | 11 |
| Articles with typed hypotheses, before / after dense expansion | 8 / 8 |
| L2 top-set changes caused by dense expansion | 0 |
| L2 versus L1 top-set changes on common union | 5 articles |
| Predictive admissions | **0** |

The 52 hypotheses involve only eight articles and 13 contracts in seven **provisional** split groups. Seven articles are Bitcoin-related; the eighth is a World Cup story whose Mexico/Iran team-role ambiguity was already identified as a false-positive risk. The seven provisional groups therefore do not establish seven independent information events. At the article day, 28/52 typed pairs have an observed trade, but this is neither verified relevance nor point-in-time market eligibility. The eight articles are previously opened development examples. There are no human reference labels for the revised context endpoint, so candidate counts and top-set changes cannot be called precision, recall, or improvement.

Dense retrieval added candidates but no new article-level typed coverage. The binding and evidence gates, plus historical source support, remain the bottleneck in this fixed sample. L0 and L1 have different semantics by design; their rank changes are descriptive. The encoder and reranker are retrospective development components, with historical training-cutoff eligibility uncertified.

## Data and paper decision

The current cache is large in raw rows but **not ready for a V6 incremental-news forecasting paper**. There are zero certified V6 exposed contract-days and no accepted link frame from which to calculate a meaningful event-cluster power estimate. A methods or feasibility paper can report these limitations and the completed negative/development experiments without a positive forecasting claim.

Do not bulk-fetch more trades or articles, retry the same ten missing metadata fields, or select only these eight hypothesis-bearing articles as a new study cohort. The earlier alternate-field probes still left six rules and four end fields missing. More copies of current descriptive snapshots cannot establish historical validity. A focused next data gate is:

1. Obtain provider evidence for exact metadata/news text versions, historical trading status, and feed/run completeness, using the prepared `eventx/release/v5/LUMID_CERTIFICATION_REQUEST_20260910.md` as the source question. No provider message was sent by this work.
2. Fix and compare the relevance/role policy on opened development examples, preserving known Bitcoin and Mexico failure cases, then freeze an audit design with accepted and rejected/nonretrieved samples. The old 40-case strict audit remains closed and failed.
3. Once the source and link methods can admit a prespecified frame, choose development event windows across topic/activity and low/no-news strata; recover complete overlapping news windows with a seven-day history warm-up using bounded date partitions and receipts. Count distinct stories, events, exposed contract-days, and their concentration before power calculations or additional trades.

The immediate decision is **targeted source certification and link validation, not volume expansion**. No live fetch was attempted because the fixed comparison produced no newly covered article and the previous exact-field metadata probes did not resolve the historical-version gap. This is a stop gate for the current version, not evidence that relevant news is absent.

Artifacts: `data/v6/support_ledger_20260926/` and `data/v6/fixed_pipeline_comparison_20260926/`.
Runners: `eventx.tasks.build_v6_support_ledger_20260926` and `eventx.tasks.compare_v6_fixed_pipelines_20260926`.
