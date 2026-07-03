# EventX (v4) — Artifact-Led Research Plan
## A leakage-safe benchmark for measuring incremental social-media information in prediction-market price discovery

> **Positioning (one line).** EventX is a benchmark for testing whether social-media signals contain incremental, point-in-time predictive information about prediction-market repricing after conditioning on observable news and microstructure.We're building EventX, a benchmark for measuring whether social-media signals from Key Opinion Leaders (KOLs) carry incremental, point-in-time predictive information about prediction-market price moves — after controlling for what's already observable in the news and in market microstructure.
The core question, stated cleanly: do KOL posts help predict prediction-market repricing beyond what news and price/liquidity data already tell you? Rather than the older, weaker framing ("which tweet caused this jump," which has no objective ground truth), we predict future repricing from information available at time t and measure the added value of KOL signals over a news baseline — a target that's objectively scorable against realized prices.
It's artifact-led: the main contribution is the reusable benchmark itself (linked KOL-tweet / news / trade-and-orderbook data over Kalshi and Polymarket, with fixed tasks, leakage-safe splits, baselines, and a two-track release), and the incremental-information result is the reference finding that shows the benchmark works. Three core tasks: predict jumps (T1), measure KOL value beyond news (T3, the spine), and localize where that signal lives across KOLs and categories (T5).

---

## 0. What changed (v4)

Builds on the v3 artifact-led structure; v4 applies five polish edits for reviewer-defense:
1. **C3 drops bare "venues"** (→ liquidity regimes) so localization isn't confused with the held-back T4 cross-venue task.
2. **"Repricing risk" is defined once** and tied to T1, so C2 and T1 stay consistent.
3. **Rehydration-Track baseline kept deliberately simple** (TF-IDF/BM25 or embedding aggregation), so the paper stays a benchmark, not an NLP-model paper.
4. **Resolution-leakage exclusion made explicit** — exclude windows where the outcome is already public or mechanically settled (the highest-value fix).
5. **Category composition + stratified evaluation** added, so results aren't driven by a single dominant category.

---

## 1. What EventX is

A leakage-safe benchmark linking a **curated KOL tweet archive**, **news with structured sentiment**, and **trade- and orderbook-level Kalshi + Polymarket data**, with objective prediction tasks, a fixed evaluation protocol, published baselines, and a two-track release.

**Why this is a benchmark, not a dataset dump** (the case D&B reviewers probe):
1. A **non-trivial, objectively scorable task** the community can iterate on.
2. A **rigorous protocol** foreclosing the usual financial-ML failure modes (look-ahead, overlap leakage, and resolution leakage).
3. **Baselines** that establish the frontier and, crucially, **leave measurable headroom** across horizons, categories, and liquidity regimes — demonstrating the benchmark is neither saturated nor trivially unsolvable.
4. A **reference finding** showing the benchmark separates weak from strong approaches.
5. **Genuine reusability and extensibility** via the two-track release below.

The release maps directly onto standard datasets/benchmarks evaluation criteria: accessibility, documentation, open tooling, impact, and ethics.

---

## 2. Contributions (hedged; artifact-first)

- **C1 (artifact).** We introduce EventX, a leakage-safe benchmark for measuring whether KOL social-media signals contain incremental information about prediction-market price discovery beyond news and market microstructure — with fixed splits, a documented evaluation protocol, baselines, and a two-track release.
- **C2 (reference finding).** We provide the first large-scale evidence, to our knowledge, on whether curated KOL signals improve prediction-market **jump / repricing-risk forecasting after controlling for observable structured news**.
- **C3 (localization).** We quantify where any signal concentrates — across KOLs, market categories, time horizons, and **liquidity regimes** — using out-of-sample lift and FDR-controlled influence estimates.
- **C4 (economic).** We assess economic significance through a **stylized, conservative** spread- and fee-aware backtest.

---

## 3. The benchmark contract (what a submission does)

- **Unit of prediction.** A (market, timestamp t) pair.
- **Inputs.** Only features constructible from information available **at or before t** (strict point-in-time). Released feature families: **KOL, news+sentiment, market microstructure**; **cross-venue features are included where matched markets exist but are not required for the core leaderboard.**
- **Target.** Realized price change over horizon Δ in **log-odds** space `y = ln(p/(1−p))`; binary jump label (T1) and signed/continuous Δy (localization).
- **Inclusion / resolution-leakage exclusion.** Drop (market, t) pairs where the outcome is already publicly known or mechanically incorporated into settlement, so the benchmark measures **non-trivial** prediction rather than trivially-known outcomes.
- **Horizons.** Δ ∈ {5m, 30m, 2h, 6h, 24h}.
- **Splits.** Temporal train / validation / test with an **embargoed future holdout**; **purged cross-validation** within train to kill overlap leakage from overlapping label windows.
- **Metrics.** AUC-PR, Brier, calibration; **ΔBrier / ΔAUC over the news baseline** (headline number); stylized economic net-of-cost return; FDR-controlled per-KOL lift.
- **Two tracks (comparability is within-track).**
  - **Feature Track.** Uses only the released precomputed features. Fully runnable by anyone; the reproducible core.
  - **Rehydration Track.** Users with tweet/news access rebuild representations under the *same* splits, labels, and metrics — the path for better text models. Ships with ≥1 **deliberately simple** raw-text baseline (e.g., TF-IDF/BM25 + logistic regression, or sentence-embedding aggregation + gradient-boosted trees) so the track is live, not notional — the goal is to show better representations *can* help, not to contribute a strong NLP model.
  - Leaderboard entries are compared **only within** their track, since the two have different input access.
- **Leaderboard protocol.** Fixed: splits, labels, metrics, per-track input set. Submitter-varied: model and feature engineering within the allowed inputs. Test labels withheld; anti-leakage rules stated.

---

## 4. Core task suite (trimmed)

- **T1 — Jump / early-warning prediction.** P(large repricing in [t, t+Δ]) from signals ≤ t, where **repricing risk** is defined as the probability of a large future movement in log-odds price over a fixed horizon Δ. Metrics: AUC-PR, Brier, calibration, lead time.
- **T3 — Incremental information content (the spine).** Nested ladder: market-only (b0) → +news (b1) → +KOL (b2) → full (b3). **KOL value = b2−b1 and b3−b1**, with significance. Headline result.
- **T5 — KOL influence ranking.** Rank KOLs by out-of-sample predictive lead; report temporal stability; **FDR control** across the 3,702-handle roster.

**Held back as follow-on papers (stated in the paper):** T2 return/direction forecasting; T4 cross-venue price discovery (Hasbrouck information share + KOL lead–lag — standalone-worthy); T6 wallet-level informed / smart-money flow (standalone-worthy).

---

## 5. Data & scoping

- **Venues / history.** Polymarket (trades from 2020-10) + Kalshi (candles from 2021-06). Polymarket *candles* are only ~7 months; **reconstruct bars from trade prints + orderbook midprice** for anything longitudinal.
- **Study window.** A dense, well-covered 12–18-month span with simultaneous KOL + news + PM coverage, justified explicitly; report coverage.
- **Signal families.** KOL tweets (roster-filtered), news + structured sentiment, microstructure (spread / depth / order-flow imbalance / open interest), and cross-venue matched pairs (feature only, per §3).
- **Frozen extract.** The API strips lineage and picks a canonical provider per surface, so **pin and version the exact rows used**; bulk-pull under the 100 req/min limit into local Postgres (already in place).

---

## 6. Methodology & rigor

- **Boundary-aware jumps.** Log-odds space; adaptive threshold `k · rolling σ(Δy)` so a 0.02→0.05 move (large in odds) isn't masked.
- **Liquidity-aware, not last-trade.** Define moves on orderbook midprice; require minimum depth/notional and ≥ n distinct trades to qualify as informative; exclude (or separately model) the terminal resolution-convergence window.
- **Resolution-leakage exclusion.** Beyond terminal convergence, exclude windows where the outcome is already publicly known or mechanically incorporated into settlement. The information may technically be available at *t*, but it is *trivial* signal that would inflate reported performance and misstate the benchmark's difficulty — so its exclusion is what makes EventX measure genuine prediction.
- **Leakage-safe evaluation.** Walk-forward splits; purged & embargoed CV; strictly point-in-time features.
- **Baseline ladder + null model.** b0→b3 plus placebo-timestamp and shuffled tweet↔market-assignment nulls (essential — 33.9M tweets guarantee spurious topical matches near any jump).
- **Economic significance (stylized).** A conservative spread/fee-aware backtest framed as an **economic-significance check** — does the statistical signal survive realistic-ish costs? — **not** a claim of a deployable trading strategy. Fill, slippage, and liquidity assumptions stated and kept conservative.
- **Multiple testing.** Benjamini–Hochberg FDR on all per-KOL / per-market claims.

**Causal-language discipline.** T3 estimates predictive value **conditional on observable news**, not the marginal causal effect of KOL posts. Residual confounding remains because information can (a) surface first on unobserved channels (Telegram, Discord, Farcaster, livestreams), (b) be captured poorly by per-ticker sentiment in non-finance markets (politics, sports, legal, geopolitics), or (c) be timestamped later by the provider than the KOL posted. Named as limitations, not eliminated.

---

## 7. Release, datasheet, licensing, maintenance

- **Two-track release.**
  - **Feature Track (reusable core):** precomputed features / embeddings + labels + splits + evaluation code + leaderboard. Runs the benchmark **without** the raw corpus or the source API — resolving both the redistribution constraint and the "requires private access" objection.
  - **Rehydration Track (extensibility):** raw tweet/news text via tweet-ID rehydration or an application process, where licensing allows, plus the ≥1 (deliberately simple) raw-text baseline. This is what keeps the benchmark useful for representation-learning advances after publication.
- **Datasheet (Gebru et al.).** Provenance, coverage, **category composition**, missingness, **deleted-tweet rate**, known biases, intended and out-of-scope uses.
- **Licensing.** Labels/features under a permissive data license (e.g., CC-BY); code under MIT/Apache; document upstream feed constraints.
- **Maintenance / versioning.** DOI'd versioned releases (e.g., Zenodo), a stated update cadence, and a named maintainer — pre-empting "will it rot?".

---

## 8. Reference finding (a result, not the thesis)

Run EventX and report: best baseline results per track, the **ΔBrier / ΔAUC of KOL-over-news**, where it concentrates (KOLs / categories / horizons / liquidity regimes), and stylized economic significance. Present **remaining headroom across horizons, categories, and liquidity regimes**, showing the benchmark is neither saturated nor trivially unsolvable. **Report category composition and stratified performance** so results are not driven by a single dominant category (prediction markets skew toward politics / crypto / sports depending on window). Frame all of this as *what EventX reveals with current methods and where the headroom is* — not the paper's central claim. Positive, limited, or null results are all publishable; the artifact stands on protocol, baselines, and release.

---

## 9. Ethics & responsible use

Address: potential misuse of a market-prediction benchmark (manipulation / front-running) and mitigations; KOL privacy (public handles only, no PII beyond public); dual-use framing; and a responsible-release statement covering the two-track access model.

---

## 10. Timeline (~6–7 months; start July 2026)

- **Jul (wk 1–3):** freeze extract + window; write the **benchmark contract** (including the resolution-leakage exclusion rule); label pipeline (logit space, liquidity-aware); datasheet v0.
- **Aug (wk 4–7):** Feature-Track pipeline (KOL / news / microstructure); leakage-safe splits; b0–b3 baselines for T1/T3; stand up ≥1 Rehydration-Track baseline.
- **Sep (wk 8–11):** reference finding — incremental-value + null tests + stylized backtest; eval harness + leaderboard.
- **Oct (wk 12–15):** T5 influence ranking + FDR; headroom + category-stratified analysis; event case studies.
- **Nov (wk 16–19):** package the artifact — two-track release, eval code, leaderboard, datasheet, licensing, Zenodo DOI; write-up.
- **Dec–Jan:** polish, internal review, responsible-release check; submit.

Strong submission lands around **Jan–Feb 2027**.

---

## 11. Venue strategy (artifact-led ordering)

1. **Best path — datasets/benchmarks tracks & data-science journals:**
   - **NeurIPS 2027 Evaluations & Datasets (~May 2027)** — welcomes datasets, benchmarks, evaluation protocols, tools, negative results, and critical analyses; fits the "artifact + reference finding" design. Comfortable for the timeline. *(2026 round closed May 6, 2026.)*
   - **KDD 2027 Datasets & Benchmarks, later cycle** — strong home, but the later-cycle date is **not confirmed** on the official 2027 D&B page (the 2026 track ran a February cycle; don't assume the same). **Verify before planning around it.**
   - **EPJ Data Science** (top journal pick; computational social science + large-scale measurement) or **ACM TKDD** (benchmark + mining methodology + evaluation harness) — rolling deadlines, reward the fuller artifact.
2. **Very good topical backup — ICWSM January round.** Full papers may be submitted in any round, but **posters/demos/datasets only in the third (January 15, 2027) round** — so an artifact/dataset-style ICWSM submission targets January.
3. **No longer the lead — ICWSM September finding-led paper.** Only if early results are surprisingly strong.

Also viable: **CIKM**; **Journal of Financial Data Science** if the economic layer grows into a first-class contribution. **WSDM 2027** full-paper deadline is mid-to-late August 2026 — too soon for the full artifact.

**Recommendation.** Anchor on **NeurIPS 2027 E&D (~May 2027)** or the **KDD 2027 D&B later cycle** once its date is confirmed, with **EPJ Data Science / ACM TKDD** as no-deadline fallbacks. ICWSM January is the topical backup.

---

## 12. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Reviewers question reusability (private API / non-redistributable data) | Feature-Track release runs the benchmark standalone |
| Benchmark can't reward better text models | Rehydration Track + ≥1 (simple) raw-text baseline; within-track comparison |
| Benchmark looks saturated or trivial | Report headroom + stratified performance across horizons / categories / liquidity regimes |
| Results driven by one dominant category | Report category composition; stratified evaluation |
| Look-ahead / overlap leakage | Purged & embargoed CV; point-in-time features |
| Resolution leakage (outcome already public / settled) | Exclude such windows from labels; measure non-trivial prediction only |
| Economic backtest overclaimed | Framed as stylized economic-significance check, conservative assumptions |
| Reproducibility (API strips lineage) | Frozen, versioned, DOI'd extract |
| Tweet-content redistribution (X ToS) | Feature/ID release; raw text only in Rehydration Track |
| "Will the benchmark rot?" | Versioning + update cadence + named maintainer |