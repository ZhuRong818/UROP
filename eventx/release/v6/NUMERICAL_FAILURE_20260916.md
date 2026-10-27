# V6 local reranker numerical failure — retained diagnostic

The first hybrid builder attempt stopped on `Nonfinite reranker output`, before
publishing a release. Stack: torch2.14.0, transformers5.17.0,
sentence-transformers5.7.0. All reranker parameters were finite float32.

A non-research smoke pair (capital of France / Paris) also returned NaN with both
SDPA and eager attention. Therefore this is not evidence of poor research relevance
or an article-specific label. Exact lower-level cause remains undiagnosed.

Next diagnostic: pinned stable stack, same model revision and same smoke input.
Do not accept nonfinite scores, substitute zero, or choose a model based on outcomes.
No forecast data or human labels were opened; failed attempt produced no final
hybrid dataset. Model downloads and original V6 pilot are retained unchanged.

Follow-up: torch2.8.0 / transformers4.57.1 / sentence-transformers5.1.1 still
returned NaN on the same float32 smoke input, including one-thread eager attention.
Largest absolute stored parameter was4.715854167938232, not an exploding stored
weight. Converting the same model to float64 with eager attention produced a finite
logit8.500707. The lower-level float32 failure is not yet isolated; do not claim a
particular library caused it. The builder now uses explicit float64/eager for both
models, checks a non-research smoke input first, and rejects nonfinite embeddings
and reranker scores. This is a numerical execution change, not hypothesis tuning.

The all-float64 batch reached development article25 but was stopped for excessive
runtime before publication. A bfloat16 reranker smoke batch of32 repeated non-research
pairs completed in0.7047s with finite scores. On16 synthetic pairs (four distinct
examples repeated), bfloat16 versus float64 maximum absolute logit difference was
0.01905536651611328 and rank order matched. This is a bounded smoke test, not a
global numerical-error guarantee. Final retry retains float64 encoder and uses
bfloat16 reranker/eager attention; same weights, candidate policy and no gold labels.
