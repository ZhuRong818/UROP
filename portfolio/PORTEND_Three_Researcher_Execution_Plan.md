# PORTEND — Three-Researcher Execution Plan

## Purpose of this document

This document turns the existing PORTEND research plan into a practical work plan for three researchers.

The goal is simple:

> Each researcher should have a clear research problem, know exactly what data is needed, know how to start without waiting for the other researchers, and know exactly what they must deliver for the final benchmark.

The three workstreams are:

- **R1 — Data Collection + Joint Probability**
- **R2 — Event Families + Relations + Ladder Constraints**
- **R3 — Execution Simulator + Market Rules**

The workstreams are designed to be independent during development. They will be connected only through a small, clearly defined interface and a final integration step.

---

# 1. Research Question of PORTEND

The current central question is:

> When beliefs are held fixed, which allocation strategies work when event-market constraints, collateral lockup, fees, changing markets, and real execution are included?

The project should not start with allocator experiments. The first job is to make sure the required data, market relations, probability construction, and execution rules are actually available and reliable.

---

# 2. The Main Idea Behind the Three-Way Split

The three researchers answer three different questions.

### R1 — What data do we have, and how do we build a valid joint belief?

R1 answers:

1. What historical data can we collect?
2. Can the data be joined correctly?
3. Can the data be used and released under its license?
4. Given market probabilities and logical constraints, how can we build one valid joint probability distribution?

### R2 — What logical relationships exist between markets?

R2 answers:

1. Which markets belong to the same event family?
2. Which outcomes imply other outcomes?
3. Which outcomes are mutually exclusive?
4. Which outcomes form ladders such as `BTC > 10k`, `BTC > 20k`, `BTC > 30k`?
5. What mathematical constraints should those relations create?

### R3 — What would actually happen if we traded?

R3 answers:

1. What were the trading rules at a given time?
2. Given a book and an order, what fills would occur?
3. What price, fee, and collateral cost would result?
4. Can the simulator reproduce observed aggressive trades well enough to use it in the benchmark?

---

# 3. Independence Rule

The three researchers should be independent during the development stage.

This does **not** mean that the work will never be combined.

It means:

> No researcher should stop working just because another researcher has not finished collecting the final dataset.

Each researcher must have a way to test their work using either:

- a small sample they can collect independently,
- synthetic data,
- hand-built examples,
- or a small public sample.

When R1 later produces the canonical dataset, R2 and R3 should run the **same tested code** on that real dataset. They should not redesign their methods at that point unless the real data reveals a genuine problem.

---

# 4. Common Rules for All Researchers

## 4.1 Work should be reproducible

Every result should have:

- the input data version,
- the code version,
- configuration values,
- the date of collection,
- and a short record of important decisions.

## 4.2 Do not silently repair difficult data

If something is missing, ambiguous, or contradictory:

- mark it as missing,
- quarantine it,
- or exclude it with a written reason.

Do not silently change the data so that the method works.

## 4.3 Keep raw data separate from processed data

Never overwrite raw files.

Recommended structure:

```text
PORTEND/
├── raw/
├── normalized/
├── curated/
├── r1_joint_probability/
├── r2_relations/
├── r3_execution/
├── benchmark/
├── results/
├── reports/
└── tests/
```

## 4.4 Shared data contract

The following fields are the minimum common language between the three researchers:

```text
Market
- market_id
- event_id
- condition_id
- title/question
- description
- start_time
- end_time/close_time
- resolution information

Outcome
- token_id
- market_id
- outcome_name

Trade
- token_id
- timestamp
- price
- size
- side

Book snapshot
- token_id
- timestamp
- bids
- asks

Settlement
- market_id
- resolved_outcome
- resolution_timestamp

Venue rule
- valid_from
- valid_to
- fee rule
- tick size
- minimum order size
- collateral rule
- other execution rules
```

This is a contract, not a requirement that all researchers use the same internal database.

---

# 5. R1 — Data Collection + Joint Probability

## R1 Main Objective

R1 has two connected but independently testable responsibilities:

### Responsibility A
Determine whether the data needed for PORTEND actually exists with enough historical coverage and usable rights.

### Responsibility B
Research how to build a valid joint probability distribution from market beliefs and the logical constraints supplied by R2.

R1 therefore owns the data feasibility gate and the joint probability module.

---

## R1-A. Data Feasibility

### R1-A-1. Start with a small pilot

Do not begin by downloading the entire market history.

Start with approximately **50–100 resolved markets**.

The sample should contain different types of markets, including:

- several domains,
- binary and multi-outcome markets,
- liquid and thin markets,
- short and long settlement periods,
- related markets that may form event families,
- and markets from different venue-rule periods if the final study period crosses a rule change.

The purpose is not to produce the research dataset yet.

The purpose is to answer:

> Can we actually obtain, join, timestamp, and legally use the data required for the final study?

---

### R1-A-2. Build a source list

For every required data field, record:

```text
Field:
Source:
URL/API/file:
Historical coverage:
Granularity:
Identifier available:
Timestamp available:
Collection method:
License/terms:
Can raw data be archived?
Can raw data be redistributed?
Can derived data be redistributed?
```

Do this before large-scale collection.

---

### R1-A-3. Identify all required data

At minimum, investigate the availability of:

1. market metadata,
2. event metadata,
3. outcome/token identifiers,
4. trade history,
5. settlement information,
6. price history if available,
7. full historical L2 if available,
8. venue-rule history,
9. timestamps precise enough for replay,
10. source and license information.

The most important question is **historical L2**. A current order-book API is not enough for a historical execution benchmark.

---

### R1-A-4. Test the joins

For every pilot market, try to build the following chain:

```text
Event
  ↓
Market
  ↓
Condition / stable market identifier
  ↓
Outcome / token
  ↓
Trades
  ↓
Settlement
  ↓
Historical book, if available
```

Record every failed join.

A successful API request does not mean that the data is usable. The join must work across the whole chain.

---

### R1-A-5. Check time correctness

For each source, determine:

- what the timestamp means,
- whether it is event time or collection time,
- its precision,
- whether timestamps are in the same time zone,
- whether duplicate timestamps occur,
- and whether the data can be sorted into a reliable decision-time sequence.

All normalized timestamps should use UTC, but raw timestamps should be retained.

---

### R1-A-6. Measure historical coverage

For candidate decision times, estimate:

```text
number of decision times
number with usable book
number with stale book
number with missing book
number with usable trade history
number that can be linked to settlement
```

Do this for at least two possible decision schedules.

The goal is to know how much of the proposed study period is actually replayable.

---

### R1-A-7. Licensing and release check

This should be treated as a research question, not an administrative task.

For every source determine:

- whether data can be used for academic research,
- whether it can be stored long term,
- whether it can be redistributed,
- whether derived tables can be redistributed,
- whether an archival DOI is possible,
- and whether special permission is required.

Do not assume that “publicly downloadable” means “freely redistributable.”

---

### R1-A-8. Produce the Scope A/B/C decision

At the end of the pilot, R1 must recommend one of:

**Scope A — Full historical executable benchmark**

Requires enough historical L2 coverage and rights for the intended claims.

**Scope B — Prospective executable benchmark**

Used when historical L2 is not sufficient, but a prospective recording system can collect enough future L2 coverage.

**Scope C — Price-and-trade benchmark**

Used when depth-aware historical or sufficiently mature prospective L2 cannot be supported.

The decision must be based on evidence.

---

## R1-A Deliverables

```text
r1_data/
├── source_registry.csv
├── license_matrix.csv
├── pilot_market_list.csv
├── raw_pilot/
├── normalized_pilot/
├── join_report.md
├── timestamp_report.md
├── coverage_report.md
├── l2_availability_report.md
├── storage_estimate.md
└── G0_decision.md
```

### R1-A Acceptance Criteria

R1-A is complete only when:

- stable IDs can be traced through the main data chain,
- timestamps are understood,
- historical coverage is measured,
- missingness is measured,
- L2 availability is documented,
- licensing is documented,
- and Scope A/B/C is justified in writing.

---

# 6. R1-B. Joint Probability Research

## Main Research Question

> Given marginal probabilities for several related markets, how do we construct a coherent joint probability distribution that respects the logical constraints between those markets?

This is separate from detecting the market relations.

R2 determines the relations. R1 determines how probabilities can be combined under those relations.

---

## R1-B-1. Start with simple examples

Do not start with the full Polymarket dataset.

Use small hand-made examples.

### Example 1 — Ladder

Suppose:

```text
A = BTC > 30,000
B = BTC > 20,000
```

Because:

```text
A implies B
```

we must have:

```text
P(A) <= P(B)
```

If:

```text
P(A) = 0.60
P(B) = 0.75
```

the probabilities are compatible with the ladder.

If:

```text
P(A) = 0.80
P(B) = 0.60
```

they are not compatible.

R1 must study how to handle both cases.

---

## R1-B-2. Enumerate small joint states

Start with two or three binary events.

For example:

```text
A ∈ {0,1}
B ∈ {0,1}
```

Possible joint states:

```text
(A=0, B=0)
(A=0, B=1)
(A=1, B=0)
(A=1, B=1)
```

A relation may remove some of these states.

Example:

```text
A implies B
```

means:

```text
(A=1, B=0)
```

is impossible.

R1 should first make sure the basic mathematics and implementation are correct on these small examples.

---

## R1-B-3. Define the exact requirements for a valid joint distribution

The final joint distribution should satisfy, where applicable:

```text
1. Every probability >= 0
2. Total probability = 1
3. Required marginals match the input beliefs
4. Impossible states have probability 0
5. Logical relations are respected
```

Write these checks as automated tests.

---

## R1-B-4. Study construction methods

The researcher should compare practical methods for building the joint distribution.

At minimum investigate:

- exact enumeration for small components,
- a constrained optimization / linear programming approach,
- a simple deterministic method for larger components.

The purpose is not to test every possible method in the literature.

The purpose is to find a method that is:

- mathematically valid,
- deterministic,
- reproducible,
- practical at the expected scale,
- and easy to explain in the paper.

---

## R1-B-5. Handle inconsistent market beliefs

The market-provided marginal probabilities may not satisfy all logical constraints.

For example:

```text
P(BTC > 30k) = 0.80
P(BTC > 20k) = 0.60
```

This violates the ladder relationship.

R1 must research and clearly define what happens.

Possible research directions include:

- reject the component,
- project the beliefs to the nearest feasible set,
- use a declared optimization objective,
- or use another deterministic correction method.

Do not choose a method simply because it makes the benchmark run. Test whether the method introduces a systematic bias.

---

## R1-B-6. Controlled belief experiments

R1 should create synthetic examples where the market beliefs are deliberately changed.

For example:

```text
Belief set 1: strongly consistent
Belief set 2: mildly inconsistent
Belief set 3: strongly inconsistent
```

Then test how the chosen joint-probability method behaves.

This will help later when the paper studies controlled belief differences.

---

## R1-B-7. Make one standard belief object

At the end, all allocators should receive the same object.

Conceptually:

```text
belief_object = {
    event_family_id,
    possible_states,
    probability_of_each_state,
    source_marginals,
    constraint_version,
    construction_method,
    data_timestamp
}
```

The actual implementation may use another structure, but the idea must stay the same.

---

## R1-B Deliverables

```text
r1_joint_probability/
├── research_question.md
├── mathematical_definition.md
├── toy_examples/
├── exact_method/
├── scalable_method/
├── feasibility_checks/
├── inconsistent_belief_tests/
├── controlled_belief_tests/
├── joint_belief_schema.json
└── joint_probability_report.md
```

### R1-B Acceptance Criteria

R1-B is complete when:

- small examples can be solved exactly,
- impossible states are removed correctly,
- valid marginals produce valid joint distributions,
- inconsistent marginals are detected,
- the selected handling method is deterministic,
- repeated runs give identical results,
- and the final belief object is usable by all allocators.

---

# 7. How R1 Works Without Waiting for R2

R1 must **not** wait for R2's full relation dataset.

During development, R1 uses manually created constraint examples such as:

```text
A implies B
A and B are mutually exclusive
A and B are exhaustive
A is part of a ladder with B and C
```

Then R1 builds and tests the probability system.

Later, when R2 delivers real constraints:

```text
R2 relation export
        ↓
R1 constraint reader
        ↓
R1 joint probability method
```

The algorithm should remain the same.

Only the input changes.

---

# 8. R2 — Event Families + Relations + Ladder Constraints

## R2 Main Objective

R2 answers:

> Which markets are logically related, and what exact constraint does each relation create?

R2 should focus on **semantic and logical structure**, not on joint-probability construction.

---

## R2-A. Build a Market Metadata Sample

R2 does not need historical L2, full trade history, or the final database.

R2 initially needs only market and event information:

```text
market_id
event_id
question/title
description
outcomes
resolution rule
start time
end time
category/tags
grouping information, if available
```

R2 can collect a small independent sample while R1 is doing the full data feasibility study.

Recommended starting sample:

- 200–500 markets,
- intentionally include markets that appear related,
- include several domains,
- include threshold/ladder examples if available,
- include ambiguous examples.

The sample is for method development, not the final benchmark.

---

# 9. R2-B. Event Family Detection

## Research Question

> How do we decide that multiple markets describe different questions about the same underlying event or process?

### Step 1
Start with metadata-based grouping.

Look for:

- shared event IDs,
- shared market metadata,
- common entities,
- common time window,
- common underlying quantity.

### Step 2
Create deterministic rules where possible.

### Step 3
Use semantic matching only for cases that remain unresolved.

### Step 4
Create a human-checked sample.

Do not automatically accept all model-generated groups.

---

## R2-C. Relation Taxonomy

Start with a small set of clearly defined relation types.

Recommended first version:

```text
1. Implication
2. Complement
3. Mutually exclusive
4. Exhaustive
5. Monotone / ladder
6. No verified relation
7. Ambiguous / quarantine
```

Each relation should contain:

```text
source_market
source_outcome
target_market
target_outcome
relation_type
reason/evidence
valid_from
valid_to
extraction_method
confidence
verification_status
```

---

# 10. R2-D. Ladder Research

This is one of the main research questions for R2.

## Example

Consider:

```text
BTC > 10k
BTC > 20k
BTC > 30k
BTC > 40k
```

The natural logical structure is:

```text
BTC > 40k  =>  BTC > 30k  =>  BTC > 20k  =>  BTC > 10k
```

Therefore:

```text
P(BTC > 10k)
    >= P(BTC > 20k)
    >= P(BTC > 30k)
    >= P(BTC > 40k)
```

R2's job is to detect the **logical relationship**.

R1's job is later to use that relationship when building the joint distribution.

Do not mix these two responsibilities.

---

## R2-D-1. Find candidate ladders

Start with a simple search based on market text and metadata.

For example, detect groups that share:

- the same asset/entity,
- the same quantity,
- the same direction (`above`, `below`, etc.),
- different thresholds,
- similar time windows.

---

## R2-D-2. Verify the ordering

Once a candidate ladder is found, sort it by threshold and manually verify whether the logical implication actually holds.

Do not assume that two similar-looking questions always have a valid relation.

---

## R2-D-3. Convert the relation to a machine rule

For example:

```text
Relation:
BTC > 30k implies BTC > 20k

Machine constraint:
If state(BTC > 30k) = 1,
then state(BTC > 20k) = 1.
```

This is the output that R1 needs.

---

## R2-D-4. Test on synthetic examples

Before waiting for the final dataset, manually create:

```text
valid ladder
invalid ladder
same asset, different time window
same threshold, different asset
similar wording but different meaning
```

The detector should not merge these incorrectly.

---

# 11. R2-E. Other Relations

After ladders are working, investigate:

### Implication

```text
A => B
```

### Complement

```text
A = not B
```

### Mutually exclusive

```text
A and B cannot both be true
```

### Exhaustive

```text
At least one of A/B/... must be true
```

### Combined relations

For example, one market family may contain both a ladder and mutually exclusive outcomes.

The researcher should test whether the relation types can be represented together without creating contradictions.

---

# 12. R2-F. Human Golden Set

Before running the relation system at large scale, build a human-checked set.

Initial target:

**200–300 verified relations.**

The set should contain a mix of:

- true relations,
- false candidate relations,
- ambiguous cases,
- different relation types,
- different domains.

Record the human decision and reason.

If multiple researchers are available for annotation, measure agreement. If not, use a clear adjudication process.

---

# 13. R2-G. Constraint Export

R2 must create a clean export that R1 can read.

Example:

```text
relation_id
family_id
constraint_type
left_variable
right_variable
valid_from
valid_to
verification_status
```

R2 should not produce a probability distribution.

R2 produces the **rules that probabilities must obey**.

---

## R2 Deliverables

```text
r2_relations/
├── market_sample/
├── family_detection/
├── relation_taxonomy.md
├── relation_schema.json
├── ladder_detector/
├── relation_detector/
├── golden_set.csv
├── annotation_guidelines.md
├── constraint_export/
├── relation_tests/
└── relation_audit_report.md
```

### R2 Acceptance Criteria

R2 is complete when:

- event families have a defined rule,
- relations have explicit definitions,
- ladder relations are detected correctly on the test set,
- relations can be converted into machine constraints,
- every released relation has provenance,
- ambiguous relations can be quarantined,
- and a human-checked golden set exists.

---

# 14. How R2 Works Without Waiting for R1

R2 should have two input modes.

### Development mode

Use:

```text
small independently collected metadata sample
+
synthetic markets
+
hand-created difficult cases
```

### Final mode

Use:

```text
R1 canonical market metadata
```

The algorithm should be the same.

Only the input dataset changes.

This is important because otherwise the team may unconsciously tune the method to the final data after seeing the results.

---

# 15. R3 — Execution Simulator + Market Rules

## R3 Main Objective

R3 answers:

> Given the market state, venue rules, and an order at a decision time, what execution should occur?

R3 should focus on deterministic execution.

The first version should not attempt:

- maker queue position,
- endogenous market impact,
- live trading,
- or other features outside the declared benchmark scope.

---

# 16. R3-A. Research the Trading Rules

R3 should first collect and document venue rules.

Investigate:

- order types,
- taker/marketable-limit behavior,
- tick size,
- minimum order size,
- fee rules,
- collateral requirements,
- rounding,
- participation limits if used by the benchmark,
- identifier changes,
- and historical rule changes.

Every rule must have a time range.

Do not build the simulator around one timeless rule file.

---

# 17. R3-B. Build a Synthetic Order Book

R3 does not need historical L2 to start.

Create small hand-built books.

Example:

```text
ASKS
0.51 : 100
0.52 : 200
0.53 : 500

BIDS
0.49 : 100
0.48 : 200
0.47 : 500
```

Then define orders such as:

```text
buy 50
buy 100
buy 150
buy 800
sell 50
sell 500
```

The simulator should consume available levels in a deterministic order.

---

# 18. R3-C. Define One Simple Simulator Interface

The core idea should be close to:

```text
execute(book, order, venue_rules) -> execution_result
```

The exact code can be different, but the interface should make the simulator independent of the source of the order book.

This is what allows R3 to work before historical L2 is available.

---

# 19. R3-D. Unit Tests

Build tests before using any real historical data.

At minimum test:

### Test 1 — Full fill at one price

The order is smaller than the best available level.

### Test 2 — Multi-level fill

The order consumes several price levels.

### Test 3 — Insufficient depth

The order is larger than available depth.

The simulator must not invent liquidity.

### Test 4 — Minimum size

Orders below the minimum size are rejected or handled according to the documented rule.

### Test 5 — Tick size

Prices and order sizes are rounded according to the correct rule.

### Test 6 — Fees

Fees match the rule active at that time.

### Test 7 — Participation limit

Orders above the declared participation limit are handled correctly.

### Test 8 — Reproducibility

Running the same book, order, and rules twice produces exactly the same result.

---

# 20. R3-E. Build the Execution Output

Each simulated execution should contain enough information to audit it.

Example:

```text
order_id
timestamp
asset/token_id
requested_size
filled_size
unfilled_size
side
levels_used
vwap
gross_cost
fees
collateral_locked
final_cost
rule_version
```

The exact schema can be changed, but every result should be explainable.

---

# 21. R3-F. Historical Validation

Historical validation starts only after real historical order books and observed aggressive trades are available.

The process should be:

```text
Historical book just before trade
        ↓
Observed trade size + side
        ↓
R3 simulator
        ↓
Predicted fill
        ↓
Compare with observed execution
```

Compare at least:

- fill size,
- VWAP,
- price levels used,
- fees if reconstructable.

Report results by useful groups such as:

- liquidity,
- trade size,
- participation,
- market category,
- book age,
- data regime.

---

## R3 Deliverables

```text
r3_execution/
├── venue_rules/
├── rule_history.md
├── execution_spec.md
├── simulator/
├── synthetic_books/
├── unit_tests/
├── validation_pipeline/
├── validation_report.md
└── execution_interface.md
```

### R3 Acceptance Criteria

R3 is complete when:

- the simulator is deterministic,
- the simulator never consumes unavailable depth,
- historical rules are selected by time,
- synthetic tests pass,
- and historical validation is complete for the eligible data if Scope A/B is used.

---

# 22. How R3 Works Without Waiting for R1

R3 has two stages.

### Development stage

Use:

```text
synthetic L2 books
+
venue-rule fixtures
+
synthetic orders
```

### Final stage

Use:

```text
R1 historical L2
+
R1 historical trades
+
R3 venue-rule table
```

The simulator code itself should not be rewritten just because the data source changes.

Only the input loader should change.

---

# 23. What Each Researcher Does NOT Own

Clear boundaries are important.

## R1 does not own

- relation extraction,
- ladder detection,
- execution simulation,
- allocator implementation.

## R2 does not own

- historical L2 collection,
- fee reconstruction,
- joint probability construction,
- allocator experiments.

## R3 does not own

- event-family detection,
- logical relation discovery,
- joint probability construction,
- allocator research.

These boundaries should prevent one researcher from becoming a hidden dependency for another.

---

# 24. Recommended Work Order

## Stage 0 — Common setup

All researchers agree on:

- project folder structure,
- minimal schemas,
- timestamp convention,
- identifier names,
- versioning rules.

This should be small and should not delay research.

---

## Stage 1 — Parallel development

### R1

Start:

```text
Data source investigation
Pilot collection
Historical L2 investigation
License investigation
Joint probability toy examples
```

### R2

Start:

```text
Metadata sample
Event family rules
Ladder detector
Relation taxonomy
Synthetic relation tests
Golden-set design
```

### R3

Start:

```text
Venue-rule research
Synthetic order books
Execution interface
Simulator
Unit tests
```

All three can work at the same time.

---

# 25. First Integration Point

Do not wait for the final dataset for the first integration.

As soon as the following exist:

- R1 has a small normalized pilot,
- R2 has a small relation export,
- R3 has a working simulator,

create a **small end-to-end fixture**.

For example:

```text
Market A
Market B
Market C

A => B
B => C

market probabilities:
P(A), P(B), P(C)

small synthetic L2 book

one example allocation/order
```

Then run:

```text
R2
 ↓
logical constraints
 ↓
R1
 ↓
valid joint belief
 ↓
allocator
 ↓
R3
 ↓
execution cost
```

This proves that the interfaces work before large-scale ingestion.

---

# 26. Final Integration Architecture

Once all three workstreams are mature, they should connect as follows:

```text
                    R1 — DATA
                       |
                       | canonical market,
                       | trade, settlement,
                       | book data
                       v
              +-------------------+
              | Common Market     |
              | State / Dataset   |
              +-------------------+
                    |        |
                    |        |
                    v        v
                  R2          R3
              Relations    Execution
                  |            |
                  |            |
                  v            v
        Logical Constraints   Validated
                  |           Execution
                  |           Simulator
                  v            |
              +----------------+
              |      R1        |
              | Joint Belief   |
              +----------------+
                       |
                       v
             Common Joint Belief
                       |
                       v
               Reference Allocators
                       |
                       v
                 Orders / Actions
                       |
                       v
                R3 Execution Engine
                       |
                       v
                 Simulated Results
                       |
                       v
                Metrics + Analysis
```

The important point is:

> **R2 defines the rules. R1 builds the valid probability distribution. R3 models the actual execution.**

---

# 27. Detailed Final Data Flow

## Step 1 — R1 supplies market data

R1 supplies the canonical version of:

```text
markets
outcomes
trades
settlements
books, if available
venue-rule references
```

---

## Step 2 — R2 reads the canonical market metadata

R2 runs the already-tested event-family and relation algorithms.

Output:

```text
families
relations
verified constraints
```

---

## Step 3 — R1 reads the R2 constraints

R1 passes market beliefs and R2 constraints into the joint-probability system.

Output:

```text
one versioned joint belief per benchmark instance
```

Every allocator receives exactly that same belief object.

---

## Step 4 — Allocators make decisions

The benchmark gives every allocator the same:

- beliefs,
- market state,
- bankroll,
- fees,
- constraints,
- benchmark horizon,
- and information available at the decision time.

Only the allocation strategy should differ.

---

## Step 5 — R3 executes the decisions

R3 receives the order/action and the correct market state.

It returns:

```text
fills
fees
slippage
collateral usage
final execution cost
```

---

## Step 6 — Benchmark metrics

The final benchmark computes metrics such as:

- terminal wealth,
- log growth,
- drawdown,
- turnover,
- fees,
- slippage,
- utilization,
- concentration,
- ruin,
- and other declared metrics.

Statistical inference should use event families or suitable time blocks rather than treating every individual contract as an independent observation.

---

# 28. Final Integration Gate

Before running the main benchmark, the three researchers must jointly verify:

## Data

```text
Can every benchmark market be traced to its source?
Can the required historical state be reconstructed?
Are timestamps point-in-time safe?
```

## Relations

```text
Are event families verified?
Are relations versioned?
Are ambiguous relations excluded or marked?
```

## Probability

```text
Are all joint probabilities valid?
Are impossible states assigned zero probability?
Do the supplied marginals and constraints agree?
Does every allocator receive the same belief?
```

## Execution

```text
Does the simulator behave deterministically?
Does it use the correct rules for the date?
Does it respect available depth?
Has historical validation been completed where required?
```

## Benchmark

```text
Are splits frozen?
Are event families protected from leakage across splits?
Are labels only used after settlement?
Are scenario definitions frozen?
Are exclusions fixed?
```

The benchmark should not be frozen until these checks pass.

---

# 29. What Happens If R1 Cannot Obtain Historical L2?

This is a planned branch, not a failure of the whole project.

### Scope A

If full historical L2 is available with suitable coverage and rights:

```text
R1 historical L2
       ↓
R3 validated execution simulator
       ↓
full executable benchmark
```

### Scope B

If historical L2 is not available but prospective collection is possible:

```text
prospective recorder
       ↓
recorded L2
       ↓
R3 simulator
       ↓
benchmark over recorded period
```

### Scope C

If neither historical nor sufficiently mature prospective L2 is available:

```text
market prices / trades
       ↓
allocation evaluation
```

The paper must then remove claims about historical depth-aware execution and validated historical L2 replay.

The purpose of this branch is to prevent the team from silently changing the paper's claims after seeing the data.

---

# 30. Research Questions That Need Independent Investigation

These questions should be researched explicitly rather than assumed.

## R1 research questions

### Data

1. What historical market, trade, settlement, and L2 data is available?
2. What is the earliest useful date?
3. What is the time resolution?
4. Can market, outcome, trade, book, and settlement identifiers be joined reliably?
5. How much historical L2 coverage exists at candidate decision times?
6. What are the timestamp semantics?
7. Which sources can legally be archived and redistributed?
8. Which sources require permission?
9. What storage is required?
10. Which Scope A/B/C is defensible?

### Joint probability

11. What is the correct mathematical definition of the common joint belief?
12. How should small event families be solved exactly?
13. What method works for larger event families?
14. How should inconsistent market marginals be handled?
15. How should controlled belief perturbations be generated?
16. How should the final belief object be versioned and supplied to all allocators?

## R2 research questions

17. How should event families be defined?
18. How can ladder structures be detected reliably?
19. Which relations are common enough to matter?
20. How should implication, complement, exclusive, and exhaustive relations be represented?
21. How often are relations time-varying?
22. How should ambiguous relations be handled?
23. What level of human verification is required?
24. How should semantic relation validity be kept separate from price consistency?

## R3 research questions

25. What historical venue rules apply to the study period?
26. How do fee rules vary over time and across market types?
27. What tick-size and minimum-size rules apply?
28. What are the correct collateral rules?
29. What is the correct order/fill logic for the benchmark's order types?
30. How much historical book staleness is acceptable?
31. What execution error is acceptable for the simulator?
32. Which data strata should be excluded if simulator validation fails?

---

# 31. Common Development Rule: Synthetic First, Real Data Second

This is the most important practical rule in this plan.

### R1

Test the probability system with synthetic relations and probabilities first.

### R2

Test relation discovery with synthetic and small independent market metadata first.

### R3

Test the execution simulator with synthetic order books first.

Then, when R1's real data is ready:

```text
same R2 code + real market metadata
same R3 code + real historical books
same R1 probability code + real beliefs + R2 constraints
```

This protects the project from a common failure mode where one researcher finishes late and everyone else waits.

---

# 32. What Should Be Done Before Large-Scale Data Collection?

The team should be able to answer these questions first:

```text
R1:
Do we know what data we need?
Do we know where it comes from?
Do we know its license?
Do we know how we will test joint probability construction?

R2:
Do we know what a valid relation means?
Do we know how a ladder is represented?
Do we have a human annotation procedure?

R3:
Do we know the historical rules we need?
Do we have a simulator interface?
Does the simulator work on synthetic books?
```

If the answer to these is yes, then the project is ready for the next stage.

---

# 33. Suggested First Deliverables by Researcher

## R1 — First deliverables

1. Source registry.
2. 50–100 market pilot.
3. ID join report.
4. L2 availability report.
5. License matrix.
6. G0 Scope A/B/C decision.
7. Joint probability toy implementation.
8. Joint probability feasibility tests.

## R2 — First deliverables

1. 200–500 market metadata sample.
2. Event-family definition.
3. Relation taxonomy.
4. Ladder detection prototype.
5. Synthetic relation test set.
6. 200–300 relation golden set.
7. Constraint export format.

## R3 — First deliverables

1. Venue-rule table.
2. Historical rule notes.
3. Synthetic order-book fixtures.
4. Execution interface.
5. Deterministic simulator.
6. Unit-test suite.
7. First execution audit report.

---

# 34. Communication Between Researchers

The researchers should communicate through short, versioned outputs rather than changing one another's code.

### R1 → R2

```text
canonical market schema
canonical market IDs
final normalized market metadata
```

### R2 → R1

```text
verified relations
machine-readable constraints
relation version
```

### R1 → R3

```text
historical books
historical trades
canonical timestamps
market/token IDs
```

### R3 → R1

```text
execution interface
rule version
validation report
eligible market/period list
```

### All → Benchmark

```text
frozen data version
frozen relation version
frozen belief version
frozen execution version
frozen benchmark configuration
```

---

# 35. Recommended Git Structure

A simple structure is enough:

```text
repo/
├── r1_data/
├── r1_joint_probability/
├── r2_relations/
├── r3_execution/
├── benchmark/
├── tests/
├── configs/
├── reports/
└── README.md
```

Each researcher owns their directories.

Integration code lives under `benchmark/` and should be changed only after the individual modules have passed their own tests.

---

# 36. Final Success Condition

The three-researcher system is complete when an independent person can understand and reproduce the following chain:

```text
Raw market data
      ↓
Canonical market state
      ↓
Event families and verified relations
      ↓
Machine-readable logical constraints
      ↓
Coherent joint probability distribution
      ↓
Common belief supplied to all allocators
      ↓
Allocator decision
      ↓
Historical / recorded market state
      ↓
Deterministic execution simulator
      ↓
Fees + fills + collateral + slippage
      ↓
Benchmark results
      ↓
Statistical analysis
```

The central experimental requirement is:

> **The allocators must differ in how they allocate capital, not because they were given different beliefs, different market states, or different execution assumptions.**

---

# 37. Final Operating Principle

The team should follow this rule throughout the project:

> **Research independently. Test early with small or synthetic data. Define interfaces before integration. Replace synthetic inputs with R1's real canonical data when available. Freeze the final benchmark only after all three streams pass their own tests and the joined system passes the end-to-end tests.**

This keeps the project moving even if historical data is difficult to obtain, while also preventing the final paper from making claims that the data cannot support.
