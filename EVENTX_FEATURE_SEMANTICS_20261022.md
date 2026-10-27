# EventX: feature semantics and API migration diagnosis

## Findings

The frozen historical preparation assigns Polymarket `size` to its field named `notional`. The market model therefore expects summed **token quantity** in its two notional columns and derived size ratio. Substituting cash value (`price × size`) would change three model inputs. Historical code hashes verified through four linked manifests; the predictor was not loaded.

Earlier source diagnostics used cash value and inclusive left boundaries. The historical trailing sums use **(t−window, t]**. Their saved results remain intact and should be described as cash-based source diagnostics, not exact replicas of model-input eligibility.

A versioned re-audit of 602 comparable candidate windows found **0 quantity-screen passes**, versus **0 cash-screen passes** with the same open-left boundary. It changed 0 candidate pass decisions relative to the frozen earlier diagnostic. These overlap in time and do not count independent events. No predictive admissions follow.

## Source migration required before the first release

Polymarket's [official migration notice](https://docs.polymarket.com/migrate/data-api-v1-to-v2) states retirement of the legacy Data API on24October2026. The [replacement trade API](https://docs.polymarket.com/api-reference/feeds/list-trades) changes filtering and pagination. In particular, market-scoped requests ignore start/end bounds, so simply changing the URL would silently break six-hour reconciliation. The new collector must traverse ordered cursors and filter windows locally, leaving capped or unordered pages unresolved.

The replacement documentation distinguishes taker-only rows from maker-inclusive rows and specifies a default minimum trade size. Neither API success nor matching economic fingerprints establishes unique executions or reproduces historical provider sampling. The migration does not authorize changing a frozen historical study or the project-v2 cycle.

## Remaining compatibility gaps

- Map provider `trade_id` to venue execution identity and account for maker/taker rows.
- Resolve ordering of different-price trades sharing a timestamp; a transaction hash alone is not necessarily one execution.
- Verify source coverage, retained-size thresholds, availability and pagination independently of activity.
- Preserve received-at clocks; backfill cannot restore timely capture during an outage.

The fixed model remains blocked from scoring. Units are now understood; exact observation semantics are not yet established. Machine evidence: `data/v7/feature_semantics_20261022/report.json` and `window_units.jsonl`.
