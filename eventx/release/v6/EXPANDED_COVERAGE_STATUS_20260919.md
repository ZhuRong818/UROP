# Fixed broader coverage and targeted cached metadata recovery

## Broader development check completed

Selected500 additional articles by deterministic SHA256 article-ID ordering from
the existing opened May17–July22 source inventory. Excluded the original200 article
IDs/content hashes and reserved100 article IDs/content hashes. Reservation identifiers
were projected only for exclusion; no review labels were used. Story-level similarity
exclusion was not established, so this remains development, not confirmation.
Selection receipt and all linking-code hashes were saved before matching and verified
unchanged afterward. Every selected source article ID/content hash matched its receipt.

Unchanged subject retrieval/context/relation/claim-period gates produced:

| Output | Count |
|---|---:|
| Articles | 500 |
| Subject retrieval pairs | 1,759 |
| Context-retained pairs | 1,071 |
| Event-channel pairs / distinct articles | 138 / 6 |
| Opinion/assessment pairs | 127 |
| Measurement claims with unverified period | 3 |
| Unresolved claim roles | 8 |
| Before question deadline / after recorded close / unresolved period | 118 / 17 / 3 |
| Before-deadline event-update articles | 0 |
| Predictive admissions | 0 |

Neural reranking was not repeated: cached architecture has no neural acceptance
threshold and ordering cannot change this gate-yield count. This is not a second
three-algorithm accuracy comparison. The6/500 (1.2%) is candidate article yield,
not recall or useful-signal prevalence. Broad opinion cues can classify factual
attributed reports as assessments; zero update yield is not a news-null finding.

## Targeted metadata recovery completed within existing caches

Followed exact original source-file/line pointers for the prior15 candidate contracts.
Recovered15/15 records with15/15 condition-ID matches. All contain question, source-run
ID, ingestion timestamp and start date;14 contain an end date. The projected records
provide no nonempty rules, version-validity intervals or historical trading-state
timeline. No certificate was created. Outcome fields were excluded from outputs.

This inspected the referenced snapshots, not every possible cache or live Lumid table.
It does not establish that the evidence is unavailable at the provider. Live recovery
remains unfinished: needed evidence is the exact historical contract-text version,
its availability/validity interval, and status/open-close history with lineage. A
current snapshot or market start date is not a substitute. News-content assurance
remains provisionally accepted and is not revoked by this metadata result.

## Decision

The fixed pipeline's current yield is inadequate; do not tune a probability model or
interpret repeated contract variants as independent news. Next algorithm work should
test claim-role errors (especially attribution versus opinion) and sparse contract/news
universe overlap, with a fixed diagnostic contract. Separately recover provider-level
historical metadata evidence. No new bulk review packet is justified by these results.

Artifacts: `data/v6/expanded_coverage_20260919/` and
`data/v6/candidate_metadata_cache_20260919/`. Both runs finished. No live fetch,
predictive outcome access, reviewer annotations or training occurred.
