# Extraction diagnosis and version 0.2

## Diagnosis

The bottleneck is semantic binding, not a shortage of extracted predicates.
The previous parser generated332 candidates in70 opened articles, but more output
did not establish correct actors, objects, sources, or article–contract links.

| Failure | Cause | Revision |
| --- | --- | --- |
| `the company of his resignation` becomes recipient | Nominal attachment treated as resolved identity | Keep `the company`; retain extension only as an unresolved alternative |
| Partitive `some` loses the asset | Noun chunk too short | Retain full complement evidence alongside the base and head; do not discard it |
| `Is` becomes speaker | Bad headline parse propagates into attribution | Flag non-nominal heads; never verify attribution from a dependency edge alone |
| History/share order becomes speaker | Grammatical noun is not necessarily a communicating source | Keep communicator type and identity unverified, including for nominal heads |
| Pronouns/fragments/encoded text | Surface evidence conflated with canonical identity | Explicit referent, fragment, possessive and encoded-text risk flags |
| Perfect tiny synthetic suite but poor real text | Known regression cases omit realistic ambiguity | Preserve failures and distinguish software safety from semantic accuracy |

The same parser supplies all these hypotheses. Agreement between its noun chunks
and dependencies is not independent verification. Negation detection still does
not resolve factuality; a year mention still does not identify the contract episode.

## Implemented v0.2

Separate module: `eventx/v6/compositional_evidence_v02.py`.
It offers live `extract(article, nlp)` and deterministic `revise(v01_record)` APIs.
The trial used cached v0.1 outputs: no new model inference or external requests.

Each role now retains:

- base source span and syntactic head;
- optional extended spans with unresolved attachment;
- structural risk flags;
- a separate unresolved canonical entity.

All expanded roles are demoted to alternatives, not silently discarded. Original
role evidence is restored in the legacy actor/object/speaker fields. These legacy
fields remain candidates, not resolved entities. Attribution edges preserve their
speaker, epistemic and negation evidence but explicitly have
`verified_attribution=false`. Relation readiness never auto-admits a contract link.

The checks do not classify History as metaphorical or identify the true source of
a share-order report. They correctly leave those semantic questions unresolved.
No special rules name any of the problematic headlines, companies or people.

## Completed checks

Canonical artifacts: `data/v6/compositional_evidence_v02_20260924/`.
Predecessor code/output manifests verified before replay; receipt saved before
processing. Exact source spans and new manifest hashes verified afterward.

-70 opened articles,332 preserved predicate candidates.
-25 optional expansions retained, none promoted to resolved entities.
-54 role records structurally flagged. These are warnings, **not54 proven errors**;
 pronouns are included because their referents remain unresolved.
-19 speaker candidates;17 attribution edges;0 verified attribution edges.
-58 combined tests pass, including8 new v0.2 tests.
-0 predictive admissions; no holdout, predictive training or annotation access.

Legacy synthetic actor9/9, speaker4/4, proposition4/4 and other checks are unchanged.
The base-span object score is5/6, down from v0.1's6/6: the full partitive now lives
in the alternatives instead of being asserted as the sole object. This is a
deliberate representational tradeoff, not an accuracy improvement. The dedicated
test verifies that the full partitive evidence is retained and unresolved.

Inspection confirms the notification recipient is again `the company`; `Is` is
flagged non-nominal. History and the share order remain unverified, not “fixed.”

## Revised next-version strategy

Do not keep chasing a perfect12-case score with wider parser expansion rules.
Use v0.2 as an uncertainty-preserving interface, not the final linker.

1. Define a bounded attachment/source-resolution task with contrast classes:
   partitive asset vs notification topic; organization name vs dangling possessive;
   actual source vs metaphor/passive-source omission; literal vs figurative action.
   Preserve source offsets and permit unsupported/ambiguous outputs.
2. Compare parser-only alternatives with a separately versioned semantic resolver
   (span-constrained SRL or structured extraction). Select the model and verify its
   license, local availability and provenance before acquisition or execution.
   A relevance reranker score alone cannot certify a role or resolve truth.
3. Test both success and abstention: exact supported spans, false semantic promotion,
   missed supported relations, and changes on the same opened article set. Report
   coverage together with errors; all-unknown output is not a successful linker.
4. Then complete article–contract compatibility and the retrieval/source-support
   ledger. Broader outcome-open development is allowed under the existing exclusions;
   reserved audit data must not become another tuning set.
5. Only after the method and acceptance rule stabilize, preregister one fresh bounded
   link audit. Predictive M/T/R/N experiments still require source, family and
   inference gates. This implementation neither closes nor bypasses those gates.

The paper question remains incremental news information. This is an extraction
revision, not a change to the frozen predictive protocol or a positive news result.
