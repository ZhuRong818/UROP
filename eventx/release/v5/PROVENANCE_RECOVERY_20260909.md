# V5 targeted provenance recovery — 9 September 2026

**Outcome: partial recovery succeeded; dataset admission and experiment freeze remain blocked.**

## What was done

1. Reached authenticated Lumid catalog routes and recovered schemas for Polymarket
   events/markets, news articles/article sources and ingestion runs.
2. Confirmed a schema-supported mapping route: `polymarket_events.market_ids` can
   potentially link cached Polymarket market IDs to venue event IDs. Actual membership
   values and JSON element types still require a projected data query.
3. Recovered 20/20 priority historical news-run lineage records through
   `/catalog/lineage/run/{run_id}`. These are the largest eight discovery-article runs
   in each failed/partial/aborted category, or all runs when fewer than eight exist.
4. Prepared an exact-ID recovery package for all 819 missing Polymarket conditions:
   17 event-link batches and 17 projected metadata batches, at most 50 target markets
   per batch. No condition/token/market ID substitution is used.
5. Tested query projection, identifier separation and SQL literal escaping; three
   new synthetic checks passed. No research model was trained or holdout consumed.

Final regression check: 32/32 tests passed. Verified 77 artifact hashes, including
all 15 frozen V4 implementation artifacts; zero mismatches.

## Results and limitations

| Check | Result |
|---|---|
| Warehouse retrieval on 8 September | Schema inventory request returned HTTP 500 |
| Warehouse retrieval on 9 September | `SELECT 1 AS read_only_probe` returned HTTP 500 |
| Historical lineage retrieval | 20/20 priority requests returned HTTP 200 |
| Discovery articles linked to those runs | 10,555 |
| Selected runs missing insert/update counters | 12 |
| Selected runs with local article count above reported inserts + updates | 4 |
| Source intervals fully reconciled by this work | 0 |
| Polymarket event mappings actually recovered | 0; queries prepared but not executed |
| Rebuilt admissible examples / real model fits | 0 / 0 |

The source-only news archive links to 4,088 distinct ingestion runs: 1,585 `ok`,
189 `completed`, 318 `partial`, 1,992 `failed`, and four `aborted`. The 20-run recovery
is a priority sample, not a random sample or a full audit of all affected runs.

For example, one failed run is marked `auto-cleanup: abandoned >2h`, with null write
counters. A partial run reports zero inserted/updated rows while 1,750 staged articles
reference it. This may reflect bookkeeping semantics, updates, or partial commits;
it does not prove article corruption. We need committed-row and retry coverage evidence
before interpreting these counters as completeness.

The catalog exposes current `active`/`closed` fields and source/run ingestion fields,
but does not by itself establish historical validity intervals or exact content-version
availability. The inspected natural keys are event ID/source, market ID/source,
article URL/publication time, and article-source URL/source—not explicit version IDs.
Metadata catalog runs also report updates. Therefore an immutable-history guarantee
cannot be inferred merely from table existence or a source ingest timestamp.

No dedicated version-history table appeared in the three inspected schema listings.
This is not proof that the provider has no archive elsewhere. Raw archive/version
evidence remains a provider question, especially while projected warehouse queries fail.

## Why the remaining steps were not forced through

The user's requested sequence requires source evidence before admitting examples.
The functioning catalog proves that relevant structures exist; it does not return
the missing historical mappings or prove data completeness. The required warehouse
route fails even for a constant query. Repeatedly sending all 34 recovery queries
would not resolve that route-level failure.

Generic market/detail/event calls can return unprojected current prices or outcomes.
They were not used as a substitute for the outcome-blind projected recovery queries.
V4 and consumed holdouts remain untouched. No source constraint, feature definition,
family approval or confirmation date was silently changed.

## Artifacts

- `data/v5/provenance_recovery_20260908/`: append-only request receipts and catalog
  evidence from 8–9 September, including failed network attempts and HTTP 500 checks.
- `data/v5/lineage_recovery_20260909/`: pre-request selection plan, 20 projected
  lineage records, report and hash manifest. Credentials and arbitrary error text
  are excluded from the batch projections.
- `data/v5/recovery_requests_20260909/`: 819 condition-to-cached-market targets,
  34 SQL files, request manifest and hashes. Queries remain unexecuted and must pass
  the documented scalar-membership and count/censoring checks before bulk use.
- `eventx/release/v5/LUMID_PROVENANCE_REQUEST_20260909.md`: provider-ready request,
  prepared locally only; not sent externally.

## Next execution order

1. Restore `/retrieve` or obtain an approved outcome-blind projected warehouse export
   from Lumid using the same target lists. Validate a small query before full batches.
2. Recover event mappings, reconcile missing/ambiguous memberships and review semantic
   family dependencies across venue events/venues. Do not automatically approve IDs.
3. Establish archived metadata/content availability and reconcile failed-run committed
   rows, target windows and retries. Keep unproven intervals explicitly incomplete.
4. Rebuild a new as-of dataset only when admission gates pass. Finalize the matched
   timing/content control, semantic warm-up and fold specification, then freeze the
   new research version before an independent test.

The remaining block needs source access/evidence, not additional model tuning.
Historical data remain an option if the missing proof can be recovered; nothing in
this recovery requires waiting for new calendar dates merely to inspect old sources.
