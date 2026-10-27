# Paper A claim and reproducibility review

**Date:** 10 October 2026  
**Reviewer:** Codex assistant; this is an internal consistency review, not independent scientific review.  
**Manuscript:** [Expanded Paper A draft](../../../MARKET_NEWS_PAPER_A_DRAFT_20261010.md).  
**Export:** [Full-precision evidence](evidence.json), [tables](TABLES.md), and [export manifest](manifest.json).

## Claim ledger

| Claim in manuscript | Evidence | Review and scope |
|---|---|---|
| News counts failed five historical promotion gates | V3.1 `selection_result.json`: `aggregate_oof`, `promotion_gates` | Supported for the frozen development representation; does not establish a universal news effect |
| B0 holdout AP 0.171628 and Brier 0.107107 | Already published `evaluation_result.json`: `primary_and_calibration_metrics` | B0 only; consumption receipt inspected first; no evaluator rerun |
| Historical evaluation had a receipt-order deviation | Existing consumption receipt and deviation report | Disclosed in abstract, result interpretation, and limitations |
| V4 historical B3 was worse than B0 | Existing discovery result, 745,443 matched rows | Exploratory; full-discovery semantic transform and its future-text limitation disclosed |
| Tree market forecast improved log loss by 9.683467% | V5 paired diagnostic: `paired_improvement` | Existing opened predictions, no new inference; independent redesigned-baseline confirmation absent |
| Context explains the favorable fixed-offset comparison against the original tree | Existing offset summary, 9,965 common rows | Descriptive comparison: semantic beats original tree but loses to context; no causal decomposition asserted |
| Selected news lost against stronger market and context controls | Existing joined fold-5 metrics, 5,388 identical rows | Correct selection/reporting history disclosed; reporting fold was already exposed |
| Practical positive content gain remains possible | Joined descriptive interval [−0.004221, 0.002996] | Interval includes gains above 0.001 and is selection-unadjusted; no equivalence or useful-gain exclusion claim |
| Fifty extra configurations attempted; 45 completed | Existing method survey and screen artifacts | One feature-budget stop and four failed-runtime attempts retained; no performance attributed to failed imports |
| V4 prospective confirmation is pending | Frozen V4 protocol and canonical handoff | Manuscript contains protocol information only; no protected examples, predictions, labels, or result read |
| Measurement gaps may explain news failure | Existing source/link diagnostics and control experiments | Hypotheses; no oracle-link comparison, causal identification, or exhaustive mechanism diagnosis |
| Literature already overlaps text/market controls and information absorption | Checked primary bibliographic pages and abstracts | No first-of-kind claim; recent work is preliminary; SSRN full-method review pending because page access returned 403 |

## Reproducibility completed in this task

The exporter reads an explicit allowlist of existing aggregate result and contract JSON. It reads the historical consumption receipt before the already published B0 holdout aggregate, verifies that reruns are prohibited and B1 was not evaluated, records source hashes, and checks selected V5 reports/contracts against their manifests. It does not import forecasting code, refit models, compute predictions, resample confidence intervals, or read binary examples/predictions.

The generated table appendix keeps seven cohorts/evidence panels separate and preserves missing metrics as unavailable. The figure contains point estimates in three distinct panels with cohort sizes, metric directions, and a warning that vertical scales differ. PNG was visually inspected; PDF and SVG exports are supplied for reuse. No error bars were invented for model point estimates.

The manuscript's numeric result tables are checked against six-decimal values in canonical JSON. Relative artifact links are checked for existence. These checks verify transcription and artifact references, not upstream dataset validity, inference calibration, semantic accuracy, or reproducibility of the original data retrieval.

## Remaining submission work

- Independent review of claims, chronology, selection history, statistical assumptions, and the original implementations.
- Broader literature review and full-method comparison with relevant working papers; confirm bibliography details in the venue format.
- Source-release rights and a concrete code/aggregate-data release policy. Source hashes do not establish permission to redistribute raw data.
- Author identities, affiliations, contributions, funding/conflicts as applicable, venue choice, and formatting.
- A V4 results section only after the frozen window and collection/receipt/evaluation gates; confirmation can remain incomplete if required source evidence fails.

The original 4 October manuscript and all frozen experiment artifacts are preserved. No source-admission state or research protocol was changed by this paper work.
