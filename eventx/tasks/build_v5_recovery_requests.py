"""Prepare exact-ID, projected recovery queries without executing or admitting data."""

import hashlib
import json
from pathlib import Path

from eventx.settings import REPO_ROOT

OUT = REPO_ROOT / "data/v5/recovery_requests_20260909"
CACHE = REPO_ROOT / "data/v3_historical/feasibility/raw/polymarket_markets/polymarket_markets.jsonl"
QUEUE = REPO_ROOT / "data/v5/source_readiness_20260908/family_review_queue.jsonl"
END = "2026-07-22T00:00:00Z"


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def event_sql(targets):
    values = ",\n".join(f"({literal(cid)}, {literal(mid)})" for cid, mid in targets)
    return f"""WITH targets(condition_id, cached_market_id) AS (VALUES
{values}
)
SELECT DISTINCT t.condition_id, t.cached_market_id, e.event_id,
       e.title AS event_title, e.source, e.source_endpoint, e.source_run_id, e.ingest_ts
FROM prediction_markets.polymarket_events e
CROSS JOIN LATERAL jsonb_array_elements_text(
  CASE WHEN jsonb_typeof(e.market_ids) = 'array' THEN e.market_ids ELSE '[]'::jsonb END
) AS member(market_id)
JOIN targets t ON member.market_id = t.cached_market_id
WHERE e.ingest_ts < TIMESTAMPTZ '{END}'
ORDER BY t.condition_id, e.event_id, e.source
LIMIT 5000
"""


def metadata_sql(targets):
    ids = ",".join(literal(cid) for cid, _ in targets)
    return f"""SELECT id, condition_id, question, start_date, end_date, active, closed,
       source, source_endpoint, source_run_id, ingest_ts
FROM prediction_markets.polymarket_markets
WHERE condition_id IN ({ids})
  AND ingest_ts < TIMESTAMPTZ '{END}'
ORDER BY condition_id, ingest_ts, source
LIMIT 5000
"""


def main():
    if OUT.exists():
        raise FileExistsError("Recovery request package already exists")
    targets = {}
    for line in QUEUE.read_text().splitlines():
        r = json.loads(line)
        if r["venue"] == "polymarket":
            targets[r["market_id"]] = None
    for line in CACHE.read_text().splitlines():
        r = json.loads(line)
        if r["condition_id"] in targets:
            old = targets[r["condition_id"]]
            if old is not None and old != str(r["id"]):
                raise ValueError("Ambiguous condition-to-market ID in local evidence")
            targets[r["condition_id"]] = str(r["id"])
    if any(value is None for value in targets.values()):
        raise ValueError("Cannot use condition IDs as a substitute for market IDs")
    OUT.mkdir(parents=True)
    ordered = sorted(targets.items())
    plans = []
    for batch, start in enumerate(range(0, len(ordered), 50)):
        part = ordered[start:start+50]
        for kind, build in [("event_links", event_sql), ("metadata_snapshots", metadata_sql)]:
            path = OUT / f"{kind}_{batch:03d}.sql"
            path.write_text(build(part))
            plans.append({"query_file": str(path.relative_to(REPO_ROOT)), "targets": len(part),
                          "status": "not_executed_retrieve_unavailable"})
    (OUT / "polymarket_targets.json").write_text(json.dumps(
        [{"condition_id": k, "cached_market_id": v} for k, v in ordered], indent=2) + "\n")
    report = {"polymarket_conditions": len(ordered), "target_batch_size": 50,
              "queries": plans, "source_route": "POST /findata/retrieve",
              "admission_status": "blocked_not_executed",
              "review_contract": [
                  "Compare source row count with downloaded rows; LIMIT hit means censored, split batch",
                  "Audit zero-match/multiple-event markets; never substitute slug equality",
                  "Probe market_ids JSON element types before running full batches; query assumes scalar IDs",
                  "Snapshot status is not status history; no validity intervals may be invented",
                  "Review shared drivers across events and venues before approving family IDs",
                  "Do not admit metadata/content as historical solely from ingest_ts",
              ], "outcome_columns_requested": False,
              "source_files": [str(QUEUE.relative_to(REPO_ROOT)), str(CACHE.relative_to(REPO_ROOT))]}
    (OUT / "request_manifest.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    artifacts = [*sorted(OUT.iterdir()), Path(__file__).resolve(), QUEUE, CACHE]
    (OUT / "hashes.json").write_text(json.dumps(
        [{"path": str(p.relative_to(REPO_ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
         for p in artifacts], indent=2, sort_keys=True) + "\n")
    print(json.dumps({"targets": len(ordered), "queries_prepared": len(plans),
                      "queries_executed": 0, "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
