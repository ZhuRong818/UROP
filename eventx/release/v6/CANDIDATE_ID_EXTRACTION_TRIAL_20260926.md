# V6 candidate-ID extraction trial: format fixed, semantic gate failed

Date: 26 September 2026. This is a separately versioned development trial on the
same ten assistant-authored sentences used in the failed structured-span trial.
They are known regression cases, not independent reference data. No real articles,
reserved review labels, protected outcomes, or predictive models were accessed.

## Fixed design

The local pinned Qwen2.5-0.5B-Instruct model from the prior trial was reused at
revision `7ae557604adf67be50417f59c2c2f167def9a775`. The model manifest
verifies all nine files. For each sentence and each of `source`, `traded_object`,
and `mode`, the specification lists finite candidates including null where
applicable. Candidate order was shuffled by the fixed seed 20260926 and saved
before inference. The model selected the highest single next-token logit among
allowed digit IDs, with a fixed tie rule. The chosen ID was mapped to its
predeclared exact span, null, or mode value. There was no free-form generation,
retry, answer repair, threshold tuning, or post-result candidate change.

The specification and receipt were written before inference. The original trial,
extractors, and all frozen experiment files were left unchanged. This method
forces structural validity by construction; it does not measure the model's
ability to obey a JSON schema. Candidate-ID logits are not calibrated confidence.

## Result

| Check | Result |
| --- | ---: |
| Structurally valid mapped records | 10/10 by construction |
| All three fields correct | 0/10 |
| Source correct | 3/10 |
| Traded object correct | 5/10 |
| Mode correct | 1/10 |
| False source bindings | 7/10 |
| False object bindings | 5/10 |
| Missed supported source/object bindings | 0/6 |
| Predictive admissions | 0 |

All seven sentences whose reference source is null received a non-null source.
Five of the seven sentences whose reference traded object is null received a
non-null object. The model selected mode candidate ID `4` in nine of ten cases,
although the fixed shuffle mapped that ID to different labels. This strong ID
preference means the field scores cannot isolate semantic competence from the
candidate-token interface. The case-level records retain every prompt, candidate
list, allowed token ID and logit, chosen value, and score.

The prior unconstrained trial had 0/10 valid records. This run shows that a finite
ID mapping removes its format failure, while this specific model/interface still
fails the bounded field checks. Neither run provides an independent accuracy or
forecasting result. Do not promote this method, deploy it on the 70 opened real
articles, or reinterpret the old malformed responses as repaired outputs.

## Integrity and next work

The code, fixed specification, model manifest, and prior trial manifest hashes were
receipted before inference. The new manifest's input and output hashes were
verified after the run. A pre-run structural check covered all ten candidate lists;
a synthetic scoring check covered false-binding and missed-binding flags. No
protected evaluation artifact was opened or generated.

`runtime.json` has a null `model_revision` field because the runner looked at the
manifest top level. The canonical revision is present at
`data/v6/span_model_20260925/manifest.json` → `receipt.revision`; the model files
and manifest hashes were verified. The hashed runtime artifact is preserved as run.

If a further model comparison is useful, prerecord a new version that checks
candidate-order invariance and scores full candidate text or uses schema-constrained
decoding. Include unknown and both false bindings and missed supported bindings.
Retain these ten sentences as known regressions. Complete the V6 retrieval/support
ledger and fixed L0/L1/L2 development comparison before another independent audit
or any predictive training.

Artifacts: `data/v6/candidate_id_extraction_trial_20260926/`.
Runner: `eventx.tasks.trial_v6_candidate_id_extraction`.
