# Paper A: aggregate results appendix

Generated from existing aggregate JSON only. Scores are rounded to six decimal places.
Panels describe different samples; comparisons across panels do not estimate a model effect.

## V3.1 development

**Evidence status:** prespecified historical development selection. **Rows:** 1,460,454.

| Model | Log loss | Brier | AP | ROC AUC |
|---|---:|---:|---:|---:|
| b0 | — | 0.119209 | 0.193294 | 0.626311 |
| b1 | — | 0.119494 | 0.191378 | 0.622853 |

## V3.1 B0 holdout

**Evidence status:** one-shot B0 only; disclosed receipt-order deviation. **Rows:** 211,718.

| Model | Log loss | Brier | AP | ROC AUC |
|---|---:|---:|---:|---:|
| b0 | — | 0.107107 | 0.171628 | 0.628037 |

## V4 historical discovery

**Evidence status:** exploratory; full-discovery semantic fitting. **Rows:** 745,443.

| Model | Log loss | Brier | AP | ROC AUC |
|---|---:|---:|---:|---:|
| b0 | 0.459158 | 0.143117 | 0.206147 | 0.578684 |
| b1 | 0.461659 | 0.143817 | 0.201221 | 0.566488 |
| b2 | 0.461946 | 0.143817 | 0.202546 | 0.567415 |
| b3 | 0.465617 | 0.143959 | 0.204842 | 0.569418 |

## V5 no-terminal baseline

**Evidence status:** opened development; descriptive post-selection diagnostic. **Rows:** 364,903.

| Model | Log loss | Brier | AP | ROC AUC |
|---|---:|---:|---:|---:|
| linear_no_terminal | 0.451070 | 0.140952 | 0.226649 | — |
| tree_no_terminal | 0.407391 | 0.131106 | 0.334964 | — |

## V5 fixed-offset corrections

**Evidence status:** opened observed-news rows; context/timing/semantic. **Rows:** 9,965.

| Model | Log loss | Brier | AP | ROC AUC |
|---|---:|---:|---:|---:|
| context | 0.327533 | 0.105861 | 0.374094 | 0.797947 |
| semantic | 0.328787 | 0.106183 | 0.373029 | 0.794255 |
| timing | 0.327942 | 0.105982 | 0.372586 | 0.797075 |
| tree_no_terminal | 0.330591 | 0.107047 | 0.373627 | 0.798060 |

## V5 selected market screen, fold 5

**Evidence status:** already opened reporting fold; selection used fold 4. **Rows:** 112,616.

| Model | Log loss | Brier | AP | ROC AUC |
|---|---:|---:|---:|---:|
| original_tree | 0.348884 | 0.110880 | 0.327323 | 0.766917 |
| selected_hgb | 0.344816 | 0.109677 | 0.337805 | 0.774735 |

## V5 matched observed-article subset, fold 5

**Evidence status:** exact market/time join; opened and adaptive. **Rows:** 5,388.

| Model | Log loss | Brier | AP | ROC AUC |
|---|---:|---:|---:|---:|
| frozen_tree | 0.245673 | 0.078771 | 0.350843 | 0.853158 |
| selected_context | 0.243985 | 0.078174 | 0.350843 | 0.853158 |
| selected_market_hgb | 0.243727 | 0.078230 | 0.355478 | 0.855048 |
| selected_news | 0.244576 | 0.078265 | 0.350656 | 0.853344 |

## Provenance

Source hashes and full precision are in [evidence.json](evidence.json). Selected report/contract manifest checks are recorded there; this is not certification of every upstream source or payload.
