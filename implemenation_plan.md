# EventX — Implementation Plan v2 (Core: T1, T3, T5)

Grounded in the `findata` API at `https://kv.run:5000/`. Assumes Python 3.11+, PostgreSQL, and the v4 research plan. Where the API doc names a data domain but not an exact path/schema (historical L2 orderbook, open-interest history, holders/leaderboard, matched pairs), **confirm the real shape via the OpenAPI spec or the `catalog_table_schema` / `catalog_table_profile` MCP tools before coding.**

**v2 changes (all before writing pipeline code):** (1) explicit **outcome/token normalization** — the prediction unit is now per outcome, not per market; (2) actual `resolution_ts` is **never a feature**, only a label filter; (3) **corrected purged-split** using a `Timedelta` purge; (4) **eligibility (pre-*t*) separated from label-validity (forward)** so the benchmark never conditions on future liquidity; (5) `price_logodds` + `price_source` flag replaces the misleading `mid_logodds`; (6) a **deterministic tweet/news↔market matching rule** with a released association table; (7) **stratified nulls**. Plus a toy end-to-end slice before full ingestion.

---

## 0. API realities & landmines (read first)

1. **Rate limit 100 req/min, auth on every route.** 401 anon; 503 fail-closed if Lumid unreachable. Ingestion is a **multi-hour resumable batch job** — checkpoint table, honor `429 Retry-After`, backoff on `503`.
2. **Polymarket candles only ~7 months.** Reconstruct bars from **trades** for a uniform label definition; use candles only to validate the reconstruction.
3. **Historical L2 depth is limited** (recorder covers 500 active markets going forward). Liquidity handling for the historical window relies on **trade-based proxies**; true L2 depth only where snapshots exist. Confirm coverage with `catalog_table_profile`; record as missingness.
4. **News is per-ticker (financial symbols).** Associate to markets via full-text `/news/search` on entities; use structured per-ticker sentiment only where a symbol mapping exists. News-control strength varies by category → stratified reporting.
5. **KOL tweets are full-text + cashtag indexed.** Cashtags map to finance/crypto; other categories need entity/keyword matching.
6. **Lineage stripped, canonical provider chosen by API.** Snapshot a **frozen, content-hashed extract**; all downstream work runs against it.
7. **Markets have multiple outcomes / YES-NO tokens (NEW).** "Price" is undefined until you fix a canonical outcome token. Treat this as an architectural constraint (§1.1), not a detail.
8. **Resolution-leakage exclusion needs an operational rule** (§4.3).

---

## 1. Infrastructure & schema (Phase 0)

**Repo layout** (unchanged from v1): `ingest/ db/ clean/ labels/ features/ splits/ tasks/ eval/ release/ config/`.

### 1.1 Outcome normalization — the prediction unit

**The prediction unit is `(venue, market_id, outcome_id, t)`**, not `(venue, market_id, t)`.
- **Binary markets:** pick a single **canonical side** (the YES/proposition token); its price is the proposition probability. Do **not** also include the NO token — it's mechanically `1 − YES` and would double-count.
- **Multi-outcome markets:** each outcome token is its own probability series; the tokens sum to ~1, so outcomes within a market are dependent.
- **v1 scope decision:** **binary markets only** (one canonical side each). Defer multi-outcome to v2 of the dataset — the sum-to-1 dependency complicates labels, nulls, and FDR. State this scope explicitly.

**Core tables** (raw → curated separation so re-cleaning never re-pulls):
- `raw.pm_markets(venue, market_id, outcome_id, outcome_name, canonical_side, question, category, created_ts, scheduled_close_ts, scheduled_event_ts, resolution_ts, resolution_source, status, raw_json)`
- `raw.pm_trades(venue, market_id, outcome_id, ts, price_yes_prob, size, side, trade_id)`
- `raw.pm_candles(venue, market_id, outcome_id, interval, ts, o,h,l,c, volume)` — recent, for validation
- `raw.pm_l2(venue, market_id, outcome_id, ts, bid_px, bid_sz, ask_px, ask_sz, ...)` — where available
- `raw.news(article_id, ts, category, symbols[], sentiment_label, sentiment_reasoning, title, body, raw_json)`
- `kol.tweets(tweet_id, handle, ts, text, cashtags[], reply_to, retweets, ...)`
- `curated.pm_bars(venue, market_id, outcome_id, freq, ts, price_logodds, price_source, has_l2, n_trades, notional, px_dispersion, depth_*)`
- `curated.assoc(kind, doc_id, venue, market_id, outcome_id, ts, match_reason)` — the **released association table** (§5.4)
- `meta.job_checkpoints(job, key, cursor, status, updated_ts)`
- `meta.extract_version(version, created_ts, config_hash, row_counts jsonb)`

`price_source ∈ {l2_mid, last_trade, candle_close}`; `has_l2 ∈ {0,1}` — so reviewers see exactly where true midprice vs. trade-print proxy is used. Index `(venue, market_id, outcome_id, ts)` and `(handle, ts)`; partition big tables by month.

### 1.2 Rate-limited resumable client
(As v1 — `FindataClient` with `_throttle` at ~90 rpm, tenacity exponential backoff, `429 Retry-After` handling, `503` retry, `paginate(limit≤1000, offset)`.) Every puller checkpoints per `(market_id, outcome_id, cursor)`.

---

## 2. Data acquisition (Phase 1)

Cheapest → most expensive in request budget:

1. **Market universe.** `GET /prediction-markets/markets/search` → enumerate markets **and their outcomes**; store per-outcome rows with canonical side. Filter to **binary markets** for v1.
2. **Window & selection.** Restrict to markets whose life overlaps a dense **12–18-month** window; drop dead markets (min lifetime trade/notional). Record category composition.
3. **Trades.** `GET /prediction-markets/trades/{venue}/{id}` per selected outcome, paginated — the bulk of the budget; run resumable, overnight.
4. **Candles (recent).** `GET /prediction-markets/candles/{venue}/{id}?interval=…` for the ~7-month overlap — validation only.
5. **L2 (where available).** Confirm endpoint via OpenAPI/catalog; pull where coverage exists.
6. **News.** `/news/{symbol}` (+ sentiment) for symbol-mappable markets; `/news/search` on entities otherwise.
7. **KOL tweets.** `/kols/tweets/search?q=…` by entities/cashtags, or pull the roster timeline via `/kols/{handle}/tweets/history` and index locally; dedupe on `tweet_id`.

---

## 3. Cleaning & normalization (Phase 2)

**3.1 Bar reconstruction (trades → log-odds bars), per outcome token.** Resample to 1-min:
- Price: **L2 midprice where available** (`price_source=l2_mid`), else **last trade print** (`price_source=last_trade`); record `has_l2`.
- `price_logodds = ln(p/(1−p))`, clipped at `[ε, 1−ε]`.
- Per bar: `n_trades`, `notional`, `px_dispersion`, depth features where L2.
- Validate reconstructed close vs. `/candles` on the overlap (correlation ≈ 1).

**3.2 Dedup & integrity.** Trades on `trade_id`; tweets on `tweet_id`; news on `article_id`. UTC ISO-8601; assert monotonic per `(venue, market_id, outcome_id)`.

**3.3 Metadata & categories.** Fixed taxonomy (politics / crypto / sports / macro / other). Parse `scheduled_close_ts`, `scheduled_event_ts`, `resolution_ts`, `resolution_source`, `status` into structured fields.

**3.4 Entity extraction (market → entities/cashtags/keywords).** Rule-based first: cashtags, light spaCy NER, salient keywords → `market_entities(market_id, outcome_id, entity, type)`. Auditable, not an LLM pipeline.

---

## 4. Labels & eligibility (Phase 3–4) — the crux

### 4.1 Two distinct filters (do not conflate)
- **Pre-*t* eligibility** — decided using **only ≤ t** information; determines which `(outcome, t)` are prediction points: enough recent history, minimum pre-*t* trade activity, reasonable pre-*t* spread, not near-terminal.
- **Forward-label validity** — decided by future **measurability** only: the price series exists at `t+Δ` so `Δy` is computable, and the market isn't mechanically settled across the window.

Thin-market noise is handled by the **robust price definition** (L2 mid preferred) + pre-*t* eligibility — **not** by gating labels on forward volume/notional (that would condition the benchmark on future liquidity and bias the problem). Any forward-liquidity filter is a **reported robustness variant only**.

```python
import numpy as np, pandas as pd

def build_labels(bars, horizon_bars, k=4.0, vol_window=240,
                 elig_min_pretrades=3, elig_min_prenotional=100.0):
    b = bars.sort_values("ts").reset_index(drop=True)
    # forward target (measurability, not selection)
    fwd = b["price_logodds"].shift(-horizon_bars) - b["price_logodds"]
    label_valid = fwd.notna()
    # jump on robust price
    dy = b["price_logodds"].diff()
    sigma = dy.rolling(vol_window, min_periods=30).std()
    is_jump = (fwd.abs() >= k * sigma)
    # PRE-t eligibility — only <= t info
    pre_trades   = b["n_trades"].rolling(vol_window, min_periods=1).sum()
    pre_notional = b["notional"].rolling(vol_window, min_periods=1).sum()
    eligible = (pre_trades >= elig_min_pretrades) & (pre_notional >= elig_min_prenotional)
    eligible &= ~b["near_terminal"]
    b["eligible"]    = eligible.astype(int)
    b["label_valid"] = label_valid.astype(int)
    b["y_jump"]      = np.where(is_jump, 1, 0)
    b["fwd_dy"]      = fwd
    return b
# benchmark rows = eligible & label_valid
```
Repeat per Δ ∈ {5m,30m,2h,6h,24h}. Calibrate `k`, `vol_window`, eligibility thresholds on an **early** slice; report sensitivity.

### 4.2 Boundary handling
Clipping keeps log-odds finite; flag `near_terminal` once price crosses and stays beyond 0.98/0.02.

### 4.3 Resolution-leakage exclusion (operational ladder)
"Outcome already public" isn't queryable, so, strongest first: (1) drop `t` after the outcome was effectively determined where `resolution_ts`/event time is known; (2) drop after `status` = resolving/settling; (3) price-convergence fallback; (4) category-specific event times (sports end, election calls) for dominant categories. **`resolution_ts` is used here for filtering only — never as a feature.** Log and report the exclusion rate.

---

## 5. Feature engineering (Phase 5) — strictly point-in-time

Only information with timestamp ≤ t. Four families (cross-venue feature-only).

**5.1 Market microstructure (b0).** From `curated.pm_bars` up to `t`: recent realized vol of log-odds, short-window momentum, spread & depth-imbalance (where L2), order-flow imbalance, trade-count/notional trend, and **time-to-`scheduled_close`** (NEW — use scheduled/known-at-`t` deadlines only; **not** actual `resolution_ts`).

**5.2 News (b1).** Pre-*t* windows {1h,6h,24h}: article volume on the market's entities via `/news/search`; per-ticker structured sentiment where a symbol mapping exists, plus a `news_symbol_mapped ∈ {0,1}` flag (itself informative; supports stratification).

**5.3 KOL (b2).** Roster tweets matching entities/cashtags in pre-*t* windows: burst intensity vs. baseline, author reach, **train-only** historical lift of the posting KOL, cross-tweet coherence, cashtag-match strength.

**5.4 Deterministic matching rule (NEW — the highest-risk part, so make it auditable).**
```text
associate(doc, outcome) := TRUE iff
    exact cashtag match with the market's cashtags
    OR >=1 high-confidence NER entity match (confidence >= c)
    OR cosine(emb(doc_text), emb(market_question)) >= tau
where c, tau are tuned ONLY on train/validation.
```
Persist results to `curated.assoc` and **release that association table with the Feature Track**, so submitters don't re-run matching and the frozen core stays reproducible. Matching-method improvements (e.g., better embeddings/LLM matchers) belong to the **Rehydration Track**, not the Feature Track.

**Anti-leakage discipline:** every rolling feature has a strict as-of-`t` cutoff; unit-test that moving `t` earlier never changes a feature. Persist the feature set per extract version.

---

## 6. Splits (Phase 6) — temporal, purged, market-grouped

Labels look forward, so adjacent samples' windows overlap → purge. Forward-only walk-forward (train on past, test on future), so an embargo *after* test is unnecessary (that's only for two-sided K-fold-with-purge); the needed purge is the pre-test gap, with a **`Timedelta`** length per horizon:

```python
def purged_walk_forward(df, ts_col, horizon_minutes, n_splits=5):
    df = df.sort_values(ts_col).reset_index(drop=True)
    t = df[ts_col]                                   # pandas datetime
    purge = pd.Timedelta(minutes=horizon_minutes)    # per-horizon: 5,30,120,360,1440
    bounds = pd.date_range(t.iloc[0], t.iloc[-1], periods=n_splits + 1)
    for i in range(1, n_splits):
        test_lo, test_hi = bounds[i], bounds[i + 1]
        test  = (t >= test_lo) & (t < test_hi)
        train = t < (test_lo - purge)                # forward-only + label-overlap purge
        yield np.where(train)[0], np.where(test)[0]
```
**Market-level grouping (NEW):** because per-outcome samples from the same market at the same `t` are dependent, group by `market_id` when forming folds and nulls so the same market's rows don't straddle train/test. Hold out a final contiguous block as the **untouched test set**; freeze split indices in the release.

---

## 7. Task implementations (Phase 7)

### T1 — Jump / early-warning
Regularized logistic (interpretable deltas) + LightGBM (ceiling), per horizon. Metrics: AUC-PR (primary; imbalanced), Brier, calibration + ECE, lead time. Leaderboard on the frozen test block, Feature Track.

### T3 — Incremental information (spine)
Nested b0→b1→b2→b3 on identical splits/labels. Headline: `ΔAUC-PR` and `ΔBrier` for **b2−b1** and **b3−b1**.
- **Significance:** DeLong assumes i.i.d. (violated) → **moving-block bootstrap over the test period**; report CIs.
- **Stratified nulls (NEW — harder):** shuffle tweet↔market assignments **within strata** — same category, same time block — preserving per-market activity and per-tweet-volume distributions. The real deltas must beat this stratified null (not just fully-random shuffling, which is too easy — it would leak signal from politics-into-sports or busy-into-quiet mismatches). Also keep the placebo-timestamp null.

### T5 — KOL influence ranking
Per-KOL out-of-sample lift (ablate that KOL's tweets → drop in b3 test performance, or predictive lead on `fwd_dy`), estimated out-of-sample. P-values via block bootstrap / permutation, then **Benjamini–Hochberg FDR** across the 3,702 handles (`multipletests(..., method="fdr_bh")`). Report rank stability across folds; stratify by category.

---

## 8. Economic significance (Phase 8) — stylized, not a strategy
Conservative spread/fee-aware backtest as an **economic-significance check**: trade on threshold crossings, charge realistic Polymarket fees + half-spread, no better-than-mid fills, assumptions stated. Answers "does the signal survive plausible costs?" — not a deployable strategy. Keep it simple.

---

## 9. Reference finding & stratification (Phase 9)
From the frozen test block: best baselines per track, b2−b1 / b3−b1 with bootstrap CIs, **headroom across horizons / categories / liquidity regimes**, and **category composition + stratified performance** so no single category drives results. Positive/limited/null all publishable.

---

## 10. Release & reproducibility (Phase 10)
- **Feature Track:** precomputed features + labels + **frozen `curated.assoc` table** + frozen split indices + eval code + leaderboard. Content-hash the extract; write `meta.extract_version`.
- **Rehydration Track:** tweet-ID + news-ID manifest (where licensing allows) + one deliberately-simple raw-text baseline; matching-method improvements live here. Comparisons within-track.
- **Datasheet:** provenance, coverage, category composition, missingness (esp. historical L2 gap, `price_source` breakdown), deleted-tweet rate, biases, intended/out-of-scope uses.
- **Licensing:** features/labels CC-BY (verify upstream); code MIT/Apache. **X ToS:** ship IDs, not raw text, publicly.
- **DOI:** deposit Feature Track on Zenodo; pin version in the paper.

---

## 11. Toy end-to-end slice FIRST (before full ingestion)

Run a walking skeleton to validate definitions, not performance:
```text
10–20 binary markets · 1–2 months · one horizon (30m)
trade bars → labels (eligibility + validity) → simple KOL/news features
→ b0/b1/b2/b3 train+eval → export Feature Track → reload with a clean script
```
Verifies: outcome/price normalization works, labels are non-trivial after the leakage filter, feature timestamps are point-in-time, the split code runs, the baseline ladder trains and evaluates, and exported files load cleanly. This can save weeks.

---

## 12. Build order (revised)

1. Schema + API client + checkpointing
2. **Market universe + outcome/binary normalization** ← critical, do early
3. **Toy end-to-end slice** (§11)
4. Trade pull for the selected window (overnight)
5. Bar reconstruction + candle validation
6. Resolution-leakage / eligibility rules
7. Label generation
8. Entity/cashtag extraction
9. News + KOL association (deterministic rule → `curated.assoc`)
10. Feature builders
11. Splits (purged, market-grouped)
12. b0/b1/b2/b3 for T1/T3
13. Stratified nulls + block bootstrap
14. T5 ranking + FDR
15. Stylized backtest
16. Feature Track export + datasheet + release

**Lock these operational definitions before step 4:** the prediction unit (per-outcome, binary-only v1), what price means (`price_logodds` + `price_source`), inclusion/resolution-leakage rules, the point-in-time feature boundary (scheduled deadlines only), and the deterministic association rule. Once locked, the architecture is solid — proceed via the toy slice.