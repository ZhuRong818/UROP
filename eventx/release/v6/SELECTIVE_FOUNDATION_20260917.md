# Selective matcher foundation 0.1

User authorized proceeding with the separate redesign implementation on17 September.
This adopts engineering work only, not a new audit, cohort or predictive freeze.
The existing proposal and failed audit remain unchanged.

Implemented `eventx/v6/selective_vnext.py` with evidence-backed typed fields, exact
text-version certificates, half-open temporal validity, contract-close checks,
entity/predicate/metric/period compatibility, explicit abstention and stable ranking.
Initial engineering adapter: same-period measurements. Other contract types abstain;
this is a bounded implementation choice, not an approved restriction on research claims.

Twenty synthetic tests pass in `eventx/tasks/test_selective_vnext.py`. Fixtures are
synthetic, not human-reviewed labels. Tests include negative-direction evidence,
wrong entities/metrics/periods, missing/conflicting fields, invalid quotes, future
revisions, changed text, closed contracts, empty pools, ties and nonfinite scores.

## Deliberate limits

- This is a schema/compatibility foundation, NOT a complete automated semantic matcher.
  Callers provide structured fields; extraction and typed alias resolution remain.
- Quoted spans establish traceability, not truth of a canonical semantic value.
  Certificate flags must come from an audited upstream process, never be auto-set.
- Raw-score ranking is not calibrated acceptance. `rank_compatible` returns no
  supported links until an acceptance policy is separately implemented/validated.
  All decisions explicitly keep `predictive_admitted=False`.
- No spot-price-to-future-threshold adapter yet; it must not be conflated with
  same-period measurement matching. Exact settlement entailment is not required.
- No model tokenization/truncation path exists in this foundation; a later model
  adapter must enforce evidence retention. No real-data precision/coverage reported.
- Existing contracts lacking certificates cannot be admitted by this implementation.

Next: implement evidence-backed extraction and typed aliases on opened development
text, with structured unknown/conflicting states. Then add explicit relevance versus
background acceptance logic. Do not use the40 opened cases as independent validation.
New audit thresholds, useful coverage/yield and review budget still require a freeze.
