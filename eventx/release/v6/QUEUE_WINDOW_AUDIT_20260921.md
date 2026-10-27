# Corrected queue: clocks and missing-field investigation

Reconciled all134 contract snapshots with866 retrieved development article pairs.
Inputs/receipts were hash-verified. Original cards remain unchanged.

| Venue | Before start | Within bounds | At/after end | Missing bound |
|---|---:|---:|---:|---:|
| Kalshi |157|315|175|0|
| Polymarket |55|120|39|5|

Of435 within-bound pairs,405 have primary-subject mentions;185 also have snapshot
ingestion at/before article availability. These are screening results, NOT validated
links or admitted observations. Polymarket bounds are nominal start/end dates, not
verified trading activation/closure. No predictive admissions or protected outcomes.

## Missing fields investigated

Two additional descriptive queries returned all10 requested rows, HTTP200; payload
hashes verified. Six Kalshi records still have null primary, secondary and alternative
rule fields: three July Fed-decision contracts and three World Cup winner contracts.
Four Polymarket World Cup quarterfinal contracts have null endDate, endDateIso and
closeTime. Their descriptions contain a July21 fallback resolution deadline, but
that is not proof of actual trading closure and was NOT substituted for end time.

Thus no gaps were closed by these alternate-field probes. This establishes absence
in the queried snapshots/fields, not absence everywhere at Lumid.

Evidence: `data/v6/queue_windows_20260921/` includes pair-level screens, missing-field
records, queries and manifest. Fetch receipts:
`data/v5/provenance_recovery_20260908/v6_queue_gaps_kalshi_20260921.json` and
`v6_queue_gaps_polymarket_20260921.json`.

Next use the primary-mention, time-screened subset for a bounded association
diagnostic, retaining distinct source-version, relevance and family gates. Seek
historical rule/status evidence for the ten incomplete contracts; do not fill gaps
from inferred deadlines or describe the185 pairs as experiment-ready.
