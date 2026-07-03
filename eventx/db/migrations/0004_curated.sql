-- curated.* holds derived series, rebuilt from raw.* without re-pulling (guardrail A3).

-- Reconstructed log-odds bars (guardrail C7/C8): built from trades (+ L2 mid where it
-- exists), NOT the candle endpoint, since Polymarket candles are only ~7 months.
-- outcome_id defaults to '' so binary markets sit cleanly in the PK.
CREATE TABLE IF NOT EXISTS curated.pm_bars (
    venue           text        NOT NULL,
    market_id       text        NOT NULL,
    outcome_id      text        NOT NULL DEFAULT '',
    freq_min        integer     NOT NULL,
    ts              timestamptz NOT NULL,
    mid_price       numeric,                 -- orderbook mid where L2 exists, else last print
    mid_logodds     numeric,                 -- ln(p/(1-p)), p clipped to [eps, 1-eps]
    last_price      numeric,
    n_trades        integer     NOT NULL DEFAULT 0,
    notional        numeric     NOT NULL DEFAULT 0,   -- sum price*size in the bar
    px_dispersion   numeric,                 -- std of intra-bar prices
    best_bid        numeric,                 -- L2 features, null where snapshots absent
    best_ask        numeric,
    spread          numeric,
    depth_bid       numeric,
    depth_ask       numeric,
    price_source    text,                    -- 'midprice' | 'last' — audit which was used
    extract_version text        NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (venue, market_id, outcome_id, freq_min, ts)
);
CREATE INDEX IF NOT EXISTS ix_pm_bars_market_ts ON curated.pm_bars (venue, market_id, ts);

-- market -> entities / cashtags / keywords, driving both news and KOL association
-- (implemenation_plan §3.4). Rule-based + light NER; kept auditable.
CREATE TABLE IF NOT EXISTS curated.market_entities (
    venue           text        NOT NULL,
    market_id       text        NOT NULL,
    entity          text        NOT NULL,
    entity_type     text        NOT NULL,    -- cashtag | ticker | person | org | keyword
    source          text,                    -- how it was extracted (rule/ner)
    extract_version text        NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (venue, market_id, entity, entity_type)
);
CREATE INDEX IF NOT EXISTS ix_market_entities_entity ON curated.market_entities (entity);
