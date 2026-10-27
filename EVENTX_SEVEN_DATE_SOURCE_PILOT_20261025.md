# EventX seven-date price-only source pilot — 25 October 2026

Completed the frozen 20-market source pilot: **114,154 YES-token events**, **602 fresh 30-minute endpoint pairs**, and **60 windows with continuous history and forward coverage**. This establishes source yield, not forecast accuracy or a baseline-beating result.

## Scope and selection

April 21–27, 2026, from 12:00–14:00 UTC each day: **14 sampled hours**, not 168 hours of continuous week coverage. The five-minute grid covers 12:30–13:25 daily; each complete window needs 30 minutes of history and 30 minutes forward. The frozen cohort contains 20 markets and 140 scheduled market-days (1,680 decision grids).

A seeded SHA256 ordering of cached identity-only candidates was frozen before metadata retrieval. Twenty markets passed exact binary YES/NO mapping, start/end-date and rule-text checks after 53 metadata lookups from 128 candidates. The selected IDs were then frozen before new economic-column retrieval. No substitutions followed coverage outcomes. There is zero overlap with the prior five price-inspected markets.

This remains an availability-conditioned convenience sample from the first sorted-market row group, not a representative market-universe sample. Metadata is current and may be revised historically. Scheduled end dates do not prove that a market remained tradable throughout the sample.

## Coverage results

All 14/14 hourly files completed; 53,157,576 archive bytes downloaded under the 512 MiB cap. Metadata response bodies are outside this archive-byte count.

| Date | YES events | Fresh current | Fresh endpoint pairs | Continuous forward | Continuous history + forward | Markets with complete windows |
|---|---:|---:|---:|---:|---:|---:|
| 2026-04-21 | 13,720 | 113 | 106 | 28 | 11 | 2 |
| 2026-04-22 | 21,685 | 86 | 78 | 22 | 11 | 2 |
| 2026-04-23 | 13,345 | 101 | 89 | 22 | 8 | 1 |
| 2026-04-24 | 14,767 | 91 | 76 | 9 | 0 | 0 |
| 2026-04-25 | 11,472 | 112 | 98 | 30 | 17 | 3 |
| 2026-04-26 | 24,045 | 101 | 89 | 24 | 11 | 1 |
| 2026-04-27 | 15,120 | 95 | 66 | 5 | 2 | 1 |

Complete quote-coverage windows occur in **5 markets, 10 market-days and 6 calendar dates**. Overlapping targets, common markets and shared calendar shocks mean these are not independent samples. Twenty current event-family IDs are not twenty verified information episodes.

| Domain (descriptive metadata annotation) | Selected markets | Fresh endpoint pairs | Complete history + forward |
|---|---:|---:|---:|
| crypto | 3 | 149 | 9 |
| energy | 2 | 114 | 4 |
| entertainment | 2 | 72 | 0 |
| foreign_exchange | 1 | 0 | 0 |
| monetary_policy | 1 | 36 | 0 |
| politics | 2 | 162 | 43 |
| sports | 9 | 69 | 4 |

All domains and failed market-days are retained. The categories are assistant annotations, not independent human review, and did not influence selection.

## Method and remaining limitations

Direct best bid and ask are taken from the received update. A same-receipt-time group must have one unique quote pair. Ambiguous or invalid states reset coverage until a later valid observation; missing updates are not filled across gaps. Prices must be strictly between zero and one, noncrossed, with spread at most 0.05. Both source and receive clocks must remain within 120 seconds. No depth is inferred or imputed.

Continuous windows require valid coverage at every observed update and no freshness gap through the entire history/forward interval. This is an observed-stream continuity check, not proof that the archive received every exchange message. We do not compute target changes, model predictions or forecast errors in this pilot.

**Fully admitted forecasting observations remain zero** under the current status/completeness requirements. Current metadata establishes identity, but historical tradability and rule versions are not verified. The live depth model and the original absolute-movement classifier are unchanged. This sample does not include verified news signals and cannot establish incremental news value.

## Next execution decision

Expand coverage across full daily hours using the same fixed cohort and rules, with a new bounded manifest, if the observed yield supports the cost. Do not replace poor-coverage markets with winners. In parallel, resolve historical-status evidence or explicitly freeze a different observational quote-prediction task whose claims exclude tradability. That target decision must precede model selection.

Then freeze persistence and a small price-only candidate set (momentum, volatility, spread and quote-update age) on matched rows. Use purged chronological development splits and reserve a disjoint future block for confirmation. Keep unchanged prices, all eligible segments and all candidate comparisons. Neither row count nor selected development wins alone establishes a paper-level result.

## Integrity and evidence

No protected evaluation-period prices were read. Mixed April chunks decoded 264,932 excluded-cohort rows; those were filtered before retained economic analysis. All frozen models and holdouts remain unchanged. 169 manifest entries verified. Coverage parity against the prior five-market audit passed all four measures (24/23/18/10); missing days fail closed.

- [Frozen scope](eventx/release/v7/archive_week_pilot_20261025/policy.json)
- [Frozen market identities](eventx/release/v7/archive_week_pilot_20261025/selected_markets.json)
- [Canonical source report](data/v7/archive_week_pilot_20261025/capture/report.json)
- [All market-day results](data/v7/archive_week_pilot_20261025/capture/market_day_metrics.json)
- [Domain and date summaries](data/v7/archive_week_pilot_20261025/coverage_summary.json)
- [Capture hash manifest](data/v7/archive_week_pilot_20261025/capture/manifest.json)
- [Delivery hash manifest](data/v7/archive_week_pilot_20261025/delivery_manifest.json)
