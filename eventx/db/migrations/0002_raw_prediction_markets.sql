-- raw.* mirrors of the findata prediction_markets.* tables (shapes confirmed via
-- /catalog/tables/.../schema.json, guardrail A1). Every row carries provenance:
-- extract_version (which frozen pull) + ingested_at. Kalshi prices are INTEGER CENTS;
-- Polymarket prices are numeric probabilities in [0,1].

-- Helper: create a monthly RANGE partition on demand (call before bulk load).
CREATE OR REPLACE FUNCTION meta.ensure_month_partition(parent text, month date)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    part  text := parent || '_' || to_char(month, 'YYYYMM');
    lo    date := date_trunc('month', month)::date;
    hi    date := (date_trunc('month', month) + interval '1 month')::date;
BEGIN
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %s PARTITION OF %s FOR VALUES FROM (%L) TO (%L)',
        part, parent, lo, hi);
END $$;

-- Canonical join across venues (predexon_id ties matched markets together).
CREATE TABLE IF NOT EXISTS raw.pm_canonical_markets (
    predexon_id     text PRIMARY KEY,
    question        text,
    category        text,
    venues          jsonb,
    source_raw      jsonb,
    extract_version text        NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.pm_polymarket_markets (
    condition_id        text PRIMARY KEY,
    question            text,
    slug                text,
    outcomes            jsonb,
    outcome_prices      jsonb,
    clob_token_ids      jsonb,
    volume_num          numeric,
    liquidity_num       numeric,
    start_date          timestamptz,
    end_date            timestamptz,
    closed_time         timestamptz,
    active              boolean,
    closed              boolean,
    archived            boolean,
    enable_order_book   boolean,
    market_maker_address text,
    source_raw          jsonb,
    extract_version     text        NOT NULL,
    ingested_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_pm_poly_markets_end   ON raw.pm_polymarket_markets (end_date);

CREATE TABLE IF NOT EXISTS raw.pm_kalshi_markets (
    ticker          text PRIMARY KEY,
    event_ticker    text,
    market_type     text,
    title           text,
    status          text,
    result          text,
    yes_sub_title   text,
    no_sub_title    text,
    yes_bid         integer,     -- cents
    yes_ask         integer,
    no_bid          integer,
    no_ask          integer,
    last_price      integer,     -- cents
    volume          bigint,
    volume_24h      bigint,
    open_interest   bigint,
    open_time       timestamptz,
    close_time      timestamptz,
    created_time    timestamptz,
    expiration_time timestamptz,
    settlement_ts   timestamptz,
    source_raw      jsonb,
    extract_version text        NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_pm_kalshi_markets_event ON raw.pm_kalshi_markets (event_ticker);
CREATE INDEX IF NOT EXISTS ix_pm_kalshi_markets_close ON raw.pm_kalshi_markets (close_time);

-- Trades: the bulk of the request budget. Partitioned monthly on the trade timestamp.
CREATE TABLE IF NOT EXISTS raw.pm_polymarket_trades (
    trade_id        text        NOT NULL,
    condition_id    text,
    asset_id        text,
    side            text,
    price           numeric,     -- probability in [0,1]
    size            numeric,
    taker           text,
    maker           text,
    ts              timestamptz  NOT NULL,
    source_raw      jsonb,
    extract_version text         NOT NULL,
    ingested_at     timestamptz  NOT NULL DEFAULT now(),
    PRIMARY KEY (trade_id, ts)
) PARTITION BY RANGE (ts);
CREATE INDEX IF NOT EXISTS ix_pm_poly_trades_cond_ts ON raw.pm_polymarket_trades (condition_id, ts);
CREATE INDEX IF NOT EXISTS ix_pm_poly_trades_asset_ts ON raw.pm_polymarket_trades (asset_id, ts);

CREATE TABLE IF NOT EXISTS raw.pm_kalshi_trades (
    trade_id        text        NOT NULL,
    ticker          text        NOT NULL,
    count           integer,
    yes_price       integer,     -- cents
    no_price        integer,     -- cents
    taker_side      text,
    created_time    timestamptz  NOT NULL,
    extract_version text         NOT NULL,
    ingested_at     timestamptz  NOT NULL DEFAULT now(),
    PRIMARY KEY (trade_id, created_time)
) PARTITION BY RANGE (created_time);
CREATE INDEX IF NOT EXISTS ix_pm_kalshi_trades_tkr_ts ON raw.pm_kalshi_trades (ticker, created_time);

-- Candles: recent window only, used to validate bar reconstruction (guardrail C7).
-- outcome_id defaults to '' so it can sit in the PK when the source leaves it null.
CREATE TABLE IF NOT EXISTS raw.pm_candles (
    venue           text        NOT NULL,
    market_id       text        NOT NULL,
    outcome_id      text        NOT NULL DEFAULT '',
    interval_min    integer     NOT NULL,
    bucket_ts       timestamptz NOT NULL,
    open            numeric,
    high            numeric,
    low             numeric,
    close           numeric,
    volume          numeric,
    extract_version text        NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (venue, market_id, outcome_id, interval_min, bucket_ts)
);

-- L2 snapshots: sparse historically; liquidity gating falls back to trade proxies
-- where these are missing (guardrail C9). Partitioned monthly.
CREATE TABLE IF NOT EXISTS raw.pm_polymarket_orderbook (
    asset_id        text        NOT NULL,
    condition_id    text,
    market          text,
    snapshot_ts     timestamptz NOT NULL,
    bids            jsonb,
    asks            jsonb,
    tick_size       text,
    min_order_size  text,
    neg_risk        boolean,
    hash            text,
    source_raw      jsonb,
    extract_version text        NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (asset_id, snapshot_ts)
) PARTITION BY RANGE (snapshot_ts);
CREATE INDEX IF NOT EXISTS ix_pm_poly_ob_cond_ts ON raw.pm_polymarket_orderbook (condition_id, snapshot_ts);

CREATE TABLE IF NOT EXISTS raw.pm_open_interest (
    venue           text        NOT NULL,
    market_id       text        NOT NULL,
    bucket_ts       timestamptz NOT NULL,
    open_interest   numeric,
    extract_version text        NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (venue, market_id, bucket_ts)
);

-- Cross-venue matched pairs: feature-only, per research_plan §3.
CREATE TABLE IF NOT EXISTS raw.pm_matched_pairs (
    venue_a         text        NOT NULL,
    venue_a_id      text        NOT NULL,
    venue_b         text        NOT NULL,
    venue_b_id      text        NOT NULL,
    match_kind      text,
    similarity      numeric,
    source_raw      jsonb,
    extract_version text        NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (venue_a, venue_a_id, venue_b, venue_b_id)
);
