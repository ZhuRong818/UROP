# V6 candidate-ID order-rotation diagnostic

Date: 26 September 2026. This separately versioned development diagnostic tests the candidate-ID interface that failed the prior semantic gate. It uses the same ten assistant-authored, previously seen sentences and the same pinned local Qwen2.5-0.5B-Instruct revision `7ae557604adf67be50417f59c2c2f167def9a775`. These are known regression cases, not independent reference data. No real article, reserved review label, protected outcome, or predictive model was accessed.

## Prerecorded design

For each sentence and each of source, traded object, and mode, the original candidate values were cyclically rotated through every digit ID position. Sentence, system prompt, question wording, candidates, reference, and single next-token digit-logit selection rule stayed fixed. Shift zero exactly reproduces the original candidate order. The fixed plan covers 30 case–field groups and 97 prompts: 22 source, 25 traded object, and 50 mode. Every candidate appears once at every available ID within its group. This checks cyclic order sensitivity; it does not exhaust all permutations or compare another decoder.

`spec.json` and `receipt.json` were written before inference, with hashes of the runner, prior candidate-ID runner and manifest, and model manifest. The runner verified prior outputs and all nine model files before inference. The model ran locally in CPU float32 with two threads and seed zero. No free-form generation, retry, repair, threshold adjustment, or candidate change was made after seeing outputs. The original trial was left intact.

## Result

| Field | Correct selections / prompts | Value invariant across rotations | False bindings | Missed supported bindings |
| --- | ---: | ---: | ---: | ---: |
| Source | 9/22 | 7/10 groups | 12/22 | 1/22 |
| Traded object | 12/25 | 4/10 groups | 11/25 | 2/25 |
| Mode | 9/50 | 0/10 groups | — | — |

Overall, the selected value changed under rotation in 19/30 case–field groups. Mode selected ID `4` in 34/50 prompts, even though each mode label occupied that ID once per sentence. At shift zero, all 30 selected IDs and values matched the prior trial. A rotated order sometimes corrected a field and sometimes broke one; the resulting fractions are correlated development diagnostics, not accuracy estimates. Several source/object false bindings persisted across all rotations, so candidate order is not the only failure. The saved `records.json` includes every prompt, candidate mapping, token ID, logit, selection, reference, and error flag.

The result confirms substantial order sensitivity in this digit interface, especially for mode. It does not identify a deployable extractor or justify choosing a favorable order. Candidate-ID v0.1 remains failed and unpromoted. Do not deploy either trial to real articles, promote evidence, run a new independent audit, or use these outputs for prediction.

## Integrity and next work

The output manifest covers the spec, receipt, raw records, report, and runtime metadata; all output hashes and the preregistered input hashes verified after inference. There were zero predictive admissions. The model revision is read from the canonical manifest receipt in this run.

The next V6 work is the already planned retrieval and support ledger plus fixed L0/L1/L2 development comparison. If structured extraction is revisited, create another preregistered version with a different interface, explicit unknown handling, and both false-binding and missed-binding checks. Keep these ten sentences as known regressions; any new independent assessment needs a fresh sealed design.

Artifacts: `data/v6/candidate_id_order_rotation_20260926/`.
Runner: `eventx.tasks.trial_v6_candidate_order_rotation`.
