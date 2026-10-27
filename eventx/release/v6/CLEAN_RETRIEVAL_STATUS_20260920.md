# Cleaned end-to-end development retrieval

Same 500 opened development articles and 4,651 contract cards. Previous artifacts
verified and preserved; no reserved labels or holdout outcomes accessed.

| Stage | Previous | Cleaned |
|---|---:|---:|
| Subject-retrieved pairs | 1,759 | 1,648 |
| Context-retained pairs | 1,071 | 969 |
| Event-channel pairs | 138 | 11 |
| Articles with channel candidates | 6 | 2 |

Three articles contain masked sidebar tails. The 11 surviving pairs exactly match
the previous fixed-pair filtering result: no added or removed survivors.
Eight are after recorded close; three have unresolved periods. Zero admissions.
Heuristic roles: three reported observations, eight prospective/modal claims.

Remaining evidence inspected:

- Gold-price headline: three contracts after recorded close. Sentence extraction
  truncates the abbreviation U.S.; no settlement measurement is established.
- SpaceX commentary: five Musk net-worth contracts after recorded close and three
  SpaceX IPO contracts with unresolved periods. Company valuation and personal net
  worth are not interchangeable predicates; IPO observation identity remains missing.

These are assistant development diagnostics, not independent relevance judgments.
Low yield cannot distinguish poor news/market overlap from missed links without
additional coverage analysis. It does not establish absence of predictive news signal.

New runner: `eventx/tasks/check_clean_retrieval.py`. Evidence and pre-run code hashes:
`data/v6/clean_retrieval_20260920/`. Four output hashes verified; 59 targeted tests pass.
Neural ranking was not rerun: there is no rank-based acceptance rule in this check.

Next: inventory temporal overlap and subject-extraction coverage in the existing
cohort, separating source coverage from retrieval failures. Do not start another
annotation round or predictive model fit on these candidates.
