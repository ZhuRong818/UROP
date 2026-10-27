# EventX v3 historical implementation amendment 1

Frozen before label construction and before any model result.

The first raw Kalshi development page that reused an identifier contained 50,145
unique `(trade_id, created_time)` keys but only 39,578 unique `trade_id` values.
There were 10,567 repeated identifier rows; every repetition had a different
`created_time`. No composite key was duplicated. Differences in count or price across
some repeated identifiers therefore belong to distinct timestamped executions and
must not be collapsed.

The implementation uses the warehouse table's composite event identity:

- Kalshi: `(trade_id, created_time)`;
- Polymarket: `(trade_id, ts)`.

This is an integrity clarification, not a model or label change. The already frozen
cohort used `COUNT(DISTINCT trade_id)` within one-day activity chunks. That rule
conservatively undercounted some Kalshi executions and is not rerun or relaxed; the
4,670-market cohort remains fixed. For price, volume and label construction, however,
distinct timestamped executions are retained because collapsing them would delete
valid observed trades.

The failed day-14 check and its source page are preserved. The corrected validator
still fails closed on duplicate composite keys, out-of-cohort rows, invalid prices,
or timestamps outside the development interval.
