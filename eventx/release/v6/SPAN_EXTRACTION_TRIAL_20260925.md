# Structured span extraction: feasibility test failed

Tested Qwen/Qwen2.5-0.5B-Instruct locally on the10 source sentences underlying the
previous18 NLI probes. These are known, assistant-authored development cases, not
independent gold. No real-article deployment or predictive evaluation occurred.

## Fixed setup

Model revision `7ae557604adf67be50417f59c2c2f167def9a775`; nine files downloaded
with approved network access. The [publisher model card](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct)
lists Apache-2.0 licensing and an instruction-tuned0.5B model. Model files are hashed
in `data/v6/span_model_20260925/manifest.json`. No research text uploaded.

One prompt, three fields (`source`, `traded_object`, `mode`), greedy local CPU
float32 generation,160-token output ceiling, no truncation, retries or answer repair.
Prompt, references, model/code hashes and generation settings receipted before
inference. Runtime package versions retained. Ignored sampling-parameter warnings
were nonfatal because generation used do_sample=false.

Span constraints were enforced **after generation** by strict JSON-key/enum and
exact-substring validation, not by constrained token decoding. All occurrences of
a quoted span are retained, avoiding invented offset disambiguation. Source means
an attributed communicator, not automatically the grammatical actor. Missing or
metaphorical sources must be null; traded_object excludes figurative transactions.

## Result

-10/10 responses rejected: all fail the exact-key schema check.
-0 valid records;0 predictive admissions.
-5 structural-validator tests pass; model and trial manifest hashes verified.
-All raw answers retained; no sanitization or rerun after inspecting outputs.

The model repeatedly invented the key `an assertion or forecast`, omitted required
keys, and used string `unknown` rather than null. Inspection also reveals potential
semantic errors: a purchasing bank treated as a source, notification labelled
negated, and a figurative purchase labelled literal. Those observations are
qualitative diagnostics, not a formally scored semantic accuracy result: all
records failed the output contract first.

The end-to-end field checks therefore fail for all10 cases. Semantic false-binding
rates conditional on valid records are **undefined**, not zero. Zero admissions
reflect validator rejection, not successful semantic abstention. This is not a
like-for-like accuracy comparison with the previous NLI18-probe classification.

## Decision

Do not promote this model/prompt combination. The failure does not establish that
all structured extraction fails; this small CPU feasibility model failed to follow
this particular output contract. Exact quotations alone would not solve semantics.

Next separate format adherence from semantic capability: a separately versioned
JSON-schema-constrained decoder or finite candidate-ID output interface, explicit
machine-readable schema, and the same retained regression inputs. The interface
must include unknown and score false bindings alongside missed supported bindings.
Do not simply delete extra keys or reinterpret unknown strings and present the
repaired records as this run's outputs. If a stronger model is tested, prerecord
that as a new model comparison, not a rescue of this failed run.

Artifacts: `data/v6/span_extraction_trial_20260925/` (specification, receipt,
per-case raw responses, runtime, report and manifest).
Runner: `eventx.tasks.trial_v6_span_extraction`.
Validator tests: `eventx.tasks.test_v6_span_extraction`.
All previous extractors, source/family/inference gates and holdouts unchanged.
