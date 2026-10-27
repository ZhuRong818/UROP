# V6 source-schema probe correction

Date: 27 September 2026. This note corrects the interpretation of the immutable `data/v6/source_schema_probe_20260927/` record; it does not alter its hashed report or receipt.

The prereceipted repeat made three authenticated read-only catalog schema GETs, for news articles, Kalshi markets and Polymarket markets. **All three returned HTTP 502.** Therefore the report's empty `fields` arrays and zero `field_count` values mean **unobserved schemas**, and its `conclusion` saying no visible revision/version/history fields is invalid for this repeat. `point_in_time_certified: false` remains the correct gate outcome. The HTTP 502 responses do not establish either field absence or source ineligibility.

Earlier ad hoc read-only GETs on the same date returned HTTP 200 and exposed current descriptive/status fields and `ingest_ts`, with no visible revision/validity/history columns in those returned field lists. That observation was not archived with a presampling receipt and is not field-level historical proof. Neither check excludes a private archive, a different endpoint, or documented field-specific immutability. The scoped provider request is `eventx/release/v6/SOURCE_EVIDENCE_REQUEST_20260927.md`; historical admission remains closed until version/status/feed evidence is certified.

Canonical row-level evidence: `data/v6/source_schema_probe_20260927/report.json` and `manifest.json`. Treat `rows[*].status_code` as controlling the ability to infer fields. A later retry, if useful, requires a new versioned script/spec/receipt with an explicit success-only conclusion, not an edit to this frozen record.
