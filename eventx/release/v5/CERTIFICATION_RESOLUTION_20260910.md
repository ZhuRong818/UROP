# V5 inference and source/family certification investigation

Date: 2026-09-10. **Not resolved; concrete checks completed without new outcomes.**
No protocol gate relaxed, candidate frozen, new research labels read, V4 payloads
opened or external provider message sent. Existing v1/v1.1 artifacts remain intact.

## 1. Inference: a different candidate tested and rejected

Investigated Ibragimov–Müller grouped-t inference. Its validity requires sufficiently
independent, approximately Gaussian group estimators; arbitrary group assignment
does not establish those assumptions. The original paper makes this dependence
requirement explicit: [author-hosted paper](https://www.princeton.edu/~umueller/tstat.pdf).

Implemented a diagnostic with four disjoint family/time diagonal groups, followed
by Student-t(df=3). Tested 1,000 synthetic datasets per each of 12 scenarios (six
processes × 35/140-day calendars); no bootstrap draws are used by this analytical
method. It is a new development screen, not independent certification or full
decision-hierarchy power. Fixed configuration/seed and all outputs are retained.

| Scenario | Days | Nominal 95% coverage | False positive lower bound |
|---|---:|---:|---:|
| IID | 35 | 96.1% | 2.4% |
| Family/day | 35 | 95.2% | 1.9% |
| AR(0.9) | 35 | **84.0%** | **8.9%** |
| Regime shifts | 35 | **86.3%** | **6.6%** |
| AR(0.9) | 140 | **92.3%** | 3.5% |
| Regime shifts | 140 | **85.4%** | **7.5%** |

The diagonal candidate uses approximately 25% of panel rows and averages groups;
it is not the current all-row estimator. Even favorable cells would not authorize
silently adopting that scope change. It fails the required dependence envelope, so
no candidate is selected. Software formula tests do not certify coverage.

Evidence: `data/v5/group_t_candidate_20260910/{config.json,report.json,manifest.json}`.

### What would genuinely resolve inference

The original V5 claim generalizes to new families at later calendar times. Keep it
unless an explicit new scope is approved. It needs defensible information about
dependence and sufficient genuinely distinct calendar/event episodes, not just more
rows within one regime. Historical episodes are acceptable; this is not a request
to wait automatically for future data.

There is no informative universal standard-error repair under unrestricted shared
regime shocks. A counterexample is every family/date having the same random loss
shock Z: thousands of rows then contain one draw, not thousands of independent draws.
This explains the need for assumptions; it is not a statement that EventX actually
has that extreme dependence.

Two possible next designs, neither silently adopted:

1. **Retain the current generalization question (recommended).** Establish plausible
   separation/mixing assumptions and enough unopened historical episodes; validate
   an inference design under that declared envelope and full pipeline before labels.
2. **Narrow to conditional performance on the realized calendar/cohort.** This is a
   different estimand and cannot support new-calendar generalization. A conditional
   or bounded prequential method would need a new protocol and its own proof/tests;
   it must not be used as a cosmetic fix for the failed unconditional intervals.

No smaller critical value, changed promotion margin or favorable-method selection
has been used. Broad generalization inference remains uncertified.

## 2. Live source certification probes

Performed read-only metadata queries via Lumid `/retrieve`:

| Request | Outcome |
|---|---|
| Accessible archive/version/request/response inventory across schemas | HTTP200, 103 schema-field rows; no matching news/market-metadata version archive exposed |
| Relevant-table visible trigger inventory | HTTP200, zero rows; visibility-limited, not proof of absence |
| Twenty-run retained-news/lineage reconciliation | Sandbox ConnectError retained; approved retry HTTP400, cause unconfirmed |
| Three-run metadata-only fallback | HTTP200, all three records recovered |

The three fallback runs still show failed/abandoned-cleanup status and null inserted,
updated and failed-row counters. This cannot reconstruct requested coverage or
prove that successor retries recovered all gaps. Nor does it invalidate every
committed article. Request only the missing proof, not another undifferentiated dump.

No accessible response supplied historical content versions, a row-immutability
guarantee, complete historical status history, or sufficient interval reconciliation.
Therefore the source admission gate remains false. Accessible schema search is not
proof that the provider has no private archive; provider coordination is now needed.

Prepared **but did not send** `LUMID_CERTIFICATION_REQUEST_20260910.md`, containing
exact example run IDs, required fields, known scope and successful/failed probes.

Receipts: `data/v5/provenance_recovery_20260908/certification_*.json` and linked payloads.
Queries: `eventx/release/v5/certification_requests_20260910/` and
`data/v5/certification_probe_20260910/`. Three completed and two failed attempts;
an attempt may include retrieval and download, not just one HTTP call.

## 3. Family review: known links resolved, full boundaries not certified

Reviewed six explicitly scoped sets: prior two golf tournaments, California 2026
gubernatorial primary/general election, Wimbledon men's and women's cross-venue
contracts, and the named Olivia Rodrigo album's sales/debut/ranking lifecycle.
These are split-isolation dependencies, not claims of identical settlement rules.

- **28 reviewed must-link edges**, spanning **264 contracts** across six scopes.
- 1,551 venue-event candidate nodes become **1,523 provisional components** after
  these known merges; that is not the number of independent families.
- Graph consistency passes; a proposed split across a known link is rejected.
- Missing final boundary reviews explicitly block certification. Annual/season,
  multi-leg and other cross-venue bridges plus historical contract semantics remain
  unresolved. **Zero final families approved.**

This is more than recovering event IDs: the review identifies concrete split leaks
and preserves their evidence. It does not invent negative-edge evidence for the
remaining components or turn unknown groups into certified singletons.

Evidence: `data/v5/family_certification_20260910/{reviewed_edges.json,
candidate_components.json,report.json,manifest.json}`.

## 4. Execution boundary and next action

This pass completed live source probes, scoped graph review and an alternative
inference screen. Further source certification
requires provider evidence; additional graph closure requires full relevant contract
semantics and documented boundary review. New-calendar inference additionally needs
an explicit defensible dependence design. These are not gates that code can mark
true just because an API responds or a graph is internally consistent.

Keep new research labels closed. Obtain/attach the provider evidence request response,
then certify exact fields/windows and finish the source-backed family boundaries.
Do not change the inferential claim without explicit approval. No future collection
requirement, cohort exclusion or new holdout date has been imposed in this task.
