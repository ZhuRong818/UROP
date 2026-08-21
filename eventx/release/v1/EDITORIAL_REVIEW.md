# EventX v1 editorial audit

**Reviewed:** 2026-07-31  
**Scope:** final report, release index, canonical result artifacts, and integrity
receipts

## Outcome

The final report's metrics, dataset identifiers, model decision, and holdout state
match the canonical artifacts. No scientific result was changed.

## Checks completed

- Development and OOT dataset IDs match their frozen manifests.
- All reported AP, Brier, prevalence, row, market, and positive-label values match
  the canonical JSON outputs.
- Incremental development metrics use the documented sign convention:
  reference Brier minus candidate Brier.
- KOL/news audit metrics and denominators match their rule-freeze manifests.
- The original test exposure is disclosed as descriptive and noncanonical.
- The replacement holdout is described as evaluated once and consumed.
- The report does not promote an unauthorized news or KOL candidate.
- Causal, trading-profit, and broad-generalization claims are explicitly excluded.
- Pilot scope is distinguished from the proposed full EventX benchmark.

## Publication issue found

The frozen category field has at least one semantic error: the Karen Bass Los
Angeles mayoral market is labeled `sports`. The source cohort remains unchanged to
preserve its hash. The report and datasheet now disclose this defect, and
category-stratified claims are prohibited until corrected metadata are versioned.

## Remaining blockers

The result is ready for internal review, but the data package is not cleared for
public redistribution. Licensing, upstream-rights, privacy, dual-use, secret-scan,
clean-room reproduction, maintainer, archive, DOI, and citation work remains. See
`PUBLIC_RELEASE_CHECKLIST.md`.
