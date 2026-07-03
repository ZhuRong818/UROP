-- EventX schema layout: raw (API mirrors) | curated (derived) | meta (bookkeeping).
-- Raw and curated are separated so re-cleaning never re-pulls (guardrail A3).

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS curated;
CREATE SCHEMA IF NOT EXISTS meta;

-- Resumability: one row per (job, key) tracks the last cursor so a killed pull
-- resumes exactly where it stopped (guardrail A2).
CREATE TABLE IF NOT EXISTS meta.job_checkpoints (
    job         text        NOT NULL,
    key         text        NOT NULL,       -- e.g. venue:market_id
    cursor      text,                        -- opaque cursor/offset/last-ts
    status      text        NOT NULL DEFAULT 'pending',  -- pending|running|done|error
    n_rows      bigint      NOT NULL DEFAULT 0,
    error       text,
    updated_ts  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (job, key)
);

-- Reproducibility: the frozen extract is content-hashed and versioned; downstream
-- work pins one version (guardrail A3).
CREATE TABLE IF NOT EXISTS meta.extract_version (
    version     text        PRIMARY KEY,
    created_ts  timestamptz NOT NULL DEFAULT now(),
    config_hash text        NOT NULL,        -- hash of eventx.yaml + code rev
    window_start timestamptz,
    window_end   timestamptz,
    row_counts  jsonb       NOT NULL DEFAULT '{}'::jsonb,
    notes       text
);
