# EventX v3 historical implementation amendment 2

Frozen before label construction and before any model result.

After adopting the warehouse composite trade key, development day 21 contained one
duplicate `(trade_id, created_time)` key. The two rows were identical on ticker,
timestamp, count and YES price. This is a duplicated warehouse record, not a distinct
execution.

The deterministic policy is therefore:

1. retain executions whose identifier repeats at a different venue timestamp;
2. collapse rows with the same composite key only when all feature-bearing fields are
   identical; and
3. fail the data gate on any same-key conflict in market, size/count or price.

Raw source pages and their hashes are preserved. Normalized feature construction must
apply this exact-duplicate collapse and report the raw-row, unique-key and collapsed-row
counts. The frozen cohort, price definition, label, features, model and hypotheses do
not change.

Lumid also enforces a 1,000,000-row `/retrieve` result cap. A capped interval is never
accepted or truncated: the collector recursively divides it into disjoint half-open
time intervals, applies the same query and validation to each child, and stops with an
error if the minimum 15-minute interval still cannot be materialized.
