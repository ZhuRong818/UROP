-- PORTEND DuckDB catalog and canonical Parquet contracts.
--
-- The contract.* tables are empty schema templates. Canonical rows live in
-- versioned Parquet releases. Public views initially expose the empty contracts
-- and are replaced with manifest-pinned read_parquet views by build_catalog.py.

BEGIN TRANSACTION;

CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS contract;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS market_data;
CREATE SCHEMA IF NOT EXISTS semantics;
CREATE SCHEMA IF NOT EXISTS benchmark;
CREATE SCHEMA IF NOT EXISTS simulation;
CREATE SCHEMA IF NOT EXISTS qa;

-- Rebuildable catalog metadata -------------------------------------------------

CREATE TABLE IF NOT EXISTS meta.schema_versions (
    schema_version VARCHAR PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    code_commit VARCHAR,
    description VARCHAR NOT NULL
);

INSERT INTO meta.schema_versions (schema_version, description)
SELECT '1.0.0', 'Initial PORTEND Parquet-contract and DuckDB catalog schema'
WHERE NOT EXISTS (
    SELECT 1 FROM meta.schema_versions WHERE schema_version = '1.0.0'
);

CREATE TABLE IF NOT EXISTS meta.source_runs (
    source_run_id VARCHAR PRIMARY KEY,
    source VARCHAR NOT NULL,
    stream VARCHAR NOT NULL,
    collector_code_commit VARCHAR NOT NULL,
    collector_config_hash VARCHAR NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status VARCHAR NOT NULL CHECK (status IN ('running', 'complete', 'failed', 'aborted')),
    request_or_connection_id VARCHAR,
    host VARCHAR,
    error_summary VARCHAR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    CHECK (completed_at IS NULL OR completed_at >= started_at)
);

CREATE TABLE IF NOT EXISTS meta.raw_batches (
    raw_batch_id VARCHAR PRIMARY KEY,
    source_run_id VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    stream VARCHAR NOT NULL,
    relative_path VARCHAR NOT NULL UNIQUE,
    compression VARCHAR NOT NULL DEFAULT 'zstd',
    content_sha256 VARCHAR NOT NULL,
    byte_count UBIGINT NOT NULL,
    record_count UBIGINT NOT NULL,
    min_event_ts TIMESTAMPTZ,
    max_event_ts TIMESTAMPTZ,
    min_received_ts TIMESTAMPTZ,
    max_received_ts TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL,
    schema_version VARCHAR NOT NULL,
    manifest_relative_path VARCHAR NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
    CHECK (max_event_ts IS NULL OR min_event_ts IS NULL OR max_event_ts >= min_event_ts),
    CHECK (max_received_ts IS NULL OR min_received_ts IS NULL OR max_received_ts >= min_received_ts)
);

CREATE TABLE IF NOT EXISTS meta.dataset_releases (
    dataset_name VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    status VARCHAR NOT NULL CHECK (status IN ('staging', 'validated', 'published', 'superseded', 'failed')),
    manifest_relative_path VARCHAR NOT NULL UNIQUE,
    manifest_sha256 VARCHAR NOT NULL,
    row_count UBIGINT NOT NULL,
    min_timestamp TIMESTAMPTZ,
    max_timestamp TIMESTAMPTZ,
    code_commit VARCHAR NOT NULL,
    config_hash VARCHAR NOT NULL,
    qa_status VARCHAR NOT NULL CHECK (qa_status IN ('pending', 'pass', 'fail', 'waived')),
    created_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ,
    PRIMARY KEY (dataset_name, dataset_version),
    CHECK (max_timestamp IS NULL OR min_timestamp IS NULL OR max_timestamp >= min_timestamp),
    CHECK (published_at IS NULL OR published_at >= created_at)
);

CREATE TABLE IF NOT EXISTS meta.dataset_files (
    dataset_name VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    relative_path VARCHAR NOT NULL,
    file_sha256 VARCHAR NOT NULL,
    byte_count UBIGINT NOT NULL,
    row_count UBIGINT NOT NULL,
    row_group_count UINTEGER,
    min_timestamp TIMESTAMPTZ,
    max_timestamp TIMESTAMPTZ,
    partition_values JSON,
    PRIMARY KEY (dataset_name, dataset_version, relative_path)
);

CREATE TABLE IF NOT EXISTS meta.dataset_dependencies (
    dataset_name VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    upstream_dataset_name VARCHAR NOT NULL,
    upstream_dataset_version VARCHAR NOT NULL,
    upstream_manifest_sha256 VARCHAR NOT NULL,
    PRIMARY KEY (
        dataset_name,
        dataset_version,
        upstream_dataset_name,
        upstream_dataset_version
    )
);

CREATE TABLE IF NOT EXISTS meta.dataset_source_runs (
    dataset_name VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    source_run_id VARCHAR NOT NULL,
    PRIMARY KEY (dataset_name, dataset_version, source_run_id)
);

CREATE TABLE IF NOT EXISTS meta.active_releases (
    dataset_name VARCHAR PRIMARY KEY,
    dataset_version VARCHAR NOT NULL,
    manifest_sha256 VARCHAR NOT NULL,
    activated_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS meta.catalog_builds (
    catalog_build_id VARCHAR PRIMARY KEY,
    database_path VARCHAR NOT NULL,
    manifest_set_sha256 VARCHAR NOT NULL,
    code_commit VARCHAR,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status VARCHAR NOT NULL CHECK (status IN ('running', 'complete', 'failed')),
    error_summary VARCHAR
);

-- Canonical core-data contracts ------------------------------------------------

CREATE TABLE IF NOT EXISTS contract.markets (
    market_version_id VARCHAR PRIMARY KEY,
    venue VARCHAR NOT NULL,
    market_id VARCHAR NOT NULL,
    condition_id VARCHAR,
    event_id VARCHAR,
    question VARCHAR NOT NULL,
    description VARCHAR,
    category VARCHAR,
    market_status VARCHAR NOT NULL,
    created_ts TIMESTAMPTZ,
    opened_ts TIMESTAMPTZ,
    scheduled_terminal_ts TIMESTAMPTZ,
    closed_ts TIMESTAMPTZ,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    availability_ts TIMESTAMPTZ NOT NULL,
    source_run_id VARCHAR NOT NULL,
    raw_payload_hash VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    CHECK (valid_until IS NULL OR valid_until > valid_from)
);

CREATE TABLE IF NOT EXISTS contract.outcomes (
    outcome_version_id VARCHAR PRIMARY KEY,
    venue VARCHAR NOT NULL,
    token_id VARCHAR NOT NULL,
    market_id VARCHAR NOT NULL,
    condition_id VARCHAR,
    outcome_name VARCHAR NOT NULL,
    outcome_index INTEGER,
    is_other BOOLEAN NOT NULL DEFAULT false,
    semantics_stable BOOLEAN,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    availability_ts TIMESTAMPTZ NOT NULL,
    source_run_id VARCHAR NOT NULL,
    raw_payload_hash VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    CHECK (valid_until IS NULL OR valid_until > valid_from)
);

CREATE TABLE IF NOT EXISTS contract.fees (
    fee_version_id VARCHAR PRIMARY KEY,
    venue VARCHAR NOT NULL,
    market_id VARCHAR,
    token_id VARCHAR,
    maker_fee_rate DECIMAL(38, 18),
    taker_fee_rate DECIMAL(38, 18),
    fee_formula VARCHAR,
    fee_currency VARCHAR,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    availability_ts TIMESTAMPTZ NOT NULL,
    provenance VARCHAR NOT NULL,
    source_run_id VARCHAR,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    CHECK (valid_until IS NULL OR valid_until > valid_from)
);

CREATE TABLE IF NOT EXISTS contract.trading_rules (
    trading_rule_version_id VARCHAR PRIMARY KEY,
    venue VARCHAR NOT NULL,
    market_id VARCHAR,
    token_id VARCHAR,
    tick_size DECIMAL(38, 18) NOT NULL,
    minimum_order_size DECIMAL(38, 18),
    minimum_notional DECIMAL(38, 18),
    collateral_currency VARCHAR,
    collateral_rule VARCHAR,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    availability_ts TIMESTAMPTZ NOT NULL,
    provenance VARCHAR NOT NULL,
    source_run_id VARCHAR,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    CHECK (tick_size > 0),
    CHECK (valid_until IS NULL OR valid_until > valid_from)
);

CREATE TABLE IF NOT EXISTS contract.settlements (
    settlement_id VARCHAR PRIMARY KEY,
    venue VARCHAR NOT NULL,
    market_id VARCHAR NOT NULL,
    condition_id VARCHAR,
    token_id VARCHAR NOT NULL,
    settlement_value DECIMAL(38, 18) NOT NULL,
    winning_outcome BOOLEAN NOT NULL,
    resolution_ts TIMESTAMPTZ NOT NULL,
    availability_ts TIMESTAMPTZ NOT NULL,
    oracle VARCHAR,
    transaction_hash VARCHAR,
    block_number UBIGINT,
    source_run_id VARCHAR NOT NULL,
    raw_payload_hash VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    CHECK (settlement_value >= 0 AND settlement_value <= 1),
    CHECK (availability_ts >= resolution_ts)
);

-- Canonical market-data contracts ---------------------------------------------

CREATE TABLE IF NOT EXISTS contract.prices (
    price_id VARCHAR PRIMARY KEY,
    venue VARCHAR NOT NULL,
    date DATE NOT NULL,
    token_id VARCHAR NOT NULL,
    market_id VARCHAR NOT NULL,
    exchange_ts TIMESTAMPTZ NOT NULL,
    received_ts TIMESTAMPTZ,
    ingest_ts TIMESTAMPTZ NOT NULL,
    availability_ts TIMESTAMPTZ NOT NULL,
    price_type VARCHAR NOT NULL CHECK (price_type IN ('last_trade', 'bid', 'ask', 'mid', 'mark', 'settlement')),
    price DECIMAL(38, 18) NOT NULL,
    source_run_id VARCHAR NOT NULL,
    raw_payload_hash VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    CHECK (price >= 0 AND price <= 1)
);

CREATE TABLE IF NOT EXISTS contract.trades (
    venue VARCHAR NOT NULL,
    date DATE NOT NULL,
    trade_id VARCHAR NOT NULL,
    token_id VARCHAR NOT NULL,
    market_id VARCHAR NOT NULL,
    condition_id VARCHAR,
    exchange_ts TIMESTAMPTZ NOT NULL,
    received_ts TIMESTAMPTZ,
    ingest_ts TIMESTAMPTZ NOT NULL,
    availability_ts TIMESTAMPTZ NOT NULL,
    price DECIMAL(38, 18) NOT NULL,
    size DECIMAL(38, 18) NOT NULL,
    side VARCHAR,
    aggressor_side VARCHAR,
    fee DECIMAL(38, 18),
    fee_currency VARCHAR,
    transaction_hash VARCHAR,
    block_number UBIGINT,
    source_run_id VARCHAR NOT NULL,
    raw_payload_hash VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (venue, trade_id),
    CHECK (price >= 0 AND price <= 1),
    CHECK (size > 0)
);

CREATE TABLE IF NOT EXISTS contract.orderbook_updates (
    venue VARCHAR NOT NULL,
    date DATE NOT NULL,
    hour UTINYINT,
    token_id VARCHAR NOT NULL,
    market_id VARCHAR NOT NULL,
    exchange_ts TIMESTAMPTZ NOT NULL,
    received_ts TIMESTAMPTZ NOT NULL,
    ingest_ts TIMESTAMPTZ NOT NULL,
    availability_ts TIMESTAMPTZ NOT NULL,
    sequence_number UBIGINT,
    connection_id VARCHAR NOT NULL,
    message_type VARCHAR NOT NULL,
    side VARCHAR,
    price DECIMAL(38, 18),
    quantity DECIMAL(38, 18),
    level INTEGER,
    snapshot_or_delta VARCHAR NOT NULL CHECK (snapshot_or_delta IN ('snapshot', 'delta')),
    intra_message_index UINTEGER NOT NULL DEFAULT 0,
    checksum VARCHAR,
    source_run_id VARCHAR NOT NULL,
    raw_payload_hash VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (
        venue,
        token_id,
        connection_id,
        received_ts,
        intra_message_index,
        raw_payload_hash
    ),
    CHECK (price IS NULL OR (price >= 0 AND price <= 1)),
    CHECK (quantity IS NULL OR quantity >= 0),
    CHECK (hour IS NULL OR hour <= 23)
);

-- Long-form snapshot: one row per book level.
CREATE TABLE IF NOT EXISTS contract.orderbook_snapshots (
    snapshot_id VARCHAR NOT NULL,
    venue VARCHAR NOT NULL,
    date DATE NOT NULL,
    hour UTINYINT,
    token_id VARCHAR NOT NULL,
    market_id VARCHAR NOT NULL,
    snapshot_ts TIMESTAMPTZ NOT NULL,
    availability_ts TIMESTAMPTZ NOT NULL,
    side VARCHAR NOT NULL CHECK (side IN ('bid', 'ask')),
    price DECIMAL(38, 18) NOT NULL,
    quantity DECIMAL(38, 18) NOT NULL,
    level INTEGER NOT NULL,
    valid_book BOOLEAN NOT NULL,
    first_source_message_hash VARCHAR NOT NULL,
    last_source_message_hash VARCHAR NOT NULL,
    source_run_id VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (snapshot_id, side, level),
    CHECK (price >= 0 AND price <= 1),
    CHECK (quantity >= 0),
    CHECK (level >= 0),
    CHECK (hour IS NULL OR hour <= 23)
);

-- Semantic-curation contracts -------------------------------------------------

CREATE TABLE IF NOT EXISTS contract.event_families (
    event_family_version_id VARCHAR PRIMARY KEY,
    event_family_id VARCHAR NOT NULL,
    family_type VARCHAR NOT NULL,
    description VARCHAR NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    availability_ts TIMESTAMPTZ NOT NULL,
    provenance VARCHAR NOT NULL,
    verification_status VARCHAR NOT NULL CHECK (verification_status IN ('candidate', 'verified', 'rejected', 'ambiguous')),
    curator_id VARCHAR,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    CHECK (valid_until IS NULL OR valid_until > valid_from)
);

CREATE TABLE IF NOT EXISTS contract.event_family_members (
    membership_version_id VARCHAR PRIMARY KEY,
    event_family_id VARCHAR NOT NULL,
    market_id VARCHAR NOT NULL,
    membership_role VARCHAR,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    availability_ts TIMESTAMPTZ NOT NULL,
    provenance VARCHAR NOT NULL,
    verification_status VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    CHECK (valid_until IS NULL OR valid_until > valid_from)
);

CREATE TABLE IF NOT EXISTS contract.relations (
    relation_version_id VARCHAR PRIMARY KEY,
    relation_id VARCHAR NOT NULL,
    event_family_id VARCHAR NOT NULL,
    relation_type VARCHAR NOT NULL CHECK (relation_type IN ('complement', 'exclusive', 'exhaustive', 'monotone', 'implication')),
    participating_market_ids VARCHAR[] NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    availability_ts TIMESTAMPTZ NOT NULL,
    provenance VARCHAR NOT NULL,
    verification_status VARCHAR NOT NULL CHECK (verification_status IN ('candidate', 'verified', 'rejected', 'ambiguous')),
    source_relation_ids VARCHAR[],
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    CHECK (valid_until IS NULL OR valid_until > valid_from)
);

-- Normalized participant rows support graph and constraint queries.
CREATE TABLE IF NOT EXISTS contract.relation_participants (
    relation_version_id VARCHAR NOT NULL,
    participant_index UINTEGER NOT NULL,
    market_id VARCHAR NOT NULL,
    token_id VARCHAR,
    participant_role VARCHAR,
    coefficient DECIMAL(38, 18),
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (relation_version_id, participant_index)
);

CREATE TABLE IF NOT EXISTS contract.relation_audits (
    audit_id VARCHAR PRIMARY KEY,
    relation_version_id VARCHAR NOT NULL,
    relation_type VARCHAR NOT NULL,
    auditor_id VARCHAR NOT NULL,
    audit_label VARCHAR NOT NULL CHECK (audit_label IN ('valid', 'invalid', 'ambiguous')),
    audit_notes VARCHAR,
    audited_at TIMESTAMPTZ NOT NULL,
    evidence_hash VARCHAR,
    audit_protocol_version VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS contract.constraints (
    constraint_version_id VARCHAR PRIMARY KEY,
    constraint_id VARCHAR NOT NULL,
    event_family_id VARCHAR NOT NULL,
    constraint_type VARCHAR NOT NULL CHECK (constraint_type IN ('equality', 'inequality')),
    sense VARCHAR NOT NULL CHECK (sense IN ('=', '<=', '>=')),
    rhs DECIMAL(38, 18) NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    availability_ts TIMESTAMPTZ NOT NULL,
    source_relation_ids VARCHAR[] NOT NULL,
    compiler_version VARCHAR NOT NULL,
    compiler_config_hash VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    CHECK (valid_until IS NULL OR valid_until > valid_from)
);

-- Sparse representation of rows in A_t or C_t.
CREATE TABLE IF NOT EXISTS contract.constraint_terms (
    constraint_version_id VARCHAR NOT NULL,
    term_index UINTEGER NOT NULL,
    token_id VARCHAR NOT NULL,
    coefficient DECIMAL(38, 18) NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (constraint_version_id, term_index)
);

-- Benchmark-construction contracts --------------------------------------------

CREATE TABLE IF NOT EXISTS contract.decision_times (
    decision_time_id VARCHAR PRIMARY KEY,
    decision_ts TIMESTAMPTZ NOT NULL,
    event_family_id VARCHAR,
    scenario_id VARCHAR NOT NULL,
    episode_id VARCHAR NOT NULL,
    eligible_market_ids VARCHAR[] NOT NULL,
    replayable BOOLEAN NOT NULL,
    book_quality_status VARCHAR,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL
);

-- One marginal belief per token and decision time.
CREATE TABLE IF NOT EXISTS contract.beliefs (
    belief_id VARCHAR NOT NULL,
    decision_time_id VARCHAR NOT NULL,
    decision_ts TIMESTAMPTZ NOT NULL,
    oracle_variant_id VARCHAR NOT NULL,
    token_id VARCHAR NOT NULL,
    marginal_probability DOUBLE NOT NULL,
    availability_ts TIMESTAMPTZ NOT NULL,
    model_version VARCHAR NOT NULL,
    training_cutoff_ts TIMESTAMPTZ,
    source_dataset_versions JSON NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (belief_id, token_id),
    CHECK (marginal_probability >= 0 AND marginal_probability <= 1),
    CHECK (availability_ts <= decision_ts),
    CHECK (training_cutoff_ts IS NULL OR training_cutoff_ts <= decision_ts)
);

CREATE TABLE IF NOT EXISTS contract.joint_distributions (
    joint_distribution_id VARCHAR PRIMARY KEY,
    decision_time_id VARCHAR NOT NULL,
    decision_ts TIMESTAMPTZ NOT NULL,
    oracle_variant_id VARCHAR NOT NULL,
    event_family_id VARCHAR,
    construction_method VARCHAR NOT NULL,
    sampling_method VARCHAR,
    sample_count UBIGINT,
    seed UBIGINT,
    feasible_set_hash VARCHAR NOT NULL,
    constraint_manifest_hash VARCHAR NOT NULL,
    code_commit VARCHAR NOT NULL,
    config_hash VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS contract.joint_distribution_members (
    joint_distribution_id VARCHAR NOT NULL,
    member_index UINTEGER NOT NULL,
    token_id VARCHAR NOT NULL,
    marginal_probability DOUBLE NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (joint_distribution_id, member_index),
    CHECK (marginal_probability >= 0 AND marginal_probability <= 1)
);

-- Long-form Monte Carlo support. Exact enumerations can use sample_index as a
-- support-vector index and sample_weight as its probability mass.
CREATE TABLE IF NOT EXISTS contract.joint_samples (
    joint_distribution_id VARCHAR NOT NULL,
    sample_index UBIGINT NOT NULL,
    token_id VARCHAR NOT NULL,
    settlement_value DECIMAL(38, 18) NOT NULL,
    sample_weight DOUBLE,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (joint_distribution_id, sample_index, token_id),
    CHECK (settlement_value >= 0 AND settlement_value <= 1),
    CHECK (sample_weight IS NULL OR sample_weight >= 0)
);

CREATE TABLE IF NOT EXISTS contract.episodes (
    episode_id VARCHAR PRIMARY KEY,
    start_ts TIMESTAMPTZ NOT NULL,
    end_ts TIMESTAMPTZ NOT NULL,
    definition_type VARCHAR NOT NULL,
    definition_version VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    CHECK (end_ts > start_ts)
);

CREATE TABLE IF NOT EXISTS contract.episode_families (
    episode_id VARCHAR NOT NULL,
    event_family_id VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (episode_id, event_family_id)
);

CREATE TABLE IF NOT EXISTS contract.splits (
    split_id VARCHAR PRIMARY KEY,
    split_name VARCHAR NOT NULL,
    split_role VARCHAR NOT NULL CHECK (split_role IN ('train', 'validation', 'test', 'live')),
    split_start_ts TIMESTAMPTZ NOT NULL,
    split_end_ts TIMESTAMPTZ NOT NULL,
    embargo_until TIMESTAMPTZ,
    split_protocol_version VARCHAR NOT NULL,
    frozen_at TIMESTAMPTZ NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    CHECK (split_end_ts > split_start_ts),
    CHECK (embargo_until IS NULL OR embargo_until >= split_end_ts)
);

CREATE TABLE IF NOT EXISTS contract.split_memberships (
    split_id VARCHAR NOT NULL,
    event_family_id VARCHAR NOT NULL,
    market_id VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (split_id, event_family_id, market_id)
);

CREATE TABLE IF NOT EXISTS contract.scenarios (
    scenario_id VARCHAR PRIMARY KEY,
    scenario_name VARCHAR NOT NULL CHECK (scenario_name IN ('term', 'simplex', 'ladder', 'churn', 'open')),
    definition JSON NOT NULL,
    definition_hash VARCHAR NOT NULL,
    frozen_at TIMESTAMPTZ NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS contract.stress_events (
    stress_event_id VARCHAR PRIMARY KEY,
    event_name VARCHAR NOT NULL,
    event_category VARCHAR NOT NULL,
    release_ts TIMESTAMPTZ NOT NULL,
    window_start_ts TIMESTAMPTZ NOT NULL,
    window_end_ts TIMESTAMPTZ NOT NULL,
    source_calendar VARCHAR NOT NULL,
    availability_ts TIMESTAMPTZ NOT NULL,
    source_run_id VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    CHECK (window_start_ts <= release_ts AND release_ts <= window_end_ts),
    CHECK (availability_ts <= release_ts)
);

CREATE TABLE IF NOT EXISTS contract.oracle_variants (
    oracle_variant_id VARCHAR PRIMARY KEY,
    oracle_name VARCHAR NOT NULL,
    oracle_family VARCHAR NOT NULL,
    epsilon DOUBLE,
    model_version VARCHAR,
    training_protocol_hash VARCHAR,
    definition JSON NOT NULL,
    frozen_at TIMESTAMPTZ NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    CHECK (epsilon IS NULL OR epsilon >= 0)
);

-- Simulation and experiment contracts -----------------------------------------

CREATE TABLE IF NOT EXISTS contract.experiment_runs (
    experiment_id VARCHAR NOT NULL,
    run_id VARCHAR NOT NULL,
    allocator VARCHAR NOT NULL,
    allocator_version VARCHAR NOT NULL,
    oracle_variant_id VARCHAR NOT NULL,
    scenario_id VARCHAR NOT NULL,
    bankroll DOUBLE NOT NULL,
    episode_id VARCHAR NOT NULL,
    seed UBIGINT NOT NULL,
    input_manifest_hashes JSON NOT NULL,
    config_hash VARCHAR NOT NULL,
    code_commit VARCHAR NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status VARCHAR NOT NULL CHECK (status IN ('running', 'complete', 'failed', 'invalid')),
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (experiment_id, run_id),
    CHECK (bankroll > 0),
    CHECK (completed_at IS NULL OR completed_at >= started_at)
);

CREATE TABLE IF NOT EXISTS contract.fills (
    experiment_id VARCHAR NOT NULL,
    run_id VARCHAR NOT NULL,
    fill_id VARCHAR NOT NULL,
    order_id VARCHAR NOT NULL,
    decision_time_id VARCHAR NOT NULL,
    decision_ts TIMESTAMPTZ NOT NULL,
    fill_ts TIMESTAMPTZ NOT NULL,
    venue VARCHAR NOT NULL,
    token_id VARCHAR NOT NULL,
    side VARCHAR NOT NULL CHECK (side IN ('buy', 'sell')),
    order_type VARCHAR NOT NULL CHECK (order_type IN ('taker', 'marketable_limit')),
    limit_price DECIMAL(38, 18),
    requested_quantity DECIMAL(38, 18) NOT NULL,
    filled_quantity DECIMAL(38, 18) NOT NULL,
    unfilled_quantity DECIMAL(38, 18) NOT NULL,
    execution_price DECIMAL(38, 18),
    levels_consumed UINTEGER NOT NULL,
    slippage DECIMAL(38, 18),
    fee DECIMAL(38, 18) NOT NULL,
    fee_currency VARCHAR,
    participation_rate DOUBLE,
    pretrade_snapshot_id VARCHAR NOT NULL,
    locked_collateral DECIMAL(38, 18) NOT NULL,
    remaining_cash DECIMAL(38, 18) NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (experiment_id, run_id, fill_id),
    CHECK (requested_quantity > 0),
    CHECK (filled_quantity >= 0),
    CHECK (unfilled_quantity >= 0),
    CHECK (filled_quantity + unfilled_quantity = requested_quantity),
    CHECK (fill_ts >= decision_ts)
);

CREATE TABLE IF NOT EXISTS contract.portfolio_states (
    experiment_id VARCHAR NOT NULL,
    run_id VARCHAR NOT NULL,
    decision_time_id VARCHAR NOT NULL,
    decision_ts TIMESTAMPTZ NOT NULL,
    cash DECIMAL(38, 18) NOT NULL,
    locked_collateral DECIMAL(38, 18) NOT NULL,
    marked_value DECIMAL(38, 18) NOT NULL,
    wealth DECIMAL(38, 18) NOT NULL,
    gross_exposure DECIMAL(38, 18) NOT NULL,
    net_exposure DECIMAL(38, 18) NOT NULL,
    ruined BOOLEAN NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (experiment_id, run_id, decision_time_id)
);

CREATE TABLE IF NOT EXISTS contract.portfolio_positions (
    experiment_id VARCHAR NOT NULL,
    run_id VARCHAR NOT NULL,
    decision_time_id VARCHAR NOT NULL,
    token_id VARCHAR NOT NULL,
    quantity DECIMAL(38, 18) NOT NULL,
    average_cost DECIMAL(38, 18),
    mark_price DECIMAL(38, 18),
    marked_value DECIMAL(38, 18) NOT NULL,
    locked_collateral DECIMAL(38, 18) NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (experiment_id, run_id, decision_time_id, token_id),
    CHECK (mark_price IS NULL OR (mark_price >= 0 AND mark_price <= 1))
);

CREATE TABLE IF NOT EXISTS contract.results (
    experiment_id VARCHAR NOT NULL,
    run_id VARCHAR NOT NULL,
    allocator VARCHAR NOT NULL,
    oracle_variant_id VARCHAR NOT NULL,
    scenario_id VARCHAR NOT NULL,
    bankroll DOUBLE NOT NULL,
    episode_id VARCHAR NOT NULL,
    terminal_wealth DOUBLE NOT NULL,
    log_growth DOUBLE,
    fees DOUBLE NOT NULL,
    turnover DOUBLE NOT NULL,
    slippage DOUBLE NOT NULL,
    max_drawdown DOUBLE,
    capital_efficiency DOUBLE,
    utilization DOUBLE,
    concentration DOUBLE,
    ruin BOOLEAN NOT NULL,
    sleeping_regret DOUBLE,
    input_manifest_hashes JSON NOT NULL,
    config_hash VARCHAR NOT NULL,
    code_commit VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (experiment_id, run_id)
);

CREATE TABLE IF NOT EXISTS contract.simulator_validation (
    validation_id VARCHAR NOT NULL,
    observed_trade_id VARCHAR NOT NULL,
    venue VARCHAR NOT NULL,
    market_id VARCHAR NOT NULL,
    token_id VARCHAR NOT NULL,
    observed_trade_ts TIMESTAMPTZ NOT NULL,
    pretrade_snapshot_id VARCHAR NOT NULL,
    liquidity_bucket VARCHAR,
    order_size_bucket VARCHAR,
    participation_bucket VARCHAR,
    market_category VARCHAR,
    book_quality_status VARCHAR NOT NULL,
    observed_vwap DECIMAL(38, 18),
    simulated_vwap DECIMAL(38, 18),
    vwap_error DECIMAL(38, 18),
    observed_fill_size DECIMAL(38, 18),
    simulated_fill_size DECIMAL(38, 18),
    fill_size_error DECIMAL(38, 18),
    price_level_error DOUBLE,
    fee_error DECIMAL(38, 18),
    simulator_version VARCHAR NOT NULL,
    config_hash VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (validation_id, observed_trade_id)
);

-- QA contracts ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS contract.replay_events (
    replay_event_id VARCHAR PRIMARY KEY,
    venue VARCHAR NOT NULL,
    token_id VARCHAR,
    connection_id VARCHAR,
    event_ts TIMESTAMPTZ NOT NULL,
    event_type VARCHAR NOT NULL CHECK (event_type IN (
        'sequence_gap', 'reconnect', 'reset', 'snapshot_boundary',
        'duplicate', 'out_of_order', 'checksum_failure'
    )),
    expected_sequence UBIGINT,
    observed_sequence UBIGINT,
    details JSON,
    source_run_id VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS contract.book_validity (
    book_validity_id VARCHAR PRIMARY KEY,
    venue VARCHAR NOT NULL,
    token_id VARCHAR NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    validity_status VARCHAR NOT NULL CHECK (validity_status IN ('valid', 'invalid', 'uncertain')),
    invalid_reason VARCHAR,
    start_snapshot_id VARCHAR,
    source_run_ids VARCHAR[] NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    CHECK (valid_until > valid_from)
);

CREATE TABLE IF NOT EXISTS contract.completeness (
    qa_run_id VARCHAR NOT NULL,
    dataset_name VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    partition_key VARCHAR NOT NULL,
    expected_count UBIGINT,
    observed_count UBIGINT NOT NULL,
    missing_count UBIGINT,
    coverage_ratio DOUBLE,
    status VARCHAR NOT NULL CHECK (status IN ('pass', 'fail', 'warning')),
    details JSON,
    checked_at TIMESTAMPTZ NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (qa_run_id, dataset_name, dataset_version, partition_key),
    CHECK (coverage_ratio IS NULL OR (coverage_ratio >= 0 AND coverage_ratio <= 1))
);

CREATE TABLE IF NOT EXISTS contract.schema_checks (
    qa_run_id VARCHAR NOT NULL,
    dataset_name VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    check_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL CHECK (status IN ('pass', 'fail', 'warning')),
    failing_row_count UBIGINT NOT NULL,
    details JSON,
    checked_at TIMESTAMPTZ NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (qa_run_id, dataset_name, dataset_version, check_name)
);

CREATE TABLE IF NOT EXISTS contract.relation_checks (
    qa_run_id VARCHAR NOT NULL,
    relation_type VARCHAR NOT NULL,
    check_name VARCHAR NOT NULL,
    sample_size UBIGINT NOT NULL,
    valid_count UBIGINT,
    invalid_count UBIGINT,
    ambiguous_count UBIGINT,
    precision DOUBLE,
    signed_graph_frustration DOUBLE,
    status VARCHAR NOT NULL CHECK (status IN ('pass', 'fail', 'warning')),
    checked_at TIMESTAMPTZ NOT NULL,
    dataset_version VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (qa_run_id, relation_type, check_name),
    CHECK (precision IS NULL OR (precision >= 0 AND precision <= 1))
);

CREATE TABLE IF NOT EXISTS contract.dataset_statistics (
    dataset_name VARCHAR NOT NULL,
    dataset_version VARCHAR NOT NULL,
    statistic_name VARCHAR NOT NULL,
    stratum_hash VARCHAR NOT NULL,
    stratum JSON,
    numeric_value DOUBLE,
    text_value VARCHAR,
    unit VARCHAR,
    computed_at TIMESTAMPTZ NOT NULL,
    code_commit VARCHAR NOT NULL,
    config_hash VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    PRIMARY KEY (dataset_name, dataset_version, statistic_name, stratum_hash)
);

-- Public views. build_catalog.py replaces these with manifest-pinned Parquet views.

CREATE VIEW IF NOT EXISTS core.markets AS SELECT * FROM contract.markets WHERE false;
CREATE VIEW IF NOT EXISTS core.outcomes AS SELECT * FROM contract.outcomes WHERE false;
CREATE VIEW IF NOT EXISTS core.fees AS SELECT * FROM contract.fees WHERE false;
CREATE VIEW IF NOT EXISTS core.trading_rules AS SELECT * FROM contract.trading_rules WHERE false;
CREATE VIEW IF NOT EXISTS core.settlements AS SELECT * FROM contract.settlements WHERE false;

CREATE VIEW IF NOT EXISTS market_data.prices AS SELECT * FROM contract.prices WHERE false;
CREATE VIEW IF NOT EXISTS market_data.trades AS SELECT * FROM contract.trades WHERE false;
CREATE VIEW IF NOT EXISTS market_data.orderbook_updates AS SELECT * FROM contract.orderbook_updates WHERE false;
CREATE VIEW IF NOT EXISTS market_data.orderbook_snapshots AS SELECT * FROM contract.orderbook_snapshots WHERE false;

CREATE VIEW IF NOT EXISTS semantics.event_families AS SELECT * FROM contract.event_families WHERE false;
CREATE VIEW IF NOT EXISTS semantics.event_family_members AS SELECT * FROM contract.event_family_members WHERE false;
CREATE VIEW IF NOT EXISTS semantics.relations AS SELECT * FROM contract.relations WHERE false;
CREATE VIEW IF NOT EXISTS semantics.relation_participants AS SELECT * FROM contract.relation_participants WHERE false;
CREATE VIEW IF NOT EXISTS semantics.relation_audits AS SELECT * FROM contract.relation_audits WHERE false;
CREATE VIEW IF NOT EXISTS semantics.constraints AS SELECT * FROM contract.constraints WHERE false;
CREATE VIEW IF NOT EXISTS semantics.constraint_terms AS SELECT * FROM contract.constraint_terms WHERE false;

CREATE VIEW IF NOT EXISTS benchmark.decision_times AS SELECT * FROM contract.decision_times WHERE false;
CREATE VIEW IF NOT EXISTS benchmark.beliefs AS SELECT * FROM contract.beliefs WHERE false;
CREATE VIEW IF NOT EXISTS benchmark.joint_distributions AS SELECT * FROM contract.joint_distributions WHERE false;
CREATE VIEW IF NOT EXISTS benchmark.joint_distribution_members AS SELECT * FROM contract.joint_distribution_members WHERE false;
CREATE VIEW IF NOT EXISTS benchmark.joint_samples AS SELECT * FROM contract.joint_samples WHERE false;
CREATE VIEW IF NOT EXISTS benchmark.episodes AS SELECT * FROM contract.episodes WHERE false;
CREATE VIEW IF NOT EXISTS benchmark.episode_families AS SELECT * FROM contract.episode_families WHERE false;
CREATE VIEW IF NOT EXISTS benchmark.splits AS SELECT * FROM contract.splits WHERE false;
CREATE VIEW IF NOT EXISTS benchmark.split_memberships AS SELECT * FROM contract.split_memberships WHERE false;
CREATE VIEW IF NOT EXISTS benchmark.scenarios AS SELECT * FROM contract.scenarios WHERE false;
CREATE VIEW IF NOT EXISTS benchmark.stress_events AS SELECT * FROM contract.stress_events WHERE false;
CREATE VIEW IF NOT EXISTS benchmark.oracle_variants AS SELECT * FROM contract.oracle_variants WHERE false;

CREATE VIEW IF NOT EXISTS simulation.experiment_runs AS SELECT * FROM contract.experiment_runs WHERE false;
CREATE VIEW IF NOT EXISTS simulation.fills AS SELECT * FROM contract.fills WHERE false;
CREATE VIEW IF NOT EXISTS simulation.portfolio_states AS SELECT * FROM contract.portfolio_states WHERE false;
CREATE VIEW IF NOT EXISTS simulation.portfolio_positions AS SELECT * FROM contract.portfolio_positions WHERE false;
CREATE VIEW IF NOT EXISTS simulation.results AS SELECT * FROM contract.results WHERE false;
CREATE VIEW IF NOT EXISTS simulation.simulator_validation AS SELECT * FROM contract.simulator_validation WHERE false;

CREATE VIEW IF NOT EXISTS qa.replay_events AS SELECT * FROM contract.replay_events WHERE false;
CREATE VIEW IF NOT EXISTS qa.book_validity AS SELECT * FROM contract.book_validity WHERE false;
CREATE VIEW IF NOT EXISTS qa.completeness AS SELECT * FROM contract.completeness WHERE false;
CREATE VIEW IF NOT EXISTS qa.schema_checks AS SELECT * FROM contract.schema_checks WHERE false;
CREATE VIEW IF NOT EXISTS qa.relation_checks AS SELECT * FROM contract.relation_checks WHERE false;
CREATE VIEW IF NOT EXISTS qa.dataset_statistics AS SELECT * FROM contract.dataset_statistics WHERE false;

COMMIT;
