# Clean-text and speech-binding development check

Verified 20 September 2026; artifacts retain their 19 September run identifier.

Of 138 fixed development candidate pairs, 11 pairs from two articles remain
provisional event-channel candidates. 88 were rejected for unbound speaker/occasion;
39 failed subject/relation checks after sidebar masking. Zero predictive admissions.

Evidence: `data/v6/clean_speech_20260919/report.json`, `cases.jsonl`,
`ranking_inputs.jsonl`, and `manifest.json`. All seven input/output hashes match.
156 related tests pass, including six new synthetic checks.

The preprocessing masks recognized sidebar tails while preserving offsets and raw
records. Speech matching requires a literal speaker/utterance pattern and the
specified occasion. This is conservative lexical matching, not a semantic parser.
Tail masking may remove valid later text; existing sentence splitting remains limited.

This checks previous candidates only, not end-to-end recall. Cleaned ranking inputs
were generated; neural ranking was not rerun. Surviving links do not establish a
quoted keyword, settlement predicate, truth, source certification or audited precision.
No new reviews, predictive training or holdout outcomes were opened.

Next: apply preprocessing in a new end-to-end development retrieval version and
compare coverage/failure types. Do not promote these pairs based on this check.
