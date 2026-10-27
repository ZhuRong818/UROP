# PORTEND — Executable Research Plan

This README turns the PORTEND paper into **six executable tasks**. The order is intentional: each task produces the inputs needed by the next one.

```text
Task 1: Raw market data
        ↓
Task 2: Event families + relations
        ↓
Task 3: Feasible outcomes + beliefs
        ↓
Task 4: Execution simulator
        ↓
Task 5: Benchmark protocol
        ↓
Task 6: Experiments + paper results
```

---

# Task 1 — Build the Raw Market Dataset

## Goal

Create one clean dataset containing everything needed to reconstruct what was available in the market at each historical decision time.

## Depends on

Nothing. This is the starting point.

## Exact data needed

| Data | Required information | Use |
|---|---|---|
| Market metadata | market ID, question, outcomes, creation, close, settlement | Define contracts and timelines |
| Outcome/token data | outcome ID/token ID, outcome name | Connect books, trades, and settlement |
| Historical L2 | timestamp, bid/ask prices, size at each level | Reconstruct executable prices |
| Trades | timestamp, price, size, side/aggressor if available | Validate execution and report activity |
| Settlement | final outcome, settlement time | Ground truth |
| Venue rules | fees, tick size, minimum size, collateral rules | Simulator |
| Source/license | source and redistribution terms | Reproducibility |

## What to do

1. Choose the venue and study period.
2. Download the raw data.
3. Standardize IDs and timestamps.
4. Join contracts, outcomes, books, trades, and settlements.
5. Remove duplicates and clearly corrupt records.
6. Record missing data explicitly.
7. Mark every timestamp for which a usable L2 book exists.

**Important:** historical L2 is required for the main replay benchmark. Historical prices alone are not enough.

## Output

```text
data/
├── contracts.parquet
├── outcomes.parquet
├── book_l2.parquet
├── trades.parquet
├── settlements.parquet
├── venue_rules.json
└── data_quality_report.json
```

Also create a market-level table containing:

```text
market_id
event_family_id
creation_time
close_time
settlement_time
number_of_outcomes
number_of_book_snapshots
number_of_trades
replayable_start
replayable_end
missingness
```

## Validation

- Every contract has a stable ID.
- Every settlement maps to a contract.
- Timestamps use one standard format.
- L2 timestamps can be ordered correctly.
- Missingness is measured.
- No future settlement information is attached to a decision timestamp.

## Paper output

Report:

- number of contracts
- number of event families
- number of L2 snapshots
- number of trades
- time span
- replayable coverage
- missingness
- domain distribution

---

# Task 2 — Build Event Families and Verify Relations

## Goal

Group contracts that describe the same underlying event and label the logical relationships between them.

## Depends on

Task 1.

## Exact data needed

Use from Task 1:

- contract question/text
- outcome names
- market ID
- creation/close/settlement times
- settlement result

Create:

```text
event_family_id
relation_id
relation_type
source_contract
target_contract(s)
valid_from
valid_to
provenance
extraction_method
verification_status
```

Required relation types:

- complement
- exclusive
- exhaustive
- monotone
- implication

## What to do

### 1. Group contracts

Example:

```text
Election X
├── Candidate A
├── Candidate B
└── Candidate C
```

These belong to one event family.

### 2. Add relations

Examples:

```text
YES + NO = 1              → complement
A + B + C = 1             → exclusive/exhaustive family
A implies B               → implication
Above 3% implies above 2% → monotone
```

### 3. Handle changing relations

A relation may only be valid during part of a market's lifetime. Store its validity interval.

For mutable `Other` outcomes, either exclude them or explicitly define when their meaning is valid.

## Golden dataset and human verification

Create a **human-verified golden set** covering all relation types. A few hundred to roughly 1,000 relations is a reasonable starting point.

For each relation, store:

```text
relation
relation_type
human_label
reason
```

Use this set to measure relation precision.

Human verification should be the reference standard for semantic correctness. Settlement outcomes can support the audit, but should not define whether a relation is logically valid.

## Output

```text
data/
├── event_families.parquet
├── relations.parquet
├── relation_golden_set.parquet
└── relation_audit_report.json
```

## Validation

Report:

- total event families
- total relations
- relations by type
- relation coverage
- human-audit precision by type
- percentage of relations that compile successfully

## Paper output

Include a compact table:

| Relation type | Count | Human precision |
|---|---:|---:|
| Complement | ... | ... |
| Exclusive | ... | ... |
| Exhaustive | ... | ... |
| Monotone | ... | ... |
| Implication | ... | ... |

Add a few clear examples in the appendix.

---

# Task 3 — Build Feasible Settlements and Common Beliefs

## Goal

For every decision time, define which combinations of future outcomes are possible, then provide the same belief input to every allocator.

## Depends on

Task 2.

## Exact data needed

From Task 1:

- market prices
- decision timestamps
- settlements

From Task 2:

- event families
- verified relations
- relation validity intervals

Create the constraint representation:

```text
A_t
b_t
C_t
d_t
```

The paper represents the feasible settlement set as:

```text
Y_t = { y ∈ {0,1}^n : A_t y = b_t, C_t y ≤ d_t }
```

The exact algorithm used to construct or solve this representation is your implementation choice.

## Probability-sum cases

Do not treat logically related contracts as independent probabilities.

Examples:

```text
Complement:
YES + NO = 1

Exclusive/exhaustive family:
A + B + C = 1

Ladder:
higher threshold implies lower threshold
```

Use the contract outcomes, event-family information, and verified relations from Task 2 to represent these cases.

**Do not solve the algorithm here. The requirement is to provide the correct data and constraints.**

## Belief data

Every allocator must receive the **same belief input** for a given decision time.

The benchmark should use a joint belief over feasible settlements, not independent probabilities for unrelated contract outcomes.

Create at least:

```text
S_mkt = market-based belief
S_cal = calibrated belief
S_mod = model-based belief
```

A controlled belief-quality sweep can be added later.

## Output

```text
beliefs/
├── market/
├── calibrated/
├── model/
└── belief_metadata.parquet
```

For each decision time store:

```text
timestamp
contracts
event_family_id
feasible_set_reference
belief_reference
```

## Validation

- Belief uses only information available at that time.
- Belief respects the feasible settlement structure.
- Every allocator receives the same belief.
- No future settlement information enters the belief.
- Missing relations are clearly marked.

## Paper output

Show one small example:

```text
Event: A / B / C

Market information: ...
Allowed outcomes: ...
Supplied joint belief: ...
```

This is enough to explain the idea without describing the implementation algorithm.

---

# Task 4 — Build and Validate the Execution Simulator

## Goal

Build a deterministic simulator that answers:

> If an allocator placed this order at this historical timestamp, what execution would it have received?

## Depends on

Task 1 and Task 3.

## Exact data needed

From Task 1:

- historical L2 snapshots
- historical trades
- fees
- tick size
- minimum order size
- collateral rules

From Task 3:

- contracts available at the timestamp
- feasible constraints
- settlement information

## Simulator scope

Support:

- taker orders
- marketable-limit orders
- displayed L2 depth
- fees
- tick size
- minimum order size
- collateral lockup
- participation cap

Do not claim maker-level queue simulation unless the data supports it.

## Simulator output

For every order:

```text
order_id
decision_time
contract_id
side
requested_size
executed_size
execution_price
fees
collateral_locked
```

For every portfolio state:

```text
timestamp
cash
locked_collateral
positions
portfolio_value
fees
turnover
```

## Validation

Use observed aggressive trades as the validation set.

For each observed trade:

1. Take the latest L2 snapshot before the trade.
2. Replay the trade through the simulator.
3. Compare simulated and observed execution.

Measure:

- VWAP error
- fill-size error
- price-level error
- fee reconstruction error

Report these by trade size and liquidity.

## Output

```text
simulator/
├── simulator.py
├── simulator_config.json
├── validation_results.parquet
└── validation_report.json
```

## Paper output

| Liquidity bucket | VWAP error | Fill-size error | Price-level error |
|---|---:|---:|---:|
| High | ... | ... | ... |
| Medium | ... | ... | ... |
| Low | ... | ... | ... |

If execution replay is unreliable for a particular market group, restrict the main benchmark to the reliable coverage and report the exclusion.

---

# Task 5 — Freeze the Benchmark Protocol

## Goal

Define exactly how experiments will run without information leakage.

## Depends on

Tasks 1–4.

## Exact data needed

Use:

- contracts
- event families
- relations
- settlements
- L2
- trades
- beliefs
- simulator
- timestamps

## 1. Create leakage-safe splits

The benchmark has three important clocks:

```text
creation
   ↓
decision
   ↓
settlement
```

Rules:

1. Features use only information available at decision time.
2. Contracts from the same event family stay in the same split.
3. Settlement labels become usable only after settlement.
4. Calibration cannot use future outcomes.
5. Use an event-family-level embargo around split boundaries.

## 2. Define the five scenarios

| Scenario | Main test |
|---|---|
| Term | Long collateral lockup |
| Simplex | Exclusive/exhaustive outcomes |
| Ladder | Ordered outcomes |
| Churn | Fast resolution and frequent trading |
| Open | Full changing market |

## 3. Define stress windows

Create windows around scheduled events using an external event/release calendar.

Define these windows **before** looking at experiment results.

## 4. Freeze experiment settings

Before the final run, fix:

- ruin barrier
- episode definition
- participation cap
- minimum order size
- fee treatment
- scenario definitions
- split dates
- stress-window rules

## Output

```text
benchmark/
├── splits.parquet
├── scenarios.json
├── stress_windows.parquet
├── benchmark_config.json
└── evaluation_protocol.md
```

## Paper output

### Split table

| Split | Dates | Event families | Contracts | Purpose |
|---|---|---:|---:|---|
| Train | ... | ... | ... | Calibration/model fitting |
| Validation | ... | ... | ... | Parameter selection |
| Test | ... | ... | ... | Final evaluation |

### Scenario table

| Scenario | Families | Contracts | Decision points | Replayable coverage |
|---|---:|---:|---:|---:|
| Term | ... | ... | ... | ... |
| Simplex | ... | ... | ... | ... |
| Ladder | ... | ... | ... | ... |
| Churn | ... | ... | ... | ... |
| Open | ... | ... | ... | ... |

---

# Task 6 — Run Baselines and Produce the Paper Results

## Goal

Run the complete benchmark and produce the results used in the paper.

## Depends on

Tasks 1–5.

## Input given to every allocator

At each decision time:

```text
available contracts
L2 book
belief
feasible constraints
cash
locked collateral
venue rules
```

No future settlement information is allowed.

## Baselines

Implement:

1. Cash / no-trade
2. Equal-weight positive-EV
3. Capped fractional Kelly
4. Relation-aware Kelly
5. Executable-arbitrage LP
6. Adapted EG / OLMAR
7. Learned allocator

Write down the exact rules for every baseline before the final experiment.

## Main experiment

Run:

```text
Allocator
× Belief condition
× Scenario
× Bankroll
```

## Metrics

Primary:

- net terminal wealth
- annualized log growth

Diagnostics:

- capital efficiency
- utilization
- maximum drawdown
- fees
- turnover
- realized slippage
- concentration
- sleeping regret
- ruin frequency

## Required ablations

Run the benchmark with and without:

- logical relations
- fees
- depth limits
- collateral lockup

For relation-dependent scenarios, compare:

```text
Relations supplied
vs.
Relations not supplied
```

## Belief-quality sweep

Run a controlled sweep from weaker to stronger belief quality:

```text
market belief
      ↓
small edge
      ↓
larger edge
      ↓
strong edge
```

The exact construction method is an implementation choice.

## Statistical testing

Do not treat individual contracts as independent samples.

Use event families or temporal blocks as the main inference unit.

Report:

- score differences
- rank differences
- event-block bootstrap intervals
- within-event variation
- across-event variation
- effective sample size

## Output

```text
results/
├── raw_results.parquet
├── summary_results.parquet
├── bootstrap_results.parquet
├── ablation_results.parquet
├── epsilon_results.parquet
└── figures/
```

## Paper output

### Dataset

| Statistic | Value |
|---|---:|
| Contracts | ... |
| Event families | ... |
| Relations | ... |
| L2 snapshots | ... |
| Trades | ... |
| Time span | ... |
| Replayable coverage | ... |

### Main benchmark

| Allocator | Market | Calibrated | Model | Controlled edge |
|---|---:|---:|---:|---:|
| Cash | ... | ... | ... | ... |
| Equal-weight | ... | ... | ... | ... |
| Kelly | ... | ... | ... | ... |
| Relation-aware Kelly | ... | ... | ... | ... |
| ... | ... | ... | ... | ... |

### Scenario results

| Allocator | Term | Simplex | Ladder | Churn | Open |
|---|---:|---:|---:|---:|---:|
| ... | ... | ... | ... | ... | ... |

### Ablations

| Removed condition | Change in performance |
|---|---:|
| Relations | ... |
| Fees | ... |
| Depth | ... |
| Lockup | ... |

---

# Research Quality Checklist

## Data

- [ ] Raw market data is stored.
- [ ] Historical L2 is available for evaluated timestamps.
- [ ] Trades are stored.
- [ ] Settlements are stored.
- [ ] Venue rules are documented.
- [ ] Missing data is reported.

## Relations

- [ ] Event families are defined.
- [ ] Relations are typed.
- [ ] Relations have validity intervals.
- [ ] Relation provenance is stored.
- [ ] Human-verified golden set exists.
- [ ] Relation precision is reported.
- [ ] Mutable `Other` outcomes are handled.

## Feasible outcomes

- [ ] Complements are represented.
- [ ] Exclusive/exhaustive families are represented.
- [ ] Ladders are represented.
- [ ] Implications are represented.
- [ ] Feasible settlements are machine-checkable.
- [ ] Supplied beliefs respect the feasible set.

## Simulator

- [ ] Taker execution works.
- [ ] Fees are applied.
- [ ] Depth limits are applied.
- [ ] Collateral lockup is applied.
- [ ] Participation cap is applied.
- [ ] Simulator validation is complete.
- [ ] Thin-liquidity failures are reported.

## Evaluation

- [ ] No future information leaks into decisions.
- [ ] Event families do not cross splits.
- [ ] Ruin barrier is frozen before experiments.
- [ ] Episode definition is frozen.
- [ ] Five scenarios are defined.
- [ ] Stress windows are fixed before results.
- [ ] Effective sample size is reported.

## Results

- [ ] Baseline rules are written down.
- [ ] Main results are complete.
- [ ] Scenario results are complete.
- [ ] Relation ablation is complete.
- [ ] Fee/depth/lockup ablations are complete.
- [ ] Belief-quality sweep is complete.
- [ ] Bootstrap intervals are reported.

---

# Final Dependency Chain

```text
TASK 1
Raw market data
    ↓
TASK 2
Event families + verified relations
    ↓
TASK 3
Feasible settlements + common beliefs
    ↓
TASK 4
Execution simulator + validation
    ↓
TASK 5
Leakage-safe benchmark protocol
    ↓
TASK 6
Baselines + experiments + paper results
```

## Definition of Done

Another researcher should be able to reproduce:

1. event families,
2. verified relations,
3. feasible settlement representation,
4. supplied beliefs,
5. historical execution,
6. five benchmark scenarios,
7. baseline results,
8. statistical intervals.

The final paper should answer one clear question:

> **When beliefs are held fixed, which allocation strategies work when event-market constraints, collateral lockup, fees, changing markets, and real execution are included?**

---

# FAQ — Understanding Tasks 1–4

This section explains the parts that are easiest to misunderstand when implementing PORTEND.

## FAQ 1 — Do we need a trading algorithm to get historical trades?

**No.** We do not need a trading algorithm to collect historical trades.

PORTEND is a benchmark. The allocator/trading strategy comes later. The dataset contains two different kinds of information:

1. **Historical L2 order books** — what the market looked like and what liquidity was available.
2. **Historical trades** — what actually happened in the market.

Think of it as:

```text
Historical market data
        |
        +-- Contracts
        +-- Outcomes
        +-- L2 order books
        +-- Historical trades
        +-- Settlements
        +-- Venue rules
                 |
                 v
          PORTEND benchmark
                 |
          Allocator makes decision
                 |
                 v
          Execution simulator
```

The allocator is **your benchmark participant**, not something you need before collecting the data.

Historical trades are mainly useful for **validating the execution simulator**. The L2 order book is what the simulator uses to answer questions such as:

> "If my allocator wanted to buy $100 worth of YES at this time, how much could it actually buy?"

---

## FAQ 2 — Is historical order-book depth the same thing as historical trades?

**No. They are different.**

### Historical order-book depth

This tells us what people **were willing to trade** at a particular moment.

For example, at 2:00 PM:

```text
ASK

$0.60 -> 100 YES available
$0.61 -> 200 YES available
$0.62 -> 500 YES available
```

This is historical L2 depth.

It tells us:

> "At that moment, there were 100 tokens available at $0.60, 200 at $0.61, and 500 at $0.62."

### Historical trades

This tells us what people **actually traded**.

For example:

```text
Time       Price     Quantity
2:00:03    $0.60       50
2:00:05    $0.60       50
2:00:10    $0.61      100
```

These are historical trades.

The relationship is:

```text
ORDER BOOK DEPTH
"What is available?"
        |
        | someone executes an order
        v
HISTORICAL TRADE
"What actually got traded?"
```

For PORTEND:

- **L2 depth -> build the simulator**
- **Historical trades -> validate the simulator**

So **depth is not historical trade data**. Depth is the available liquidity at a point in time; trades are the transactions that actually occurred.

---

## FAQ 3 — Where do venue rules come from?

Venue rules are simply the rules imposed by the exchange/market venue.

Examples include:

| Rule | Meaning |
|---|---|
| Fees | How much a trade costs |
| Tick size | Smallest allowed price increment |
| Minimum size | Smallest allowed order |
| Collateral rules | How much capital must be locked |
| Trading rules | What order types are allowed |

These come from the **venue's official documentation and relevant market/order-book data**. They do not come from a trading algorithm.

For a Polymarket implementation, collect the applicable rules for the exact venue/market period being benchmarked and save them with the dataset.

---

## FAQ 4 — What does "join contracts, outcomes, books, trades and settlements" mean?

It does **not** mean that everything has to become one giant table.

Different datasets can remain separate and be connected using their IDs and timestamps.

For example:

### Contracts

```text
market_id       question
M123            Will BTC exceed $100k?
```

### Outcomes

```text
market_id       outcome       token_id
M123            YES           T1
M123            NO            T2
```

### L2 book

```text
timestamp        token_id    side    price    size
14:00:00         T1          ask     0.60     100
14:00:00         T1          ask     0.61     200
14:00:00         T1          bid     0.59     150
```

### Trades

```text
timestamp        token_id    price    size
14:00:03         T1          0.60     50
```

### Settlement

```text
market_id       outcome       payout
M123            YES           1
```

The IDs connect the datasets:

```text
M123
 |
 +-- YES -> T1
 |          |
 |          +-- L2 book
 |          +-- historical trades
 |
 +-- NO -> T2
            |
            +-- L2 book
            +-- historical trades
```

So the goal is simply to make it possible to answer:

> Which contract/outcome does this book or trade belong to, what was the market state at that time, and what was the eventual settlement?

A clean relational structure is often better than one huge table. Useful keys include `market_id`, `token_id`, and `timestamp`.

---

## FAQ 5 — What is `relation_type`?

`relation_type` says **what logical relationship exists between contracts/outcomes**.

### Complement

Two outcomes are opposites.

```text
YES + NO = exactly one outcome
```

So:

```text
P(YES) + P(NO) = 1
```

### Exclusive

Two outcomes cannot both happen.

Example:

```text
Team A wins
Team B wins
```

They cannot both be true.

### Exhaustive

The listed outcomes cover all possibilities.

Example:

```text
A wins
B wins
C wins
```

Exactly one must happen, so:

```text
P(A) + P(B) + P(C) = 1
```

### Monotone

One outcome implies another because of an ordered threshold.

Example:

```text
BTC > $100k  ->  BTC > $90k
```

If BTC is above $100k, it must also be above $90k.

### Implication

More generally:

```text
A happens -> B must happen
```

The important point is that `relation_type` describes **why the two contracts are logically connected**.

---

## FAQ 6 — What are `source_contract` and `target_contract`?

They simply identify the contracts involved in a relation.

For example:

```text
source_contract = BTC > $100k
target_contract = BTC > $90k
relation_type   = implication
```

This means:

```text
BTC > $100k -> BTC > $90k
```

For relations involving several contracts, `target_contract(s)` can contain multiple targets.

---

## FAQ 7 — What is `extraction_method`?

`extraction_method` means:

> **How did we discover that these contracts are related?**

For example, a relation could come from:

### Venue metadata

The venue explicitly identifies the relationship or event grouping.

```text
extraction_method = venue_metadata
```

### Rule-based extraction

A deterministic rule identifies a relationship.

For example:

```text
BTC > $100k
BTC > $90k
```

A threshold rule can identify:

```text
BTC > $100k -> BTC > $90k
```

```text
extraction_method = rule_based
```

### Human annotation

A researcher reads the contracts and identifies the relationship.

```text
extraction_method = human_verified
```

### LLM-assisted extraction

An LLM proposes a relation and a human checks it.

```text
extraction_method = llm_assisted
```

The reason for recording this field is reproducibility: another researcher should know **where the relation came from**.

---

## FAQ 8 — What is `verification_status`?

This answers:

> **Do we trust this relation yet?**

For example:

```text
relation:
BTC > $100k -> BTC > $90k

extraction_method:
LLM

verification_status:
human_verified
```

Another relation might be:

```text
extraction_method:
rule_based

verification_status:
pending_review
```

This is important because automatic extraction can produce incorrect relations. The paper can then distinguish between:

- automatically proposed relations,
- human-verified relations,
- and relations that still need review.

---

## FAQ 9 — Why do we need a golden dataset for relations?

A **golden dataset** is a smaller set of relations that humans have carefully checked.

For example:

```text
Relation                    Human label

A -> B                       TRUE
C + D = 1                    TRUE
E -> F                       FALSE
G and H exclusive            TRUE
```

This gives us a trusted reference set.

We can then evaluate the automatic relation extraction against it.

For a research paper, this is much stronger than simply saying:

> "Our system found these relations."

Human verification provides a semantic reference standard. Settlement outcomes can help audit the data, but they should **not be used to define whether a logical relation is true**.

---

## FAQ 10 — What is a feasible settlement?

A feasible settlement is simply:

> **A combination of final contract outcomes that is actually possible.**

Suppose we have three contracts:

```text
A = Alice wins
B = Bob wins
C = Charlie wins
```

The event rule says:

> Exactly ONE person can win.

Therefore the possible final states are:

```text
[A=1, B=0, C=0]
[A=0, B=1, C=0]
[A=0, B=0, C=1]
```

These are the **feasible settlement states**.

But these are impossible:

```text
[A=1, B=1, C=0]  <- Alice and Bob both win
[A=0, B=0, C=0]  <- nobody wins
```

So conceptually:

```text
All possible combinations
          |
          | apply event rules
          v
Only combinations that can really happen
          |
          v
Feasible settlement states
```

---

## FAQ 11 — Why does PORTEND need feasible settlements?

Because the allocator should not be allowed to believe impossible combinations of outcomes.

Consider:

```text
A = BTC > $90k
B = BTC > $100k
```

The logical relationship is:

```text
B -> A
```

The possible states are therefore:

```text
A=0, B=0    BTC <= $90k
A=1, B=0    $90k < BTC <= $100k
A=1, B=1    BTC > $100k
```

But this is impossible:

```text
A=0, B=1   X
```

because BTC cannot be above $100k without also being above $90k.

So relations tell us what **valid beliefs** can look like.

---

## FAQ 12 — Where do the probability sums come in?

Suppose:

```text
A = BTC > $90k
B = BTC > $100k
```

The market might say:

```text
P(A) = 0.70
P(B) = 0.40
```

That is logically reasonable because:

```text
P(B) <= P(A)
```

But this would be logically inconsistent:

```text
P(A) = 0.40
P(B) = 0.70
```

because being above $100k implies being above $90k.

Similarly, for mutually exclusive and exhaustive outcomes:

```text
P(A) + P(B) + P(C) = 1
```

The exact computational method used to construct the joint belief is an **implementation choice**. The important research requirement is that the final belief respects the verified logical structure.

---

## FAQ 13 — What exactly do we do in Task 3?

Conceptually, Task 3 has four steps:

```text
Contracts
   +
Verified relations
   +
Event-family information
   +
Market probabilities/prices
        |
        v
Determine which final outcomes are possible
        |
        v
Represent those feasible final states
        |
        v
Construct a joint belief over those states
        |
        v
Give the SAME belief to every allocator
```

The key idea is:

> **PORTEND is not trying to give each allocator a different forecast.**

All allocators receive the same belief. The benchmark then asks:

> Given the same beliefs, who allocates capital better under realistic constraints and execution?

That is what makes PORTEND a portfolio-management benchmark rather than a forecasting benchmark.

---

## FAQ 14 — Where do we get the execution simulator from?

You do **not** need to find an existing trading simulator.

The PORTEND project needs to implement its own **execution simulator** as part of Task 4.

Think of it as a small virtual exchange that answers:

> "Given the historical order book and an allocator's order, what would actually have happened?"

For example, suppose the historical book at 2 PM was:

```text
ASK

$0.60 -> 100 YES
$0.61 -> 200 YES
$0.62 -> 500 YES
$0.63 -> 1,000 YES
```

The allocator says:

> Buy 1,000 YES.

The simulator walks through the available depth:

```text
100 @ $0.60
200 @ $0.61
500 @ $0.62
200 @ $0.63
```

So the allocator gets 1,000 tokens, but **not all at $0.60**.

The average execution price is therefore worse than the best displayed ask. This is the effect of consuming order-book depth.

---

## FAQ 15 — What information does the simulator use?

The simulator mainly uses information from Task 1 plus the benchmark rules.

### Historical L2 book

```text
Timestamp
Price
Side
Available size
```

This tells the simulator what liquidity was available.

### Venue rules

```text
Fees
Tick size
Minimum order size
Collateral requirements
Other applicable trading rules
```

These tell the simulator what trades are allowed and what they cost.

### Benchmark constraints

For example:

```text
Participation cap
Position limits, if defined
Capital available
```

The simulator then converts:

```text
Allocator decision
        |
        v
Execution against historical L2
        |
        v
Fees + collateral + constraints
        |
        v
Actual simulated fill
        |
        v
Updated portfolio state
```

---

## FAQ 16 — Why do we need historical trades if the simulator uses the order book?

Because historical trades are useful for **validation**.

Suppose our simulator says:

> "At 2 PM, an order of this size would have filled at this price."

We can compare the simulator's behavior with actual aggressive trades that occurred around that time.

Conceptually:

```text
Historical L2
      |
      v
Build simulator
      |
      v
Simulator predictions
      |
      v
Compare with historical trades
      |
      v
Check whether execution is realistic
```

Useful validation measurements include:

- VWAP error
- fill-size error
- price-level error
- fee reconstruction error

If the simulator performs poorly, we should not simply hide that result. We should either improve the execution model or restrict the benchmark to market conditions where the simulator is reliable.

---

## FAQ 17 — What is the complete intuition behind Tasks 1–4?

The four tasks answer four different questions:

```text
TASK 1
What did the market look like?
        |
        v
Contracts + outcomes + L2 + trades + settlements + venue rules

TASK 2
What logical relationships exist between contracts?
        |
        v
Complement / exclusive / exhaustive / monotone / implication

TASK 3
What final outcomes are actually possible?
        |
        v
Feasible settlement states + common beliefs

TASK 4
If an allocator trades, what would actually happen?
        |
        v
Execution simulator using historical L2
```

And importantly:

> **There is no trading algorithm required in Tasks 1–4.**

The portfolio allocators come later. PORTEND provides them with the same information and the same simulated market environment, then benchmarks how well they manage capital.
