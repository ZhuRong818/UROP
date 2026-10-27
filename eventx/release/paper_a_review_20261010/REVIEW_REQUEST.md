# Paper A independent scientific review request

Date: 10 October 2026. Prepared locally; no external invitation sent and no independent reviewer assigned.

Review [Paper A revision 2](../../../MARKET_NEWS_PAPER_A_DRAFT_20261010_REV2.md), [aggregate tables](../paper_a_20261010/TABLES.md), [source evidence](../paper_a_20261010/evidence.json), [internal claim ledger](../paper_a_20261010/CLAIM_REVIEW.md) and [full-method positioning notes](LITERATURE_METHOD_COMPARISON.md). Revision 2 makes retrospective cohort selection explicit and adds methodological distinctions from two inspected preprints. It preserves all numerical results and the original manuscript versions.

## Questions requiring independent judgment

1. Is the completed study accurately described as a negative development-selection result plus a B0-only historical holdout benchmark? Are abstract/title/conclusion clear that no held-out news comparison exists?
2. Does the cohort disclosure sufficiently distinguish outcome-blind selection from membership available at each historical prediction time? The cohort uses activity over the development interval and metadata observed before its close.
3. Does the implementation reproduce last-trade carry-forward, clipping, volatility, zero-volatility handling, activity/terminal eligibility and strictly earlier feature clocks? Inspect source code and frozen manifests; do not rerun consumed evaluators or reconstruct B1 on holdout.
4. Are the holdout receipt-order deviation, original exposed v1 test and opened reporting folds appropriately described wherever material? Does any wording inadvertently suggest full untouched-data confirmation?
5. Are nonlinear-baseline gains and exposure correction adequately scoped to different cohorts and selection histories? Does the paper overinterpret context as a causal explanation?
6. Are dependence, adaptive selection and future-text fitting limitations strong enough? Existing descriptive intervals are not broad population or useful-effect exclusion guarantees.
7. Does the paper offer a distinct methodological/empirical contribution relative to news/price controls, information-absorption studies and article-contract grounding? The accessible preprints are not independent replications of EventX.
8. Is the narrative publishable at an appropriate empirical forecasting venue? What additional evidence is necessary, optional or beyond the current paper's scope?

Return a new copy of `review_response_blank.json`. Identify reviewer role, relationship to the project, prior exposure and conflicts. Distinguish fatal validity concerns, necessary revisions and optional extensions. Reference exact sections/artifacts. Review status remains pending until a real response is received; no automatic approval is assumed.

## Submission dependencies

Authors, affiliations, contributions, funding/conflict statements and target venue remain user-supplied. Source-release rights and repository-code licensing remain unresolved; see [release policy](RELEASE_POLICY.md). V4 prospective results can be added only through the frozen post-close gates, and source failure can leave confirmation incomplete. Reviewer feedback must not drive a change to the frozen V4 protocol or tuning on its outcome.
