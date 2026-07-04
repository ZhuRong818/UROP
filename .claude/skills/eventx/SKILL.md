---
name: eventx
description: >-
  Guardrails for the EventX prediction-market benchmark (KOL / news / microstructure
  over Kalshi + Polymarket). Use whenever writing or reviewing code for this repo —
  ingestion, bar reconstruction, labels, features, splits, tasks (T1/T3/T5), or release.
  Enforces leakage safety, findata-API landmines, causal-language discipline, and
  statistical rigor. Source of truth: research_plan.md + implemenation_plan.md.
user-invocable: true
---

# EventX guardrails

EventX is a leakage-safe **benchmark** measuring whether KOL social-media signals carry
incremental, point-in-time predictive information about prediction-market repricing
beyond a news + microstructure baseline. This project is unusually easy to break
*silently*: a single point-in-time leak, a hardcoded API path, or the wrong significance
test invalidates the headline result **without any error surfacing**. The rules below are
non-negotiable. Each carries its *why* so you can judge edge cases rather than follow
blindly.

## A. API & reproducibility

1. **Never hardcode a guessed findata endpoint or schema.** Verify the real shape via
   `GET /openapi.json` (or the API guide), or the `catalog_table_schema` /
   `catalog_table_profile` MCP tools, before writing code against it.
   *Why:* the API doc names data domains without exact paths/schemas (historical L2,
   open-interest history, holders/leaderboard, matched pairs); guessing burns the request
   budget and rots.
2. **All ingestion is a resumable, checkpointed batch job**, not a one-shot script. Write
   a `meta.job_checkpoints` row per `(job, key, cursor)`; stay ≤90 rpm (headroom under the
   100 rpm cap); honor `429 Retry-After`; treat `503` as retry-with-backoff (Lumid
   unreachable = fail-closed).
   *Why:* 100 req/min + auth on every route + 251M+ trades = a multi-hour job that will be
   killed and resumed.
3. **Work against a frozen, content-hashed, versioned extract** (`meta.extract_version`),
   never live calls. Keep **raw ⟂ curated** so re-cleaning never re-pulls.
   *Why:* the API strips lineage and picks a canonical provider per surface — it is not
   stable over time, so reproducibility requires pinning the exact rows used.

## B. Leakage safety (the core of the benchmark's credibility)

4. **Strictly point-in-time features** — for every `(market, t)` use only information with
   timestamp `≤ t`. Unit-test that shifting `t` earlier never changes a feature. KOL
   historical-lift features must come from **training-only** estimates, never the test
   period.
   *Why:* one look-ahead leak invalidates the headline result silently.
5. **Purged + embargoed walk-forward CV.** Labels look forward, so adjacent samples'
   windows overlap → naive CV leaks; purge the overlap and embargo after each test fold.
   Hold out a final contiguous **untouched** block for the headline numbers; use
   walk-forward folds only for model selection. **Freeze split indices** in the release.
6. **Resolution-leakage exclusion** — drop `(market, t)` pairs where the outcome is already
   public or mechanically settled. Use the heuristic ladder, strongest signal first:
   `resolution_ts` → market `status` (resolving/settling) → price convergence to ~0/1 that
   stays → category-specific event-time overrides. **Log and report the exclusion rate.**
   *Why:* this is the single most important reviewer-defense line — excluding trivially
   known outcomes is what makes EventX measure *non-trivial* prediction.

## C. Measurement mechanics

7. **Trade history is retained only for a recent rolling window (~6 weeks); older intraday
   data exists ONLY as candles.** Verified 2026-07-04: on Polymarket, markets with real
   daily-candle volume back to 2025-07 return **zero** trades before a hard ~2026-05-21
   wall (the `to` cursor works — the trades simply are not retained). Kalshi shows the same:
   no trades reachable before 2025 on any market. So:
   - **Recent window (within retention):** reconstruct bars from trades (finest, true
     microstructure), and validate the reconstruction against `/candles` on the overlap.
   - **Historical window (2025 and earlier):** trades do not exist — you must fall back to
     the candle endpoint (`bucket_ts, open/high/low/close, volume`). Daily reaches back
     furthest; hourly (60m) → ~7 months; 15m is row-capped at 5000; 1m/5m are recent-only.
   Treat the retention boundary as a **granularity seam** and document it; never assume a
   uniform trade-reconstructed bar exists across the full study window.
   *Why:* the plan assumed trades go back to 2020 and candles are the short/validation-only
   source — the API is the reverse. Silently pulling `/trades` for a 2025 window yields
   empty pages, not an error, and would drop the entire historical spine without warning.
8. **Work in log-odds space** `y = ln(p/(1−p))` with `[ε, 1−ε]` clipping; detect jumps with
   an adaptive threshold `k · rolling σ(Δy)`.
   *Why:* a 0.02→0.05 move is large in odds but tiny in raw price — a fixed raw threshold
   masks it.
9. **Liquidity-gate on orderbook midprice** (minimum depth/notional and ≥ n distinct
   trades). In the historical window rely on **trade-based proxies** (trade count,
   notional, price dispersion) since L2 depth is sparse; record the gap as missingness.
   Exclude the terminal resolution-convergence window.
   *Why:* don't label a single stale print as an informative move.

## D. Inference discipline

10. **Causal-language discipline.** T3 estimates predictive value **conditional on
    observable news**, NOT the marginal causal effect of KOL posts. Name residual
    confounding — information surfacing first on unobserved channels (Telegram/Discord/
    Farcaster/livestreams), weak per-ticker sentiment in non-finance markets
    (politics/sports/legal/geopolitics), provider timestamp lag — as **limitations**,
    never eliminate it by wording.
11. **Block bootstrap, not DeLong**, for metric-delta CIs (moving-block over the test
    period). Apply **Benjamini–Hochberg FDR** to every per-KOL / per-market claim.
    **Null models are mandatory**: rebuild KOL features under (a) placebo timestamps and
    (b) shuffled tweet↔market assignment — the real ΔAUC/ΔBrier must beat both.
    *Why:* time series violate the i.i.d. assumption DeLong needs, and 33.9M tweets
    guarantee spurious topical matches near any jump.
12. **Category-stratified reporting.** Always report category composition and per-category
    performance; report headroom across horizons / categories / liquidity regimes.
    *Why:* results must not be silently driven by one dominant category (politics / crypto
    / sports depending on window).

## E. Release constraints

13. The public tier ships **tweet/news IDs, not raw text** (X ToS). Features/labels under a
    permissive data license (e.g. CC-BY); code under MIT/Apache. Keep the Rehydration-Track
    baseline **deliberately simple** (TF-IDF/BM25 + logistic, or embedding aggregation +
    GBM) — EventX is a benchmark, not an NLP-model paper.

---

When a guardrail conflicts with a quick fix, **the guardrail wins** — or stop and flag it.
For anything not covered here, read `research_plan.md` (the *why/what*) and
`implemenation_plan.md` (the *how*) at the repo root.
