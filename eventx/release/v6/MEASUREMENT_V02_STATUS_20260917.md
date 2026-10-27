# Measurement adapter 0.2

Implemented separately, preserving all prior code/releases and the failed audit.
Company aliases retain source contract ID, exact subject quote and transformation:
multiword legal-suffix normalization only. These are lexical hypotheses, not verified
entity identity or point-in-time metadata. No ticker aliases are guessed.

Added spelled-out year-qualified quarters and abbreviation-aware claim boundaries.
Questions, subtitles and full supplied rule records remain separate provenance fields;
conflicting dates/metrics or subtitles do not yield accepted links. Units and fiscal
calendar equivalence remain uncertified. Semantic candidates never become predictive
admissions; the adapter does not bypass the separate temporal gate.

40 synthetic tests pass. Debug on the40 opened cases yields1 metric-mismatch candidate
and39 unsupported-contract-grammar cases, zero admissions. The registry has one company
with two aliases: Vail Resorts Inc. / Vail Resorts. This is not a useful coverage or
precision improvement. Canonical outputs: `data/v6/measurement_v02_debug_20260917/`.

## Next decision

Do not continue presenting small quarter-regex additions as a broad matcher solution.
The remaining sample spans threshold/deadline, leadership, rankings, music and sports
contracts. A useful next stage requires multi-type structured extraction with explicit
predicate/period semantics and adequate entity coverage, or an explicitly approved
narrower research scope. Keep these alternatives separate from source certification.
The current broad research claim is not narrowed automatically. No new annotation,
fresh audit or predictive evaluation is warranted by this engineering-only release.
