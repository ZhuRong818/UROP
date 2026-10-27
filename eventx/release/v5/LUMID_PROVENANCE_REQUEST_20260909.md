# Lumid request: EventX V5 historical provenance and projected recovery

Prepared 9 September 2026. **Draft only—not sent. No credentials included.**

We are validating point-in-time prediction-market/news inputs for
`[2026-05-17, 2026-07-22)` UTC. Please help with the following bounded recovery.

## 1. Restore the projected retrieval path

Authenticated catalog GETs return HTTP 200, but `POST /findata/retrieve` returned
HTTP 500 on 8 September for a schema query and on 9 September at approximately
08:44:09 UTC for this minimal request:

```json
{"sql":"SELECT 1 AS read_only_probe","output_format":"jsonl"}
```

Please restore this path or provide an equivalent projected, read-only export
workflow. We need to exclude prices, outcomes and settlement fields.

## 2. Polymarket event membership

Our local review queue contains 819 condition IDs and their cached market IDs.
We prepared 17 event-link batches and 17 metadata batches. Please confirm whether
`prediction_markets.polymarket_events.market_ids` contains scalar market IDs,
condition IDs or objects, and provide:

- condition ID, market ID, event ID and event title;
- membership observation/availability and version timestamps;
- source, source endpoint and ingestion run ID;
- counts sufficient to reconcile zero matches and multiple memberships.

We will separately audit semantic dependencies; venue event IDs alone are not an
assertion of independent experimental families.

## 3. Historical metadata and article versions

Can archived raw payloads or versioned records establish the exact metadata/article
content at a historical time? In particular:

- What do `ingest_ts` and `source_run_id` mean after an upsert or correction?
- Are original content versions retained, and how are they retrieved?
- Are historical market-status transitions and scheduled-terminal revisions retained?
- Can exact headline/summary versions be linked to their original availability?
- If a table is immutable for these fields, what lineage or documented guarantee
  substantiates that property?

We do not assume that a download-time checksum proves historical byte availability.

## 4. Failed/partial run reconciliation

Our discovery news links to 4,088 runs. Of 148,543 discovery articles, 94,990 link to
partial/failed/aborted runs. We recovered a priority sample of 20 runs covering 10,555
articles: 12 have missing insert/update counters and four have fewer reported writes
than locally referenced articles.

Examples:

- `592ebc42-79ad-4b33-af2d-628b5edb6167`: failed, abandoned-run cleanup, null counters.
- `7da728da-fd83-4576-8402-0df14ab9252a`: partial, zero insert/update counters, while
  1,750 discovery article rows reference this run.

Please explain counter/status semantics and provide intended windows/symbol coverage,
committed-row evidence, failed pages/symbols, retry relationships and recovery receipts.
We are not treating these statuses alone as proof that individual articles are invalid.
