# V6 boundary adjudication — recovered rule evidence

Two bounded Lumid `/retrieve` calls succeeded. Exact ID reconciliation and receipt
hashes pass:57/57 Kalshi records and7/7 Polymarket records, all filtered to ingestion
before22 July2026.49 Kalshi records contain primary rules and all7 Polymarket
records contain descriptions. Eight LeBron-next-team contracts still lack rule text.
No prices, resolved winners, labels or forecast outcomes were requested.

## Review file

`data/v6/boundary_adjudication_enriched_20260916/adjudication_packet.jsonl`

Contains57 priority tasks:40 submitted must-links needing confirmation,15 unresolved
family pairs and2 related-story pairs. Every unresolved family task now has supplemental
source records attached to its existing contract context. This does not mean every
side has complete rules. Existing decisions/rationales and reviewer identifiers remain
unchanged. Fill a separate copy's `adjudicator`, `adjudication_decision`, `evidence_refs`
and `rationale`; do not overwrite immutable artifacts.

This packet reveals the first decision and rationale: it is an adjudication/evidence-
follow-up packet, NOT a blind independent second review. The original blank second-
review packets remain available for independent confirmation of all candidate boundaries.
No evidence of a second judgment per pair has been fabricated.

## Substantive clarifications from inspected rules

- **Next DNI versus Acting DNI:** the next-DNI rule explicitly excludes acting/interim
  officeholders, whereas the Acting-DNI contract includes the acting appointment.
  Thus they are not equivalent payout propositions. They may still concern a shared
  succession process; the exclusion alone does not establish safe split independence.
- **Coding versus overall AI rank:** the coding rule names Datacurve DeepSWE; the
  math rule names the Arena Math leaderboard. These are not automatically identical
  measurements merely because the snapshot date matches. Overall versus math and
  consecutive-day dependence still require a stated family policy.
- **Peace deal, ceasefire and peace talks:** Polymarket supplies detailed definitions.
  A signed peace framework can qualify without an effective ceasefire; ceasefire
  requires a mutually agreed general suspension; talks require a qualifying in-person
  diplomatic meeting. Shared conflict is not proof of logical equivalence, nor does
  lack of equivalence prove split independence.
- **USA–England matchup:** the rule concerns any2026 World Cup match, with resolution
  when both teams qualify for that matchup. Group-D winner rules are recovered,
  but the required tournament-path/bracket evidence remains outside these records.
- **Album sales measures:** matching album/week remains documented; the returned
  rules still do not supply the conversion/composition definition between the measures.
- **Treasury yield:** the month-end wording remains less precise than the explicit
  June30 daily-yield observation; the additional text does not settle that ambiguity.
- **LeBron announcement versus next team:** the announcement rule is now explicit
  about naming a team and source-agency announcement, but eight next-team records
  still lack their corresponding resolution rules.

These are assistant evidence notes, not replacement human reviews or final adjudications.
Descriptive metadata retrieved now remains retrospective semantic evidence; historical
availability/admission requires its separate proof. No live-world facts are inferred
from contract descriptions.

## Integrity and next step

Source rows and query receipts:
`data/v5/provenance_recovery_20260908/v6_adjudication_{kalshi,polymarket}_20260916.*`.
SQL/selection manifest: `data/v6/boundary_adjudication_20260916/`.
Enriched release and count/hash reconciliation:
`data/v6/boundary_adjudication_enriched_20260916/`.

Next: evidence follow-up on the15 unresolved cases and independent confirmation of
proposed links; adjudicate differences and version any revised split/sampling plan.
Prior265-pair risk preview is not an admitted335-pair test. No graph, original packet,
quarantine or research freeze changed during this recovery.
