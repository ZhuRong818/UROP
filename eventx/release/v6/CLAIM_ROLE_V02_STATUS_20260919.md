# Attribution versus claim role — development correction

Implemented a separately versioned classifier on the fixed138 candidate pairs from
six articles. Attribution (said/says/reported) is now a separate flag, not itself an
opinion label. No original classifier or published artifact changed.

| Revised diagnostic role | Pairs | Unique evidence spans |
|---|---:|---:|
| Prospective/modal claim | 48 | 2 |
| Contaminated summary context | 39 | 1 |
| Unresolved | 39 | 1 |
| Reported action/observation | 12 | 2 |

One summary embeds a “Most Read from Bloomberg” list of unrelated headlines. Its
39 links are not trustworthy evidence from the article's main story. The earlier
same-sentence test did not protect against this concatenated sidebar content.

The two observation spans concern reported iPhone supply constraints and a gold-price
move. Reported observation does not verify truth, identify the contract's speaker or
occasion, or establish correct period. Twelve pair classifications are not twelve
independent observations; zero links admitted. Modal/future claims remain distinct
from factual observations. Mixed propositions and unrecognized wording abstain.

Ten new synthetic tests cover attributed/unattributed observations, future/modal
claims, opinions, sidebar contamination and no-admission behavior; all27 tests in
the targeted role/period/relation suite pass. Examples informed development; no
independent accuracy estimate or new human annotations. Existing period checks and
source certification remain unchanged.

Next fix relation-level speaker/occasion binding and exclude contaminated evidence
before ranking. Do not expand the candidate count or train prediction models yet.

Evidence:`data/v6/claim_role_v02_20260919/`; code:
`eventx/v6/claim_role_v02.py`; runner:`eventx/tasks/check_claim_role_v02.py`.
