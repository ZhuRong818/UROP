# V6 bounded annotation audit amendment

Date: 17 September 2026. Status: **PROPOSAL FOR APPROVAL — NOT ADOPTED**.

This document proposes replacing exhaustive second review with a finite, sampled
quality audit. It does not change any frozen protocol, draw samples, open labels,
release quarantined rows or authorize predictive evaluation. The current large
annotation requests are paused pending the user's decision on this proposal.

## 1. Purpose and scope change

Answer two limited questions:

1. How often does the existing boundary review incorrectly separate a pair within
   the already enumerated candidate-boundary lists?
2. How often is the frozen hybrid retriever's top-ranked development match directly
   relevant to the specified contract proposition?

This is **bounded association-method feasibility**, not complete family certification,
an exhaustive retrieval-recall audit or confirmation of news predictive value.
Reducing annotation explicitly narrows what we can claim. In particular, passing
does NOT automatically admit the335 reserved preview pairs as an independent test.

Preserve all completed judgments,51 incorporated family edges,2 story-isolation
constraints and265 exclusions. Keep LeBron, Treasury and adjacent-series restrictions.
Do not use a sampled pass to erase known dependencies. The42 positive confirmations
remain complete; do not re-review them as part of the random samples below.

Canonical population references:

- `data/v6/reviewed_isolation_20260916/report.json`:1,149 provisional components,
  4,651 markets,335 uncertified preview pairs.
- `data/v6/retained_boundary_review_20260916/`:551 family and433 story candidate
  separations relevant to the retained preview.
- `data/v6/hybrid_development_reviews_20260916/packet.jsonl`:2,063 development pairs.
- `data/v6/hybrid_audit_20260916/`:frozen retrieval scores/selection lineage.

## 2. Fixed populations, tolerances and sample sizes

The proposed tolerances are research-design choices, not established disciplinary
standards. They require approval before drawing samples. Five percent is a tolerance
on **candidate-pair boundary errors**, not permission for5% test contamination.

| Endpoint | Finite population | Unacceptable error fraction | Random sample |
|---|---|---:|---:|
| F: missed family dependency | Existing551 retained family candidate separations | >=5% | 74 |
| S: missed same/related story | Existing433 retained story candidate separations | >=5% | 72 |
| R: incorrect direct top-one link | One fixed top-ranked development contract per eligible article, at most200 | >=10% | min(40,N_R) |

F/S sample simple random pairs without replacement from their complete respective
JSONL frames. Do not oversample by score/category and then apply unweighted bounds.
Risk-informed exclusions already precede these frames; estimates are conditional on
that screening. The frames are not all possible cross-split pairs.

For R, construct the population BEFORE any relevance annotation: among the original
200 development articles, select the highest cross-encoder-scored pair in the frozen
development hybrid retrieval pool whose pair ID occurs in the2,063-pair packet.
Use descending raw score, then ascending canonical contract ID to break ties.
No relevance cutoff, category filter or favorable substitution may be learned here.
No qualifying pair means no output; report such articles separately as abstentions.
Freeze the resulting frame, its exact N_R, score provenance and selection code.
If the frozen scores cannot be joined exactly or any score is nonfinite, stop as
incomplete; do not substitute another ranker. This tests top-one output precision
on a selected development population, not every pair in the2,063-pair packet.

If N_R<40, review the entire available output population. If N_R=0, R is incomplete.
Report N_R/200 as output coverage, not retrieval recall. A very small output population
can yield an exact finite-population result but cannot establish broad usefulness.

## 3. Sample-size derivation and inference

Allocate alpha=0.05/3 to each of F,S,R, giving simultaneous one-sided coverage of at
least95% by Bonferroni. This allocation does not require independence across endpoints.

For a fixed finite population of N cases containing K errors and a simple random
sample of n cases, X follows a hypergeometric sampling distribution. At tolerance q,
set K0=ceil(q*N). Choose n so that:

    P(X=0 | N,K0,n) = choose(N-K0,n) / choose(N,n) <= 0.05/3.

Verified locally with scipy.stats.hypergeom:

- F: N=551,K0=28,n=74 gives0.01578780853608775;73 is insufficient.
- S: N=433,K0=22,n=72 gives0.016385532121603864;71 is insufficient.
- R: n=40 is a conservative fixed cap:0.9^40=0.014780882941434608,
  below0.05/3; sampling without replacement is at least as stringent at K0.
  For N_R<40 a census determines the finite output error fraction exactly.

Invert the exact hypergeometric lower tail for a one-sided upper bound on K/N:
retain integer K values with P_K(X<=x)>alpha and report the largest retained K/N
(handle census/endpoints explicitly). Publish x,n,N and the bound, not just pass/fail.
Use the exact finite-population test at K0 for the gate.

Correlated articles/families do not invalidate randomization-based sampling from a
fixed finite frame. They DO prevent interpreting this bound as population-general
predictive uncertainty. Review mistakes themselves are not covered by the interval;
inference is conditional on the adjudicated reference judgments being correct.

These are lean zero-error acceptance designs, not high-power designs allowing many
errors. Even a low true error rate may yield a nonpass. That trade-off buys a hard
budget and must not be hidden by increasing sample size after seeing results.

## 4. Review procedure and error definitions

F/S retain the existing first judgment. Obtain one new independent judgment per
sampled case without showing prior decisions, rationales, scores or forecast outcomes.
Selection from negative cases is informative; disclose this limitation to blinding.
R gets two independent reviews per sampled top-one output. Model suggestions do not
count as human reference labels. Preserve actual reviewer identities and attestations.

- F error: an adjudicated must-link/dependency was missed by the original separation.
- S error: an adjudicated same-story or related-update link was missed.
- R success: `direct` plus `yes_proposition` applicability, supported by quoted text
  for the correct entity, event, measurement, period and contract proposition.
  Evidence need not support YES. Background/unrelated/wrong period or outcome fail.
- Insufficient evidence, unresolved disagreements and abstentions count as errors
  for the conservative acceptance calculation; report them separately from proven
  false links. Missing rules are not grounds to remove a sampled case.

One adjudicator reviews disagreements only, using evidence and both judgments.
At most one adjudication per sampled case. If still unresolved, preserve it as such;
do not solicit reviewers until agreement is obtained. Missing responses are not
replaced: endpoint is incomplete (a worst-case bound may also be reported).

## 5. Hard budget and stopping rules

Maximum distinct sampled cases:74+72+40=**186**.
New ordinary judgments:74+72+2*40=**226**.
Maximum additional adjudications:186. Absolute ceiling:**412 new judgments**.
For an R census smaller than40, reduce these totals accordingly. Existing reviews
are reused as evidence and do not count toward new work. No automatic extra batches.

For each endpoint, after completing the single frozen sample:

- **PASS:** exact one-sided test rejects error fraction>=q at alpha=0.05/3.
- **FAIL quality target:** observed error fraction>=q (a descriptive target failure,
  not automatically a statistically established lower bound).
- **INCONCLUSIVE:** observed fraction<q but the upper-bound/test requirement fails.
- **INCOMPLETE:** missing reviews, unverifiable manifests or malformed/missing evidence.

Any discovered real cross-split dependency is retained in an exclusion/correction
record even if the aggregate endpoint passes. Compute results against the ORIGINAL
frozen frame; do not drop errors, redefine the denominator and claim the repaired
frame passed. A later repaired frame is a new version, not automatically audited.

Overall bounded feasibility passes only if all three endpoints pass. Otherwise stop
this audit cycle. Do not change windows, thresholds, eligibility, semantics, ranking
or sample seeds and rerun until successful. A revised method needs a separately
approved research version and untouched audit evidence; it is not a budget extension.

## 6. Freeze and execution order after explicit approval

1. Verify source manifests and non-consumption of relevance labels; record any labels
   already seen. Previously seen labels are development evidence, never new audit gold.
2. Freeze this amendment, eligibility, three complete frames, ranker/model hashes,
   sample sizes, decision rules, review rubric and population-specific claim wording.
3. Generate one random seed once after frame freeze using system randomness; record
   it and algorithm/library versions. Sort frames by stable IDs, sample uniformly
   without replacement and publish a sampling manifest before returning any labels.
   No seed hunting. Review packets omit scores and previous answers.
4. Collect only the fixed samples; validate IDs, quotations and unchanged evidence.
5. Adjudicate once and run the prewritten exact evaluator once; publish all outcomes,
   uncertainty, abstentions and denominator counts, including negative results.
6. Decide stop/proceed at the declared scope. No sample or evaluation is run by
   drafting this proposal.

## 7. What a pass permits—and does not

A pass supports a scoped statement about error rates in the enumerated boundary
candidate lists and the fixed top-one development output pool. It permits further
development of the contract-aware association pipeline, not a news-alpha claim.

It does NOT establish absence of missed links outside top-three similarity search,
complete corpus relevance/recall, first-publication novelty, statistical independence,
point-in-time metadata validity, or performance on unseen events. The amendment
explicitly defers the prior whole-boundary certification ambition rather than
pretending a smaller pair sample delivers it. For transfer/independent confirmation,
a separate sufficiently scoped missed-link search and split design remain necessary.

Do not tune using R labels and later call R an independent confirmation. These are
development-feasibility data; subsequent model selection consumes them as development.
Do not report unweighted results on the old enriched600-pair reservation as corpus
precision. The335 preview rows remain not admitted; no automatic refilling or release.

Source availability/completeness, historical model eligibility, inference/power and
the frozen predictive protocol remain separate gates. V4 and consumed holdouts are
unchanged and protected. Social virality and KOL remain outside this amendment.

## 8. Approval required

Approve or revise the5% boundary and10% direct-link error tolerances, finite-frame
claim scope, hard budget and one-shot stopping rules BEFORE selecting cases.
Until approval, this document is a proposal only; original protocols and manifests
remain authoritative and bulk annotation requests remain paused.
