# EventX: expanding into a paper-scale forecasting study

Prepared 24 October 2026. This is a feasibility and study-design proposal, not a completed data acquisition, frozen evaluation protocol, power calculation or promise of publication.

## Assessment

Yes. A larger study is feasible through a combination of historical order-book archives and prospective collection. The scientific question should be: **Which observable market states permit incremental short-horizon forecasting beyond persistence, and do those gains transfer to new dates and markets?**

Our current 6.27% conditional development MAE reduction is a hypothesis. It uses nine rows across three markets, with two changed targets on the same market five minutes apart. None of the 420 nominal model–segment combinations passed the earlier-window stability screen. Larger data must challenge the rule, not merely supply more opportunities to find another favorable slice.

This direction supports a market-microstructure forecasting paper. It does not establish the original project's incremental-news claim. A news contribution would require a separately specified comparison with reliable article/release evidence and information-availability clocks.

## Available expansion routes

| Route | Fit to this project | Immediate limitation |
|---|---|---|
| PMXT v2 archive | Closest documented candidate for reconstructing our imbalance and momentum inputs | Need an actual reconstruction, timestamp, gap and contract-status audit |
| Broad quote-snapshot dataset | Potential larger price/spread benchmark | Documented quote fields lack bid/ask sizes, so they cannot directly reproduce our imbalance feature |
| OpenMarket | External high-frequency comparison or separately designed replication | BTC 15-minute contracts do not fit our present 30-minute target |
| Our expanded prospective collector | Records availability and operational failures directly | Needs a reliable local host and staged capacity checks |

PMXT documents hourly Parquet files, source and exporter-receipt timestamps, initial book depth and subsequent updates. Its listed file sizes are 100–400 MB per hour. These are publisher descriptions, not our verified coverage. Direct documentation fetches timed out; its indexed documentation was readable. [PMXT schema](https://archive.pmxt.dev/docs/v2-data-overview).

The broad snapshot publisher reports hundreds of millions of quotes, but documents missing volume and a multi-day outage. Its published schema has bid/ask prices without their sizes. It is a candidate for a different feature set, not a drop-in replacement. [Publisher repository](https://github.com/DineshKumar8399/polymarket-orderbook-dataset).

OpenMarket reports 727 million rows and 54 observed Polymarket days, focused on BTC 15-minute contracts. It also reports a null out-of-sample forecasting result. That makes it useful related work, rather than evidence that more observations guarantee a gain. [Research paper](https://arxiv.org/abs/2607.26245).

Only documentation was inspected in this task. No external market-price partitions or settlement-label tables were downloaded, scored or admitted. Existing frozen studies and live services remain unchanged.

## Proposed scale and sampling

Start with **10–20 markets over a one-week pilot**. If coverage and reconstruction pass, target **50–100 contracts over 6–8 weeks**, with diversity across unrelated parent events and calendar dates. These are planning ranges, not established sample-size requirements.

At five-minute decisions, the theoretical range is:

- 50 contracts × 42 days × 288 grids = **604,800 scheduled observations**.
- 100 contracts × 56 days × 288 grids = **1,612,800 scheduled observations**.

This assumes constant enrollment throughout each period. Actual usable observations will be fewer after cold starts, expiry, missing data and quality checks. Millions of overlapping rows are not millions of independent observations. Track contracts, parent events, calendar blocks, changed-price episodes and segment occurrences separately.

The narrow macro enrollment previously screened 204 metadata records and produced only two additional longer-lived candidates. We should not assume 100 comparable macro contracts exist. A new cohort can include economics, longer-lived financial contracts and political/regulatory contracts, with results stratified by domain. Exclude contracts that expire before the forecast horizon; five- or 15-minute crypto contracts require their own shorter-horizon experiment.

Choose a new cohort using documented metadata and, if desired, activity measured strictly before enrollment. Use deterministic stratified sampling and retain the rejected-candidate ledger. Do not select contracts from subsequent forecast accuracy. Related thresholds from one event remain one family for splitting and inference.

## Four execution stages

### 1. Compatibility audit before bulk acquisition

Inventory available dates, schemas, file sizes and source rights. Freeze an allowlist outside protected or consumed evaluation scopes before reading price rows. Metadata/footer inspection comes first; do not download mixed outcome tables and filter protected examples afterward.

For a small permitted time/market sample, check:

- Exact condition and YES-token mapping, timestamp units and ordering.
- A valid initial book before applying incremental updates; deletion, duplicate and reconnect behavior.
- Best-side price/size consistency, crossed books, missing levels and unexplained sequence gaps.
- Whether source or historical metadata supports tradability and terminal-state decisions at each forecast time.
- Availability of a valid pre-decision history and 30-minute forward measurement.

An archive receipt timestamp describes that archive collector's access, not EventX's access at the time. Historical replay and new local collection must retain this distinction. An event stream also cannot inherit a polling-based freshness rule without checking whether silence means an unchanged book or missing capture. Any revised measurement policy needs its own version.

If historical activity/status proof is insufficient, either obtain it or define a separately scoped retrospective quote study. Do not present it as satisfying the current strict prospective eligibility policy.

### 2. Reproducible development panel

Process approved partitions incrementally with column projection and disk-backed storage; keep raw checksums and a normalized compact feature/target panel. First measure actual I/O and storage on the pilot. Avoid loading the full archive into memory or estimating storage from quote-row count alone.

Freeze 30 minutes as the primary horizon for this branch. If adding 5- or 15-minute targets, name them as separate secondary tasks in advance. Historical discovery should compare persistence, weighted midpoint, regularized regression, a modest nonlinear model and the conditional hurdle policy on identical eligible rows.

### 3. Segment discovery with protected evaluation

Discover segments in development data and preserve all trials. Use forward training windows with a gap sufficient to prevent overlapping training labels crossing into evaluation decisions. Fit representations, scaling and thresholds inside the training window.

Freeze the chosen segment, model, target, primary metric, missing-data treatment and stopping rule before a new evaluation period. Evaluate later dates and a separate set of event families; report both temporal transfer and market-family transfer. Do not repeatedly open a final test period while selecting segments.

### 4. Prospective confirmation and paper analysis

Keep the present two-market run as a feasibility check. Create a new, separately versioned cohort for broader confirmation after the pilot; do not enlarge the current run silently. Record predictions before outcomes and all abstentions or missed endpoints.

Report segment MAE/RMSE, segment coverage, and performance across the full eligible population with persistence outside the segment. Add per-market and per-period results. Include no-change cases; excluding them using the target would answer an easier, hindsight-selected question.

Choose a practically meaningful effect before final evaluation. Estimate required duration using pilot yield and simulations that preserve shared-event, calendar and overlapping-horizon dependence. Validate the inference procedure's coverage rather than treating every five-minute row as independent. No numeric power requirement has yet been established.

## Paper contribution and decision criteria

Working title: **When Can Prediction-Market Forecasts Beat Persistence? A Conditional Evaluation Across Market States.**

The contribution would be a reproducible dataset protocol, controlled conditional forecasting results, and an explanation of when gains appear or disappear. Logistic regression or gradient boosting alone is not algorithmic novelty. An archive's existence alone is not our dataset contribution; source auditing, benchmark construction and transparent evaluation would need to add value.

A convincing positive result needs a practically useful improvement on untouched future data, adequate segment coverage and changing-event yield, and stability beyond a single contract or date. Report uncertainty and the full-population effect. Statistical significance, if supported, does not establish executable trading profitability.

If gains disappear, a careful benchmark or measurement paper may still be possible, but publication is not guaranteed by dataset size. The next concrete deliverable is **an audited compatibility sample and dataset manifest**, followed by measured coverage and power estimates—not another search for a favorable final-test subset.
