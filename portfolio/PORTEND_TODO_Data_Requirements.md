# PORTEND TODO → Data Requirements & Processing Plan

## Purpose

This document maps **every TODO in the current PORTEND draft** to:

1.  What data is required
2.  Whether that data is already available
3.  Where it can come from
4.  What processing / derived features must be created
5.  What is a genuine blocker versus a design decision
6.  What the final output of that TODO should look like

The plan is based on the current PORTEND draft and the publicly
available Polymarket data interfaces.

> **Important:** The paper's central contribution is not simply
> downloading Polymarket data. The draft explicitly says the
> contribution is the transformation:
>
> `raw data → event-family grouping → typed relations → validity/provenance → constraints → synchronized L2 replay → simulator → splits → oracle protocol`
>
> So most of the work is **data curation and derived structure**, not
> raw-data collection.

------------------------------------------------------------------------

# 1. Executive Summary

The current data situation can be thought of as five layers:

  -----------------------------------------------------------------------
  Layer                   What we need            Status
  ----------------------- ----------------------- -----------------------
  Raw market data         Markets, outcomes,      🟢 Mostly available
                          timestamps, prices      

  Trading data            Trades, sizes, prices,  🟢/🟡 Available, but
                          direction, fees         needs validation

  Order-book data         Historical L2 snapshots 🔴 **Critical
                          / updates               question**

  Semantic structure      Event families,         🟡 Must be constructed
                          relations, constraints  

  Benchmark               Beliefs, simulator,     🔴 Must be built
  infrastructure          splits, metrics,        
                          experiments             
  -----------------------------------------------------------------------

The biggest potential blocker is **historical L2 order-book data**.

Current Polymarket APIs can provide market metadata, current order
books, prices/price history and public trade information, but a
historical benchmark needs to know the **book that existed at the exact
simulated decision timestamp**. A current `/book` response is not enough
for that.

The PORTEND paper itself requires L2 snapshots and uses them to replay
taker execution.

------------------------------------------------------------------------

# 2. What PORTEND Actually Needs

The paper describes six core dataset tables:

1.  Contracts
2.  Book
3.  Trades
4.  Settlement
5.  Relations
6.  Compiled constraints

It also requires additional benchmark-layer data:

7.  Point-in-time beliefs
8.  Joint distributions over feasible settlements
9.  Event-family grouping
10. Decision timestamps / replayable windows
11. Split assignments
12. Scenario labels

The paper defines the feasible settlement set as:

`Y_t = { y ∈ {0,1}^{n_t} : A_t y = b_t, C_t y ≤ d_t }`

This means that relations must eventually become machine-readable
constraints.

------------------------------------------------------------------------

# 3. Raw Data We Should Build First

## 3.1 Market Metadata

### Required fields

  Field                Why
  -------------------- -------------------------------------
  market_id            Stable market identifier
  condition_id         Link to settlement / on-chain data
  event_id             Group markets belonging to an event
  question             Contract semantics
  description          Relation discovery
  outcomes             Outcome labels
  token_id             Link to CLOB data
  creation_time        First clock
  start_time           Trading start
  end_time             Expected expiry
  closed_time          Market lifecycle
  resolution_time      Settlement clock
  active / closed      Lifecycle state
  category / tags      Domain statistics
  neg_risk             Execution / relation handling
  tick_size            Execution
  minimum_order_size   Execution
  fee information      Execution
  volume / liquidity   Coverage / filtering

### Availability

**Mostly available from Polymarket's Gamma market/event APIs.**

Polymarket's current API ecosystem separates market/event discovery from
CLOB trading data. Gamma provides market metadata and token identifiers;
CLOB provides order-book and price information.

### Processing needed

Create a normalized `markets` table.

Also create:

``` text
market_id
    ↓
event_id
    ↓
event_family_id
    ↓
token_ids
```

### Important

Do not treat the Gamma API's current state as historical state.

For example, a field such as current liquidity is useful for today's
market but does not automatically tell us the liquidity that existed six
months ago.

------------------------------------------------------------------------

# 4. Outcomes / Tokens

## Required table

### `outcomes`

  Field           Description
  --------------- ----------------------------------
  market_id       Parent market
  token_id        CLOB token
  outcome         YES / NO / named outcome
  outcome_index   Stable index
  outcome_type    Normal / Other / etc.
  valid_from      When outcome became valid
  valid_until     When outcome stopped being valid

### Availability

🟢 Market metadata gives the outcome labels and CLOB token IDs.

### Processing needed

Normalize the JSON/list fields into rows.

Example:

``` text
market_id | token_id | outcome
----------|----------|--------
123       | AAAAA    | YES
123       | BBBBB    | NO
```

For multi-outcome / NegRisk structures, do not blindly assume every
market is simply YES/NO.

------------------------------------------------------------------------

# 5. Historical Prices

## Required

For every token:

``` text
timestamp
token_id
price
```

Ideally:

``` text
timestamp
token_id
bid
ask
mid
last_trade_price
spread
```

### Availability

🟢 Historical price history is available through Polymarket's CLOB
price-history interface.

### Processing needed

Create a point-in-time price panel:

``` text
timestamp | market_id | token_id | price
```

Then align all markets to benchmark decision timestamps.

### Important distinction

A historical price series is **not a replacement for historical L2**.

Price tells us:

> "The market was around 0.63."

L2 tells us:

> "At that exact moment, there were 400 contracts available at 0.64, 800
> at 0.65, etc."

PORTEND's execution simulator needs the second.

------------------------------------------------------------------------

# 6. Historical L2 Order Books --- Biggest Data Requirement

## Required

At minimum:

``` text
timestamp
token_id
side
price
quantity
level
```

Example:

``` text
timestamp | token | side | price | quantity
----------|-------|------|-------|---------
12:00:01  | A     | bid  | 0.61  | 500
12:00:01  | A     | bid  | 0.60  | 900
12:00:01  | A     | ask  | 0.64  | 300
12:00:01  | A     | ask  | 0.65  | 700
```

### Why it is critical

The paper explicitly says that the simulator:

-   consumes displayed depth
-   applies fees
-   respects tick size
-   respects minimum order size
-   caps participation
-   replays historical execution

Therefore we need to know what was actually displayed at decision time.

### Availability

🟡/🔴 **Must be verified from our existing data.**

Polymarket's CLOB API can return current order books and related market
data, but a benchmark needs **historical replayable L2**.

Potential sources:

1.  Our own historical API collection
2.  Existing Polymarket historical datasets
3.  Third-party historical CLOB datasets
4.  Archived WebSocket/order-book updates
5.  Reconstructed books from message-level data

### Processing needed

If we have full book updates:

``` text
book updates
      ↓
reconstruct order book
      ↓
periodic snapshots
      ↓
decision-time L2
```

If we only have snapshots:

``` text
raw snapshots
      ↓
normalize
      ↓
timestamp
      ↓
validate
      ↓
store
```

### Blocker

**If we do not have historical L2, the full PORTEND execution benchmark
cannot be reproduced faithfully.**

------------------------------------------------------------------------

# 7. Trades

## Required

  Field                      Purpose
  -------------------------- ----------------------------
  timestamp                  Match trade to L2
  token_id                   Contract
  market_id / condition_id   Market
  price                      Execution price
  size                       Execution quantity
  side                       Buy/sell
  aggressor direction        Simulator validation
  transaction hash           Deduplication / provenance
  block number               On-chain ordering
  fee                        Net performance
  trade ID                   Deduplication

### Availability

🟢/🟡

Polymarket's Data API exposes public trade information, and on-chain
data can provide a stronger source for historical execution and
direction.

### Processing needed

We need to determine whether our current trade dataset contains:

-   actual executions
-   trade size
-   timestamp
-   direction
-   fees
-   market/token IDs

If direction is absent, derive it from the strongest available source
rather than using a weak price-based heuristic.

### Final table

`trades.parquet`

------------------------------------------------------------------------

# 8. Settlement Data

## Required

  Field              Purpose
  ------------------ ------------------
  market_id          Contract
  token_id           Outcome
  settlement_value   0 or 1
  resolution_time    Settlement clock
  winning_outcome    Ground truth
  oracle             Provenance
  transaction hash   Verification

### Availability

🟢/🟡

Polymarket settlement can be reconstructed from public on-chain
information.

### Processing needed

Create a clean settlement table:

``` text
market_id
outcome
settlement_value
resolution_time
```

Then build:

``` text
market_id → settlement_time → winning outcome
```

### Critical rule

A settlement outcome must only become available to a model **after the
settlement actually happened**.

This is required to prevent look-ahead leakage.

------------------------------------------------------------------------

# 9. Event Families

This is where raw Polymarket data stops being enough.

## What is an event family?

An event family groups contracts that describe different outcomes of the
same underlying real-world event.

Example:

``` text
US Election 2028
├── Candidate A wins
├── Candidate B wins
├── Candidate C wins
└── Other
```

### Required table

`event_families`

  Field                 Purpose
  --------------------- -------------------------------------------
  event_family_id       Group ID
  market_id             Member market
  family_type           Election / sports / macro / crypto / etc.
  description           Human-readable semantics
  valid_from            Family validity
  valid_until           Family validity
  provenance            Why grouped
  verification_status   Audited / automatic

### Availability

🟡 Polymarket gives event/market groupings, but **PORTEND's
benchmark-level event families require curation**.

### Processing needed

``` text
market metadata
+ question
+ description
+ event metadata
        ↓
candidate grouping
        ↓
manual / automated verification
        ↓
event_family_id
```

------------------------------------------------------------------------

# 10. Typed Relations

This is one of the largest pieces of new work.

The paper expects relations such as:

-   complement
-   exclusive
-   exhaustive
-   monotone
-   implication

### Required table

`relations`

  Field                 Example
  --------------------- ---------------------
  relation_id           R123
  market_A              M1
  market_B              M2
  relation_type         implication
  event_family_id       F44
  provenance            rule / LLM / manual
  validity_start        timestamp
  validity_end          timestamp
  verification_status   verified
  constraint_id         C19

### Availability

🔴 **Not a raw Polymarket field.**

The paper explicitly treats relation extraction/curation as part of the
contribution.

### Processing needed

``` text
market questions
      ↓
candidate relation discovery
      ↓
relation classifier / rules
      ↓
human audit
      ↓
validity checking
      ↓
typed relation graph
```

### Important

Do **not** define relations merely because prices look correlated.

The paper explicitly separates:

> relation validity

from

> price consistency

A relation should come from contract semantics and venue mechanics, not
from historical price correlation.

------------------------------------------------------------------------

# 11. Relation Audit --- TODO

The paper currently has a TODO to:

-   report precision by relation type
-   use a hand-audited sample
-   run a signed-graph frustration check

## Data required

We need:

``` text
candidate relations
+
human labels
+
relation type
+
validity status
+
settlement outcomes
```

### Processing

Sample relations by type:

``` text
Complement
Exclusive
Exhaustive
Monotone
Implication
```

Have humans label:

``` text
VALID
INVALID
AMBIGUOUS
```

Then calculate:

``` text
precision(type)
precision(overall)
```

### Additional feature

Create a graph:

``` text
market A ──relation──> market B
```

Then run graph consistency checks.

------------------------------------------------------------------------

# 12. Mutable "Other" Outcomes --- TODO

The paper specifically calls out NegRisk "Other" outcomes whose meaning
may change as markets evolve.

## Required data

``` text
market_id
outcome
timestamp
valid_from
valid_until
market description
event description
resolution
```

## Processing

Two possible approaches:

### Option A --- Exclude

Remove mutable `Other` contracts from relation-dependent experiments.

### Option B --- Time-scope

Represent their meaning explicitly:

``` text
Other@t1
Other@t2
```

with validity intervals.

### Recommendation

For v1, **exclude ambiguous/mutable Other outcomes from
relation-dependent benchmark slices unless their semantics can be proven
stable**.

------------------------------------------------------------------------

# 13. Compiled Constraints

The paper's relations eventually become:

``` text
A_t y = b_t
C_t y <= d_t
```

## Required input

``` text
typed relations
+
event families
+
validity intervals
```

## Processing

Example:

### Exclusive + exhaustive family

If:

``` text
A
B
C
```

are mutually exclusive and exhaustive:

``` text
A + B + C = 1
```

becomes:

``` text
A_t y = b_t
```

### Implication

If:

``` text
A → B
```

then:

``` text
A <= B
```

becomes:

``` text
C_t y <= d_t
```

### Output

A machine-readable constraint object:

``` text
constraint_id
timestamp
variables
A
b
C
d
source_relation_ids
```

This is a **derived dataset**, not something we download.

------------------------------------------------------------------------

# 14. Joint Beliefs --- Major Derived Feature

This is another major part of PORTEND.

The benchmark must fix beliefs so allocators are compared on allocation,
not forecasting.

The paper requires a distribution:

``` text
π_t ∈ Δ(Y_t)
```

over feasible settlement vectors.

## Raw data needed

At decision time `t`:

``` text
market prices
+
market relations
+
feasible settlement set
```

## Processing

The paper proposes a canonical market coupling:

``` text
market-implied marginals
        ↓
constraints Y_t
        ↓
maximum-entropy joint distribution
        ↓
π_market
```

### Important

Price data alone gives marginal probabilities.

It does **not** give the full joint distribution.

Therefore we must construct:

``` text
prices → q_t
q_t + Y_t → π_t
```

### Output

``` text
timestamp
joint_distribution_id
market_ids
marginal_probabilities
sampling_method
seed
```

For large components, the paper proposes a standardized Monte Carlo
sampler.

------------------------------------------------------------------------

# 15. Alternative / Calibrated Beliefs

The paper also refers to multiple belief ladders / oracle variants.

We therefore need:

``` text
S_mkt
S_cal
S_mod
S_epsilon*
```

or whatever final naming is adopted in the completed paper.

## Data required

Historical:

``` text
market-implied probabilities
+
event settlements
+
decision timestamps
+
relation constraints
```

## Processing

Build a calibration process that uses only information available at
timestamp `t`.

For example:

``` text
historical market probability
        ↓
calibration model
        ↓
calibrated probability
        ↓
joint-distribution construction
```

### Critical

Do not train calibration using future settlements that were not known at
the simulated decision time.

------------------------------------------------------------------------

# 16. Equal-Edge / Participation TODO

The paper contains TODOs around the equal-edge ladder and participation
cap.

These are mostly **benchmark design decisions**, not missing raw data.

## Data required

For participation:

``` text
L2 depth
+
trade size
+
bankroll
+
minimum order size
+
tick size
```

## Derived feature

Define:

``` text
max_order_size
=
participation_cap × displayed_depth
```

Example:

``` text
Displayed ask depth = 10,000
Participation cap = 5%

Maximum simulated purchase = 500
```

The exact cap must be fixed before results are generated.

------------------------------------------------------------------------

# 17. Execution Simulator

This is not a downloaded dataset.

It is a software component built from the data.

## Inputs

``` text
decision timestamp
+
portfolio state
+
order
+
historical L2
+
fees
+
tick size
+
minimum size
+
collateral rules
```

## Processing

For a marketable order:

``` text
order
 ↓
find decision-time L2
 ↓
consume available levels
 ↓
apply participation cap
 ↓
calculate VWAP
 ↓
calculate fee
 ↓
lock collateral
 ↓
update portfolio
```

### Output

``` text
fills
execution_price
filled_quantity
slippage
fees
locked_collateral
remaining_cash
```

### Scope

The paper explicitly limits the canonical simulator to:

-   taker orders
-   marketable-limit orders

It does **not** claim to simulate maker queue priority.

------------------------------------------------------------------------

# 18. Simulator Validation --- TODO

This TODO requires both:

1.  Historical L2
2.  Actual observed trades

The paper proposes:

``` text
observed aggressive trade
        ↓
latest pre-trade L2
        ↓
simulated fill
        ↓
compare with observed fill
```

## Metrics

  Metric              Meaning
  ------------------- -------------------------------
  VWAP error          Did simulated price match?
  Fill-size error     Did simulated quantity match?
  Price-level error   Did simulated levels match?
  Fee error           Did fee reconstruction match?

Break results down by:

-   liquidity bucket
-   trade size
-   participation
-   category

### Output

A simulator validation report.

### Blocker

**Do not generate reference allocator results until this validation is
done.**

------------------------------------------------------------------------

# 19. Ruin Barrier --- TODO

The paper says the log-growth objective becomes undefined when wealth
reaches zero.

Therefore a fixed ruin barrier is required.

## Data required

No new raw data.

## Design decision

Choose:

``` text
ruin_threshold = ε
```

For example:

``` text
W_t <= ε × W_0
```

defines ruin.

The exact value must be chosen **before** running the reference
experiments.

------------------------------------------------------------------------

# 20. Episode Definition --- TODO

Again, this is primarily a design decision.

## Data required

``` text
decision timestamps
+
market opening/closing times
+
settlement times
+
event families
```

## Possible episode

``` text
episode = fixed temporal window
```

or

``` text
episode = event-family block
```

The paper wants ruin frequency over resampled episodes rather than a
single deterministic path.

### Output

``` text
episode_id
start_time
end_time
event_family_ids
eligible_markets
```

------------------------------------------------------------------------

# 21. Train / Validation / Test Splits

The paper warns that a simple chronological split can leak information.

## Required data

``` text
creation_time
decision_time
settlement_time
event_family_id
```

## Processing rules

For every feature:

``` text
feature(t)
```

must only use information available at `t`.

Also:

-   related contracts should not be split across train/test
-   event families should be grouped
-   settlement labels only become usable after settlement
-   embargo should operate at event-family level

### Derived table

``` text
market_id
event_family_id
split
split_start
split_end
embargo_until
```

------------------------------------------------------------------------

# 22. Live Track --- TODO

The paper currently leaves the live-track mechanism open.

## No major raw-data blocker

This is primarily a protocol decision.

Two options:

### Option A --- Prospective containers

Participants submit strategy containers that execute prospectively.

### Option B --- Private historical window

Keep a genuinely unseen historical period.

### Recommendation

Do not implement the live track until the offline benchmark is stable.

------------------------------------------------------------------------

# 23. Dataset Statistics --- TODO

The paper currently has a large TODO table.

## Statistics we need

  Statistic                 Data required               Processing
  ------------------------- --------------------------- -----------------------
  Contracts                 markets                     count
  Usable contracts          markets + L2 + settlement   eligibility filter
  Relations                 relation table              count by type
  Event families            event-family table          count
  Time span                 timestamps                  min/max
  L2 snapshots              L2                          count
  L2 gaps                   L2 timestamps               gap analysis
  Trades                    trades                      count
  Trade notional            price × size                aggregate
  Trade size distribution   trades                      quantiles
  Domain distribution       categories/tags             histogram
  Horizon distribution      creation/settlement         duration
  Relation coverage         relation graph              fraction of contracts
  Replayable coverage       L2 + decision times         fraction
  Missingness               all tables                  field-level report
  Dataset size              files                       GB
  License                   source metadata             legal verification

------------------------------------------------------------------------

# 24. Replayable Coverage

This deserves special attention.

The paper defines replayable coverage as the share of decision
timestamps for which a valid book exists.

## Required

``` text
decision timestamps
+
historical L2
```

## Processing

For every decision time:

``` text
Is there a valid L2 snapshot?
```

Then:

``` text
replayable_coverage
=
valid_decision_times / total_decision_times
```

Report this prominently.

A huge dataset with poor L2 coverage is not a useful execution
benchmark.

------------------------------------------------------------------------

# 25. Effective Sample Size --- TODO

The paper says contract count is misleading because contracts in the
same event move together.

## Required

``` text
event_family_id
+
temporal blocks
+
performance observations
```

## Processing

Estimate effective sample size at the event-family / block level rather
than simply:

``` text
N = number of contracts
```

Also use event-block bootstrap intervals for strategy comparisons.

------------------------------------------------------------------------

# 26. Five Benchmark Scenarios

The paper proposes five scenarios.

  Scenario   Main data requirement                  Main derived feature
  ---------- -------------------------------------- ---------------------------------
  Term       long-duration contracts + settlement   maturity / lockup
  Simplex    exclusive event families               equality constraints
  Ladder     ordered outcomes                       inequality constraints
  Churn      short-duration contracts               high-frequency decision windows
  Open       complete live book                     full benchmark

## Term

Need:

``` text
creation
+
decision
+
settlement
+
prices
+
collateral lockup
```

Derived:

``` text
time_to_settlement
```

The paper also wants raw and discount-adjusted results.

------------------------------------------------------------------------

## Simplex

Need:

``` text
event families
+
exclusive/exhaustive relations
+
L2
+
prices
```

Derived:

``` text
Σ y_i = 1
```

------------------------------------------------------------------------

## Ladder

Need:

``` text
ordered outcomes
+
market semantics
+
relations
```

Derived:

``` text
P(X <= k)
```

or equivalent cumulative constraints.

------------------------------------------------------------------------

## Churn

Need:

``` text
high-frequency markets
+
timestamps
+
L2
+
trades
+
settlements
```

Derived:

``` text
time_to_resolution
rebalance opportunities
turnover
fees
```

The paper explicitly keeps five-minute Bitcoin contracts as an
adversarial slice rather than silently deleting them.

------------------------------------------------------------------------

## Open

Need everything.

This becomes the headline benchmark.

------------------------------------------------------------------------

# 27. Stress Slices

The paper wants scheduled-event windows.

## Required data

``` text
market/event timestamps
+
external release calendar
```

Potential event categories:

-   elections
-   macro releases
-   scheduled announcements
-   major sports events

## Processing

Define event windows **from actual calendars**, not manually after
looking at results.

Example:

``` text
T_release - 24h
        ↓
release
        ↓
T_release + 24h
```

The exact window must be fixed before evaluation.

------------------------------------------------------------------------

# 28. Reference Results --- TODO

The paper currently has placeholders for the allocator × oracle ×
scenario × bankroll grid.

## Raw data required

Everything above.

## Additional software required

Implement:

1.  Cash / no-trade
2.  Equal-weight positive-EV
3.  Capped fractional Kelly
4.  Relation-aware Kelly
5.  Executable-arbitrage LP
6.  Adapted EG / OLMAR
7.  Learned allocator

## Output per run

``` text
allocator
oracle
scenario
bankroll
episode
terminal_wealth
log_growth
fees
turnover
slippage
drawdown
capital_efficiency
utilization
concentration
ruin
sleeping_regret
```

------------------------------------------------------------------------

# 29. Adaptation Rules --- TODO

The paper says the adaptation rules themselves are part of the
contribution.

This does not require additional raw data.

It requires a precise specification for each allocator:

``` text
inputs
decision rule
constraints
position limits
rebalance frequency
risk limits
fee handling
execution handling
relation handling
```

These rules must be frozen before running results.

------------------------------------------------------------------------

# 30. H1 / H2 / H3 Experiments

The paper proposes three hypotheses.

### H1

Mean-reversion methods lose to naive baselines after fees and lockup.

### Required data

``` text
prices
+
L2
+
fees
+
collateral
+
settlements
```

------------------------------------------------------------------------

### H2

A recalibrated oracle may be profitable gross but not net.

### Required

``` text
market probabilities
+
settlements
+
fees
+
execution
```

------------------------------------------------------------------------

### H3

Allocator choice matters more once oracle error is sufficiently small.

### Required

A controlled oracle-quality ladder:

``` text
high-quality beliefs
↓
moderately noisy beliefs
↓
highly noisy beliefs
```

Then evaluate allocator performance at each level.

------------------------------------------------------------------------

# 31. ε-Sweep

The paper wants an estimate of a threshold `ε₀` where allocation skill
starts dominating forecast error.

## Required

``` text
oracle quality parameter ε
+
allocator results
```

## Processing

Run:

``` text
ε = 0
ε = small
ε = medium
ε = large
...
```

Measure:

``` text
performance variance attributable to allocator
vs.
performance variance attributable to belief error
```

This is an experiment, not a new raw-data requirement.

------------------------------------------------------------------------

# 32. Tweets

We already have tweets, but there is an important distinction.

## Tweets are NOT required for the core PORTEND allocation benchmark.

PORTEND deliberately supplies beliefs so forecasting is held fixed.

Tweets become useful if we want to:

1.  Generate beliefs ourselves
2.  Build a forecasting model
3.  Create a richer oracle
4.  Study how information affects allocation

## Required tweet fields

  Field             Purpose
  ----------------- -----------------------------
  tweet_id          identifier
  timestamp         point-in-time alignment
  text              content
  author            optional aggregated feature
  engagement        optional signal
  market_id         mapping
  event_family_id   mapping
  embedding         semantic signal
  sentiment         optional
  topic             optional

### Processing

``` text
tweets
 ↓
timestamp filtering
 ↓
market/event matching
 ↓
feature extraction
 ↓
belief model
 ↓
probabilities
```

### Critical

Do not allow tweets posted after decision time `t` to influence beliefs
at `t`.

------------------------------------------------------------------------

# 33. Data We Already Have vs Data We Need to Build

## Likely already available

  Data                     Status
  ------------------------ ----------------------
  Tweets                   🟢 We have
  Market metadata          🟢 API
  Market outcomes          🟢 API
  Token IDs                🟢 API
  Current prices           🟢 API
  Historical prices        🟢/🟡 API / archives
  Public trades            🟢/🟡 API / on-chain
  Settlement information   🟢/🟡 on-chain

## Must be created / curated

  Component                       Status
  ------------------------------- -----------------------------
  Event families                  🟡 Build
  Typed relations                 🔴 Build
  Relation audit set              🔴 Build
  Relation validity intervals     🔴 Build
  Machine constraints             🔴 Build
  Joint beliefs                   🔴 Build
  Point-in-time oracle            🔴 Build
  Historical decision snapshots   🟡 Depends on L2
  Execution simulator             🔴 Build
  Simulator validation            🔴 Build
  Scenario labels                 🔴 Build
  Train/test splits               🔴 Build
  Episode definitions             🔴 Design
  Ruin barrier                    🔴 Design
  Reference results               🔴 Run after infrastructure

------------------------------------------------------------------------

# 34. The Most Important Missing Data

If we reduce the whole project to one question:

> **Do we have historical L2 order-book state at replayable
> timestamps?**

If YES:

We can realistically build the full PORTEND benchmark.

If NO:

We can still build:

-   market dataset
-   trade dataset
-   settlement dataset
-   relations
-   constraints
-   belief benchmark
-   price-based allocation benchmark

But we cannot honestly claim the full **historical executable portfolio
benchmark** described in the paper.

------------------------------------------------------------------------

# 35. Recommended Data Architecture

I would organize the project like this:

``` text
raw/
├── gamma/
├── clob/
├── trades/
├── settlements/
└── tweets/

normalized/
├── markets.parquet
├── outcomes.parquet
├── prices.parquet
├── trades.parquet
├── orderbook.parquet
└── settlements.parquet

curated/
├── event_families.parquet
├── relations.parquet
├── relation_audit.parquet
└── constraints.parquet

benchmark/
├── decision_times.parquet
├── beliefs/
├── joint_distributions/
├── scenarios.parquet
├── splits.parquet
└── episodes.parquet

simulation/
├── execution_engine/
├── fills/
├── simulator_validation/
└── portfolio_results/

reports/
├── dataset_statistics/
├── relation_audit/
├── simulator_validation/
└── benchmark_results/
```

------------------------------------------------------------------------

# 36. Recommended Build Order

Do NOT start with the allocators.

Build in this order.

## Phase 1 --- Raw ingestion

``` text
1. Markets
2. Outcomes
3. Prices
4. Trades
5. Settlements
6. Historical L2
7. Tweets
```

### Exit condition

We can reconstruct what the market looked like at a historical
timestamp.

------------------------------------------------------------------------

## Phase 2 --- Normalization

Create:

``` text
markets.parquet
outcomes.parquet
prices.parquet
trades.parquet
orderbook.parquet
settlements.parquet
```

### Exit condition

Every table joins through stable IDs.

------------------------------------------------------------------------

## Phase 3 --- Event structure

Build:

``` text
event_families
relations
relation_audit
constraints
```

### Exit condition

For every relation-dependent market:

``` text
market state → valid feasible settlement set Y_t
```

------------------------------------------------------------------------

## Phase 4 --- Point-in-time oracle

Build:

``` text
market marginals
        ↓
feasible set
        ↓
joint distribution
```

### Exit condition

Every allocator receives the **same beliefs** at each decision time.

------------------------------------------------------------------------

## Phase 5 --- Execution engine

Build:

``` text
historical L2
+
order
+
fees
+
limits
+
collateral
        ↓
simulated fills
```

### Exit condition

Simulator reproduces historical trades within acceptable error.

------------------------------------------------------------------------

## Phase 6 --- Benchmark protocol

Freeze:

``` text
ruin barrier
episodes
splits
scenarios
bankrolls
fees
participation cap
oracle variants
```

### Exit condition

No benchmark parameter changes after seeing final results.

------------------------------------------------------------------------

## Phase 7 --- Allocators

Only now run:

``` text
cash
equal-EV
Kelly
relation-aware Kelly
arbitrage LP
EG/OLMAR
learned allocator
```

------------------------------------------------------------------------

# 37. Final TODO Checklist

## Data acquisition

-   [ ] Market metadata
-   [ ] Outcomes / token IDs
-   [ ] Historical prices
-   [ ] Historical L2
-   [ ] Trades
-   [ ] Settlement
-   [ ] Fees
-   [ ] Tick sizes
-   [ ] Minimum order sizes
-   [ ] Tweets
-   [ ] External event calendars

## Curation

-   [ ] Event families
-   [ ] Typed relations
-   [ ] Relation provenance
-   [ ] Relation validity intervals
-   [ ] Relation audit
-   [ ] Mutable `Other` handling
-   [ ] Compiled constraints

## Benchmark construction

-   [ ] Decision timestamps
-   [ ] Point-in-time beliefs
-   [ ] Joint distributions
-   [ ] Oracle variants
-   [ ] Scenario definitions
-   [ ] Episode definitions
-   [ ] Train/test split
-   [ ] Event-family embargo
-   [ ] Ruin barrier

## Execution

-   [ ] L2 replay
-   [ ] Taker execution
-   [ ] Fees
-   [ ] Tick size
-   [ ] Minimum order size
-   [ ] Participation cap
-   [ ] Collateral lockup
-   [ ] Fill generation
-   [ ] Slippage calculation

## Validation

-   [ ] Simulator vs observed trades
-   [ ] VWAP error
-   [ ] Fill-size error
-   [ ] Price-level error
-   [ ] Fee reconstruction error
-   [ ] Relation precision
-   [ ] Replayable coverage
-   [ ] Missingness

## Experiments

-   [ ] Term
-   [ ] Simplex
-   [ ] Ladder
-   [ ] Churn
-   [ ] Open
-   [ ] Stress slices
-   [ ] Relations ablation
-   [ ] Fee ablation
-   [ ] Depth ablation
-   [ ] Lockup ablation
-   [ ] ε sweep
-   [ ] H1
-   [ ] H2
-   [ ] H3

## Final paper

-   [ ] Dataset statistics
-   [ ] Effective sample size
-   [ ] Reference results
-   [ ] Adaptation rules
-   [ ] Limitations
-   [ ] License
-   [ ] Repository URL
-   [ ] DOI
-   [ ] Immutable dataset version
-   [ ] Datasheet
-   [ ] One-command reproduction

------------------------------------------------------------------------

# 38. Bottom Line

The project is **not primarily blocked by getting more Polymarket
prices**.

The difficult pieces are:

``` text
1. Historical L2
2. Event-family construction
3. Verified typed relations
4. Machine-readable constraints
5. Point-in-time joint beliefs
6. Execution simulator
7. Simulator validation
8. Leakage-safe benchmark protocol
```

The raw Polymarket APIs give us a substantial portion of the foundation:
Gamma for market/event metadata, CLOB for order-book and price
information, and Data API / on-chain sources for trades and related
data.

The research contribution starts after ingestion:

``` text
RAW POLYMARKET DATA
        ↓
NORMALIZATION
        ↓
EVENT STRUCTURE
        ↓
RELATIONS
        ↓
CONSTRAINTS
        ↓
POINT-IN-TIME JOINT BELIEFS
        ↓
L2 EXECUTION REPLAY
        ↓
VALIDATED SIMULATOR
        ↓
PORTFOLIO BENCHMARK
```

The **first thing I would verify before doing anything else is the
historical L2 question**. Everything downstream depends on whether we
can reconstruct the order book at historical decision times.

## Sources consulted

-   PORTEND draft: `event_portfolio_bench.pdf`
-   Polymarket Gamma market/event API
-   Polymarket CLOB API
-   Polymarket Data API
-   Public Polymarket/on-chain data sources and historical CLOB datasets
