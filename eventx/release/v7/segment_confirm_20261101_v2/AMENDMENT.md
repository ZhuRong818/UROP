# Segment confirmation test: runner v2 (1 Nov 2026)

The v1 runner (`eventx/tasks/run_v7_segment_confirm_test_20261101.py`, frozen in
`eventx/release/v7/segment_confirm_20261101/`, commit a7f90ca) stopped in `select` with `Range budget exceeded`
after reading 66,511,706 bytes of identity, event-type and clock columns from 12 July hours (11 row groups per hour,
for the wider ID range [0x48, 0x80)). No price, quote or outcome column was read and no contract was selected. The
partial folder is kept at `data/v7/segment_confirm_20261101/test/cohort_failed_attempt1_identity_budget/`.

v2 differs only in the identity-read budget (256 MiB instead of 64 MiB) and its release folder. Protocol, hypotheses,
window, ID range, eligibility, fetcher and evaluation are unchanged (`protocol.json` copied verbatim from v1).
