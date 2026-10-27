# Cached symbol and retrieval inspection

Read-only inspection of the fixed 500 development articles and their exact raw
source lines. Expanded-coverage manifest hashes and all 500 source IDs verified.
No API calls, protected labels, new data or algorithm edits.

## Findings

- All 500 raw records contain `symbol` and `related_symbols` fields.
- `symbol` is non-null in 474 records; `related_symbols` is null in all 500.
- One article mentions Reddit or SoFi in headline/summary: ID129056218, tagged
  `BJ`, from `finnhub:company-news`, ingested May24 at21:32:44.085774Z. Its presence
  does not contradict the June1 zero-row probe; they concern different days.
- Reddit's inclusion contract retrieved16 articles:15 match only `S&P 500`, one
  mentions Reddit. SoFi's inclusion contract retrieved15:all match only `S&P 500`.

The subject registry includes both the company and index; retrieval accepts any
alias. That behavior can be useful for broad candidate recall, but the subsequent
fetch-priority inventory wrongly treats these as evidence of company coverage.
The 40-target batch therefore remains valid recovered metadata, but its ranking
is not a reliable company-news priority list. Original counts are mechanically
correct for any-alias retrieval and must not be described as primary-subject counts.

## Implications

Exact primary-symbol filtering misses some textual mentions. The inspected cache
provides no evidence that related-symbol arrays will recover them. HTTP400 causes
remain unverified; this inspection does not diagnose provider indexing or timeouts.

Recommended next change: separately version the fetch planner to distinguish
primary company/actor matches from index/context-only mentions, retain both counts,
and deduplicate event/threshold variants. Do not change the frozen matcher or admit
new links. Use known source IDs as positive controls for subsequent API diagnostics.
