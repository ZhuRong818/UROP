-- raw.* mirrors of findata news.* tables (shapes confirmed via catalog, guardrail A1).
-- News sentiment is per-SYMBOL and WEEKLY (news.symbol_sentiment) — it maps to
-- finance/crypto markets but not politics/sports, which is why news-control strength
-- varies by category and results are reported category-stratified (guardrail D12).

CREATE TABLE IF NOT EXISTS raw.news_articles (
    url             text        PRIMARY KEY,
    published_at    timestamptz NOT NULL,
    symbol          text,
    related_symbols text[],
    publisher       text,
    author          text,
    category        text,
    headline        text,
    summary         text,
    body            text,
    source_raw      jsonb,
    extract_version text        NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_news_articles_pub    ON raw.news_articles (published_at);
CREATE INDEX IF NOT EXISTS ix_news_articles_symbol ON raw.news_articles (symbol, published_at);

CREATE TABLE IF NOT EXISTS raw.news_symbol_sentiment (
    symbol              text        NOT NULL,
    period_end_date     date        NOT NULL,
    buzz                numeric,
    weekly_avg          numeric,
    articles_last_week  integer,
    sentiment_score     numeric,
    bearish_pct         numeric,
    bullish_pct         numeric,
    source_raw          jsonb,
    extract_version     text        NOT NULL,
    ingested_at         timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, period_end_date)
);

-- KOL roster (findata news.kol_roster). ~6k handles; the sampling frame for KOL features.
CREATE TABLE IF NOT EXISTS raw.kol_roster (
    handle                    text PRIMARY KEY,
    display_name              text,
    twitter_id                text,
    follower_tier             text,
    notes                     text,
    active                    boolean,
    added_at                  timestamptz,
    added_by                  text,
    updated_at                timestamptz,
    tweet_freq_daily          numeric,
    last_refreshed_at         timestamptz,
    refresh_interval_mins     integer,
    floor_fill_complete_at    timestamptz,
    targeted_fill_complete_at timestamptz,
    extract_version           text        NOT NULL,
    ingested_at               timestamptz NOT NULL DEFAULT now()
);

-- KOL tweets (findata news.kol_tweets). Partitioned monthly on created_at.
CREATE TABLE IF NOT EXISTS raw.kol_tweets (
    tweet_id            text        NOT NULL,
    created_at          timestamptz NOT NULL,
    kol_username        text        NOT NULL,
    author_username     text,
    author_id           text,
    author_name         text,
    author_followers    integer,
    author_verified     boolean,
    tweet_type          text,
    lang                text,
    text                text,
    url                 text,
    in_reply_to_id      text,
    in_reply_to_username text,
    conversation_id     text,
    is_reply            boolean,
    quoted_tweet_id     text,
    retweeted_tweet_id  text,
    retweet_count       integer,
    reply_count         integer,
    like_count          integer,
    quote_count         integer,
    bookmark_count      integer,
    view_count          integer,
    cashtags            text[],
    hashtags            text[],
    mentioned_users     text[],
    urls                text[],
    media_urls          text[],
    fetched_at          timestamptz,
    source_raw          jsonb,
    extract_version     text        NOT NULL,
    ingested_at         timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tweet_id, created_at)
) PARTITION BY RANGE (created_at);
CREATE INDEX IF NOT EXISTS ix_kol_tweets_handle_ts ON raw.kol_tweets (kol_username, created_at);
