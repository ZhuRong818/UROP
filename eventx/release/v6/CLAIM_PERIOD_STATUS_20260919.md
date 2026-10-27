# Claim-role and period diagnostics

Applied a separate diagnostic layer to all180 fixed development pairs. Cached neural
scores unchanged; previous output hashes verified. No training, rescoring, thresholds,
new annotation or protected outcomes.

| Heuristic role | Period screen | Pairs |
|---|---|---:|
| Event update | Before stated deadline | 8 |
| Opinion/assessment | Before stated deadline | 1 |
| Opinion/assessment | Expired period | 3 |
| Opinion/assessment | Unresolved period | 3 |

Eight update pairs share one US–Iran article and differ in deadline. Seven assessment
pairs come from SpaceX commentary and Musk's Anthropic opinion. Roles are quoted-span
heuristics, not human gold. Mixed fact/opinion sentences may be conservatively tagged
as assessment. Zero verified settlement claims and zero predictive admissions.

Full-date question deadlines and explicit end-of-month periods are screened against
source availability even without close_time. Recorded-close rejection is preserved.
Invalid/multiple bounds and IPO-relative periods remain unresolved. Date-only cutoff
timezones are uncertified: same-day/next-day arrivals remain ambiguous; expiration
requires at least two calendar dates difference. Before-deadline is not certification.
Year-only/quarter periods, precise intraday cutoffs and exact measurement-to-settlement
alignment remain unimplemented. Opinion cues take precedence over numeric observations.

All140 related tests pass, including10 new tests. Artifacts:
`data/v6/claim_period_20260919/` (receipt,180 cases,report,manifest).
Implementation:`eventx/v6/claim_period.py`; runner:`eventx/tasks/check_claim_period.py`.

Next assess article/event-level yield, not pair-count success. Keep expired pairs
excluded, relative dates unresolved and opinions separate. Historical metadata/source
certification remains required before feature admission; no new review packet yet.
