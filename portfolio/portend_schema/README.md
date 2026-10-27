# PORTEND database schema

This package implements the PORTEND storage decision:

- immutable compressed source archives are evidence;
- versioned Parquet releases are canonical research data;
- `portend.duckdb` is a rebuildable catalog and analytics layer;
- published datasets are selected by explicit manifests, never by an implicit
  "latest" directory or an unpinned wildcard.

It does not use, modify, or attach Freqtrade's `tradesv3.sqlite`.

## Files

| File | Purpose |
|---|---|
| `schema.sql` | DuckDB schemas, native catalog tables, canonical contracts and empty public views |
| `build_catalog.py` | Builds/rebuilds a catalog and replaces public views with manifest-pinned Parquet views |
| `dataset_manifest.schema.json` | JSON Schema for an atomic published Parquet release |
| `raw_batch_manifest.schema.json` | JSON Schema for an immutable raw archive batch |
| `smoke_test.py` | Creates a temporary release and verifies schema creation, manifest registration and Parquet querying |

## Database layers

`meta` contains the only native DuckDB state:

- source-run and raw-batch registrations;
- dataset releases and files;
- dependency hashes and active-release pointers;
- catalog build receipts and schema versions.

This state is a queryable cache of file manifests and is rebuildable.

`contract` contains empty tables defining the canonical columns, types, primary
keys and row-level checks. Canonical records are not stored in these tables.

The public schemas contain views over the selected Parquet releases:

| Schema | Contents |
|---|---|
| `core` | markets, outcomes, fees, trading rules and settlements |
| `market_data` | prices, trades, L2 updates and reconstructed L2 snapshots |
| `semantics` | event families, memberships, typed relations, audits and sparse constraints |
| `benchmark` | decision times, beliefs, joint distributions, samples, episodes, splits, scenarios and oracle variants |
| `simulation` | experiment runs, fills, portfolio states and normalized positions, results and simulator validation |
| `qa` | replay faults, book-validity intervals, completeness, schema and relation checks, and statistics |

## Important modeling decisions

### Identifiers

External IDs use `VARCHAR`, not integers. Polymarket condition and token IDs may
exceed ordinary integer ranges or use hexadecimal representations. Internally
generated IDs may be UUID strings.

Market and outcome metadata use version-row IDs as primary keys while retaining
stable `market_id`, `condition_id`, `event_id`, `event_family_id` and `token_id`
columns. This allows multiple non-overlapping semantic versions.

### Time

All instants use `TIMESTAMPTZ` and must be written in UTC. The schema preserves
event/exchange, receive, ingestion, availability, block, validity, terminal and
resolution time separately.

All validity intervals are half-open:

```text
[valid_from, valid_until)
```

A null `valid_until` means the version remains open. Point-in-time joins must use:

```sql
fact_time >= valid_from
AND (valid_until IS NULL OR fact_time < valid_until)
AND availability_ts <= decision_ts
```

### Numeric values

Prices, quantities, fees and collateral use `DECIMAL(38, 18)` to prevent binary
floating-point drift in execution and accounting. Model probabilities and summary
statistics use `DOUBLE` where floating-point computation is intentional.

### L2 replay

`market_data.orderbook_updates` stores one normalized update row per message element.
The deterministic logical ordering is:

```text
venue, token_id, exchange_ts, sequence_number,
received_ts, intra_message_index
```

Sequence semantics may be venue- or connection-specific. Replay code must not invent
a global sequence. Null or discontinuous sequences, reconnects, resets, duplicate
messages, out-of-order arrivals and checksum failures are recorded in
`qa.replay_events`. Only intervals marked `valid` in `qa.book_validity` may count as
replayable.

`market_data.orderbook_snapshots` is long-form: one row per side and price level.
Snapshots are derived and retain hashes of their first and last source messages.
They never replace raw updates.

### Relations and constraints

Relations retain the requested `participating_market_ids` list. A normalized
`relation_participants` table supports graph processing and ordered roles.

Constraints use a sparse representation:

- `semantics.constraints` stores the row sense and right-hand side;
- `semantics.constraint_terms` stores token/coefficient pairs.

Together these encode rows of `A_t y = b_t` and `C_t y <= d_t` without embedding
opaque matrices in JSON.

### Beliefs

`benchmark.beliefs` stores decision-time marginal probabilities. Joint distributions
have separate metadata, ordered membership and long-form samples. For exact finite
support, `sample_index` identifies a settlement vector and `sample_weight` is its
probability mass. For Monte Carlo beliefs, it identifies a deterministic seeded draw.

### Parquet constraints

Parquet does not enforce primary keys, `CHECK` clauses or non-overlapping validity
intervals. The `contract` definitions document those invariants, but release QA must
enforce them before `qa_status=pass`. A catalog build verifies:

- the manifest is published and passed QA;
- every file exists beneath the declared data root;
- file sizes and SHA-256 hashes match;
- per-file row totals match the release total;
- all canonical columns are present and their declared types are cast-compatible;
- an existing dataset version never resolves to a different manifest hash.

Duplicate IDs, temporal overlap, point-in-time leakage and domain rules still require
dataset-specific QA queries before publication.

## Partitioning

Use these physical layouts:

```text
warehouse/market_data/prices/venue=<venue>/date=<YYYY-MM-DD>/
warehouse/market_data/trades/venue=<venue>/date=<YYYY-MM-DD>/
warehouse/market_data/orderbook_updates/venue=<venue>/date=<YYYY-MM-DD>/hour=<HH>/
warehouse/market_data/orderbook_snapshots/venue=<venue>/date=<YYYY-MM-DD>/hour=<HH>/
warehouse/simulation/results/experiment_id=<id>/run_id=<id>/
```

The `venue`, `date` and optional `hour` columns are exposed from Hive partition paths.
Use daily rather than hourly L2 partitions when an hourly partition would be small.
Never partition by `token_id`. Compact files before publishing a release.

Within update files, sort by token and deterministic replay order. For reconstructed
decision-time snapshots, benchmark whether `decision_ts, event_family_id, token_id`
is faster than token-first ordering before freezing the release writer.

## Building a catalog

Install the optional dependencies:

```bash
python -m pip install -e '.[portend]'
```

Bootstrap an empty catalog containing all contracts:

```bash
python portfolio/portend_schema/build_catalog.py \
  --database portend_data/portend.duckdb \
  --data-root portend_data
```

Register explicit releases:

```bash
python portfolio/portend_schema/build_catalog.py \
  --database portend_data/portend.duckdb \
  --data-root portend_data \
  --manifest portend_data/manifests/dataset=core.markets/version=2026-09-06/manifest.json \
  --manifest portend_data/manifests/dataset=market_data.prices/version=2026-09-06/manifest.json
```

Every rebuild must provide the complete intended manifest set. There is deliberately
no automatic latest-version discovery because that would make experiments change as
new files arrive.

Run the executable check with:

```bash
python portfolio/portend_schema/smoke_test.py
```

## Scope boundary

This schema enables reproducible ingestion, point-in-time reconstruction, curation
and experiments. It cannot create historical L2 that was never recorded. PORTEND's
first empirical gate remains proving that valid order books can be reconstructed at
enough historical decision timestamps and that simulated taker fills agree with
observed aggressive trades.
