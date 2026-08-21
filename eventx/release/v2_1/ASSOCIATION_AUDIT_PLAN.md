# EventX v2.1 association-rule audit plan

**Protocol:** `eventx-v2.1-october-deadline-20260731`  
**State:** operational plan written before development labels are created or inspected

## Purpose and seal

This audit determines whether the deterministic v2.1 text-to-market association rule
is accurate enough to construct the preregistered news and KOL features. The matcher
may use only the frozen market question/category and contemporaneous document text or
metadata. It must not read prices, forward returns, jump labels, predictions, model
metrics, eventual resolutions, or the reserved holdout.

The selected cohort, matcher source hash, document-prefix hashes, candidate pool, blind
sample, and hidden prediction key must be fixed before a reviewer opens the sample.
Development labels remain sealed until the audit passes and the rule is frozen.

## Candidate documents and pairs

- Use news and KOL documents whose event timestamp is earlier than
  `2026-08-08T00:00:00Z` for the audit.
- Retain source event time, retrieval time, document natural key, and content hash.
- Deduplicate identical documents before pairing.
- Pair a document with a market only when the frozen broad-retrieval predicate finds
  an exact cashtag, entity phrase, subject anchor, or at least two non-generic market
  terms. This broad pool defines the set on which hard-candidate recall is measured.
- Hide the rule prediction, match reason, and match terms from reviewers.

## Frozen sample design

Use deterministic seed `83` and target 300 unique market-document pairs:

- 75 predicted matches from news;
- 75 hard unmatched candidates from news;
- 75 predicted matches from KOL tweets; and
- 75 hard unmatched candidates from KOL tweets.

Sample round-robin across corrected category and market before taking a second pair
from the same market. If a cell has fewer than 75 eligible pairs, retain every pair in
that cell and report the shortfall; do not synthesize or duplicate rows. The audit
report must state the realized composition and market/category coverage.

## Blind review rule

For each market-document pair, assign exactly one label:

- `relevant`: the document contains information that could reasonably update the
  probability of the stated market outcome at the document timestamp;
- `not_relevant`: overlap is generic, tangential, about a different event, or lacks an
  outcome-relevant claim; or
- `uncertain`: the supplied text genuinely lacks enough context for a reliable binary
  decision.

Also record `high`, `medium`, or `low` confidence and one pair-specific rationale.
Reviewers must not open the hidden key or matcher code until their review is complete.
Uncertain rows must be adjudicated without viewing the hidden prediction. Audit rows
used to revise a failed rule become development rows and cannot validate the revised
version; a revised rule requires a fresh deterministic sample excluding all previously
opened market-document/content pairs.

## Scoring and acceptance

After blind labels are final:

- precision = relevant predicted matches / decided predicted matches;
- hard-candidate recall = relevant predicted matches / all relevant decided pairs;
- F1 is the harmonic mean of those two quantities; and
- uncertain rows are reported and excluded only after blind adjudication is attempted.

The rule passes only when overall precision is at least 0.85 and hard-candidate recall
is at least 0.90, matching the sealed protocol. Apply the same thresholds separately
to news and KOL whenever that source has at least 20 decided predicted matches and 20
review-relevant pairs. A source below those support minima is `insufficient`, not
silently accepted. Confidence intervals and category diagnostics are descriptive and
cannot replace the fixed gates.

## Freeze artifacts

Before creating development labels, freeze and hash:

1. the selected cohort and cohort manifest;
2. matcher source and rule version;
3. market-specific lexical specifications;
4. deduplicated pre-development document-prefix manifests;
5. the blind sample, hidden key, completed review, adjudication, and scored report; and
6. the accepted news/KOL association manifest.

Future development and holdout documents must be processed by the identical frozen
rule. Any missingness, provider staleness, or source-specific audit insufficiency must
be disclosed and may not be repaired by inspecting labels or model performance.
