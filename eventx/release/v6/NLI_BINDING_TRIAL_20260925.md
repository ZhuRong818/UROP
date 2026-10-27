# Bounded NLI binding trial — do not promote

Completed overnight24–25 September Singapore time; artifact names retain the
24 September start date. This is an assistant-authored development diagnostic,
not independent gold evaluation and not an end-to-end article–contract resolver.

## Model and execution

Local inventory found a parser, embedding encoder and relevance reranker, but no
dedicated entailment model. Downloaded `cross-encoder/nli-deberta-v3-small`, pinned
revision `fa2804872c3b4bd748f38c0185cc85775361e735`, Apache-2.0 license.
The [publisher model card](https://huggingface.co/cross-encoder/nli-deberta-v3-small)
describes SNLI/MultiNLI training and contradiction/entailment/neutral labels.
Downloaded code/config and weights do not establish historical feature eligibility.

Initial sandbox download failed DNS; approved network retry succeeded. No research
text uploaded. Eight model files downloaded, hashed in
`data/v6/nli_model_20260924/manifest.json`. Local CPU/float32 inference used pinned
files, eager attention, two threads and seed0; runtime versions recorded. All logits
finite, no input truncation. Deprecated torch_dtype warning was nonfatal.

The18-probe specification and receipt were written before inference. One model,
one rule: entailment>=0.8 and margin>=0.2 over either other class. Thresholds were
not tuned. These scores are not calibrated probabilities of correct entity binding.
Hypotheses were manually authored, not generated from the role graph, so this tests
semantic scoring feasibility only. v0.2's all-abstain behavior is a safety comparator,
not a competitive semantic-resolution baseline.

## Result

| Measure | Result |
| --- | ---: |
| Supported references selected | 8/8 |
| Unsupported references incorrectly selected | 3/10 |
| Strict supported-over-unsupported ranking wins | 8/8 |
| v0.2 semantic verifications | 0/18 (all abstain) |
| Predictive admissions | 0 |

The three unsupported selections are:

- `History says...` → a person named History spoke: entailment0.9942256808.
- `bought time` → purchased a financial asset:0.9828613997.
- `is said to...` → a named company announced it:0.9605829120.

These failures show why ranking wins do not establish safe absolute acceptance.
No threshold rescue, model promotion, prediction training, new annotation, or
protected-data access followed. The v0.2 extractor and all older results remain
unchanged. Five decision/specification unit tests pass; model/trial hashes verified.

Canonical evidence: `data/v6/nli_binding_trial_20260924/` (specification, receipt,
all scores, report, runtime and manifest). Runner: `eventx.tasks.trial_v6_nli_binding`.

## Next decision

Reject this model as a stand-alone role/source acceptance gate. Do not extrapolate
its3/10 error rate to real articles, or its8/8 ranking result to retrieval quality.
Some synthetic contrasts are deliberately simple, and the forecast negative has
awkward tense; a stronger future test needs natural minimal contrasts and explicit
source/asset spans, not only paraphrase entailment.

Next evaluate a span-constrained structured extractor that must name the source
and traded object using exact text evidence, distinguish literal/figurative meaning,
and return unknown when the source is omitted. Freeze its model/prompt/schema and
structural validity tests before comparing. A quotation proves span presence, not
semantic correctness; report false binding and missed valid bindings together.
Model licensing/runtime selection remains required before that execution. Keep
these18 probes as regression cases, never call them a fresh confirmation set.

Complete that bounded comparison before deploying on the70 opened articles or
requesting another independent audit. Source/family/inference gates remain intact.
