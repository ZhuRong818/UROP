# V6 source-clock and document-role diagnostic

Date: 26 September 2026. Scope: the same 70 opened development articles, 134 retrospective contract cards, and 669 candidate pairs as the receipted fixed L0/L1/L2 comparison. This is a descriptive diagnostic. It did not open reserved reviews, protected prices or outcomes, or consumed holdouts; fit a predictor; fetch live data; or admit an article–contract link.

## Method and integrity

`eventx.tasks.diagnose_v6_source_roles_20260926` verified the upstream manifests, wrote `spec.json` and an input receipt **before** computing outputs, then applied the unchanged `eventx.v6.document_roles` v0.2 heuristic to every fixed candidate pair. It compared those statuses with stored field-aware v0.1 statuses. For the union of typed pairs, it joined article availability clocks, source-run status, cached metadata and rule ingestion, recorded terminal fields, first/last observed development trades, and contract-day trade counts. It did not reinterpret old article labels or rerank L1/L2 under the new heuristic. The six diagnostic output hashes and 18 input hashes verify; runner SHA-256 is `881a9cf50f09f6d6ac633229eb5699a1682aac1348b27bd881373ed7b6bebba6`. Canonical data and receipt: `data/v6/source_role_diagnostic_20260926/`.

The comparison is **not** an independent semantic test. The two heuristics and candidate set are development artifacts; none of the 669 pairs has revised-context human gold here. A typed hypothesis means shared context at best, not evidence that the article changes, resolves, or predicts the contract.

## What the role rule changed

| Fixed-pool count | Field-aware v0.1 | Document-role v0.2 |
| --- | ---: | ---: |
| Typed hypotheses | 52 (49 asset, 3 event) | 38 (35 asset, 3 event) |
| Hypothesis-bearing articles | 8 | 7 |
| Contracts | 13 | 12 |
| Provisional split groups | 7 | 7 |
| Abstentions among 669 pairs | 617 | 631 |
| Predictive admissions | 0 | 0 |

There were **18 status changes**: 16 typed hypotheses removed and two added. The union covers nine articles, 15 contracts and eight provisional groups; these counts are not independent events.

| Article | Development text issue | Old → new typed pairs | Interpretation |
| --- | --- | ---: | --- |
| `102500031` | “Bitcoin Bull Thesis Goes Big: 39 Trillion Reasons To Buy…”; no summary | 7 → 0 | Local purchase-object rule cannot bind “Buy” to Bitcoin. This may be a recall loss; no gold decision. |
| `152232532` | Mexico permits the **Iran team** to use Tijuana during World Cup matches | 3 → 1 | Mexico team-win hypotheses removed; Iran team context remains. Host-country mention must not inherit team role. |
| `201756152` | “Buying Time” and Citi **Buy** rating concern Strategy stock | 7 → 0 | Removes seven Bitcoin threshold contexts from figurative/stock-buy cues. |
| `211869183` | “Google Search Hits Record During World Cup Drama”; summary attributes a late win to Argentina | 0 → 2 | Recovers Argentina win and semifinal contexts, but the match, stage and year are not established by these spans. Human review required. |

The other five hypothesis-bearing Bitcoin articles retain their statuses: `166357183` (8), `168034724` (6), `189518836` (8), `193693829` (7), `197137081` (6). A headline saying Bitcoin or IBIT is relevant to a broad asset topic; it does not distinguish $70k, $85k, $100k, $150k or $1m thresholds or settlement dates.

## Clock and source diagnosis

For the **52 old typed pairs**, 36 have a cached contract snapshot and cached rule ingestion at or before the article availability clock; **16 pair an article with a later snapshot/rule**. The same counts under the document-role rule are 26/38 and 12/38. In particular, July Bitcoin threshold metadata was ingested on July 1 yet paired with some May/June articles; the Kalshi Mexico third-place snapshot was ingested July 6 for a May 26 article. A later snapshot cannot prove the earlier contract text, even if the contract existed. Conversely, an earlier ingestion timestamp does not prove that the later exported text is the historical version.

On recorded terminal fields, 50/52 old pairs and 37/38 new pairs place the article before the recorded terminal. The two old exceptions are the **June 28** IBIT article paired with the Bitcoin **May $85k** contract (nominal end June 1), and the **July 2** Strategy-stock article paired with Bitcoin **$150k by June 30** (nominal end July 1). The role rule removes the latter but retains the former. Polymarket end dates are nominal, not certified trading-close histories. Kalshi's observed `close_time` is also a retrospective field here; no historical status sequence was supplied.

Only 28/52 old typed pairs and 19/38 new typed pairs have a recorded trade on their article UTC day. These are pair counts, repeatedly reusing contracts and articles; they are neither certified full trade coverage nor independently sampled exposures. Sixteen old typed pairs predate the **first observed development trade**, and four follow the **last observed development trade** for the paired contract. Neither absence of an observed trade nor a nominal end date proves the precise tradability state. The ledger has **zero certified V6 support/admission days** across its 8,844 contract-days.

The eight old hypothesis-bearing articles map to eight source runs: five marked `failed`, three `ok`. The newly surfaced Argentina article is from a ninth run marked `ok`. Failed run status does not invalidate an already retained row, but run commitment, retry coverage and feed completeness remain unresolved. All eight old articles have `historical_content_available_at: null`; the ninth does too. The user-relayed Lumid administrator assurance in `eventx/release/v5/NEWS_CONTENT_ASSURANCE_20260914.md` provisionally supports headline/summary availability at ingestion or an updated revision timestamp. Its production field mapping and per-article history still need to be established. Article clocks are not publication-time substitutes.

## L1/L2 disagreements under the original comparator

L2 changes the L1 top set for five Bitcoin articles: `166357183`, `189518836`, `193693829`, `197137081`, `201756152`. The first switches July $70k to May $85k; three switch “$1m before GTA VI” to December $100k or June $150k; the last switches “$1m before GTA VI” to December $100k even though document-role v0.2 abstains on every pair for that article. These are rankings among weak shared-context hypotheses. No contract-specific threshold or deadline is stated in the cited article spans, and no revised-context gold establishes that L2 is better. Dense retrieval added 201 pairs and 11 typed hypotheses but no new hypothesis-bearing article or L2 top-set change in the fixed comparison.

## Decision and bounded next experiment

**Data sufficiency:** the raw corpus is large, but V6 has zero certified supported exposures and no validated revised-context link frame. This diagnostic strengthens the case for a source-and-link gate before additional volume or a forecasting power calculation. It is suitable evidence for a methods/feasibility discussion and negative findings, not a positive incremental-news forecasting claim.

1. **Source proof, scoped to real blockers.** Use the prepared, unsent `eventx/release/v5/LUMID_CERTIFICATION_REQUEST_20260910.md` and this artifact's exact nine article IDs/source-run IDs/content hashes plus 15 contract IDs. Seek field-specific version or immutability evidence for headline/summary and question/subtitle/rules/token mapping; first-seen/revision clocks; historical open/suspend/close status; committed rows, retry lineage and declared feed completeness. Include the five failed article runs and four successful runs. An admin statement without a field mapping or current-row timestamp alone does not certify a historical version. This packet remains local; no provider message was sent.
2. **Validate role/relevance on opened development.** Prerecord a human review rubric distinguishing topic, direct contract context, explicit threshold/date/settlement evidence, unsupported match, and unknown. Review accepted and rejected pairs, including the nine union articles, the 16 removed hypotheses, the two Argentina additions, L1/L2 disagreements, and sampled nonretrieved alternatives. Preserve group and article clustering; count false promotions, potential recall losses and unknowns. Do not reinterpret the failed strict 40-case audit as a pass or tune against its protected decisions.
3. **Fresh audit only after the policy and source gate.** Freeze a separate untouched audit frame, split by certified event family/article episode, and specify accepted/rejected/nonretrieved sampling and abstention criteria before opening it. If this passes, choose representative development event windows including low/no-news days; recover bounded complete overlapping news partitions plus a seven-day warm-up, with receipts and zero-row reconciliation. Count independent stories/events and admitted contract-days before power work. No bulk trade/news fetch or predictive fit is warranted now.

The original support ledger, fixed comparison, and failed old audit are unchanged. This diagnostic made **zero** predictive admissions and no model promotion.
