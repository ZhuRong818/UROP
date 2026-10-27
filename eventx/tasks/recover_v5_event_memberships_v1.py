"""Projected embedded event-ID recovery for the pre-existing 819-target queue.

Only existing historical metadata is requested; never raw JSON, prices or outcomes.
Recovered group candidates are NOT certified historical versions/final families.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from eventx.tasks.build_v5_recovery_requests import literal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/v5/embedded_membership_recovery_20260910"
RECEIPTS = ROOT / "data/v5/provenance_recovery_20260908"


def query(ids):
    return f"""SELECT m.condition_id, m.id AS cached_market_id,
       jsonb_typeof(m.raw->'events') AS container_type,
       jsonb_typeof(e.value) AS member_type,
       e.value->>'id' AS event_id, e.value->>'title' AS event_title,
       m.raw->>'groupItemTitle' AS contract_subtitle,
       m.source, m.source_endpoint, m.source_run_id, m.ingest_ts
FROM prediction_markets.polymarket_markets m
LEFT JOIN LATERAL jsonb_array_elements(
  CASE WHEN jsonb_typeof(m.raw->'events') = 'array'
       THEN m.raw->'events' ELSE '[]'::jsonb END
) e(value) ON true
WHERE m.condition_id IN ({','.join(literal(i) for i in ids)})
  AND m.ingest_ts < TIMESTAMPTZ '2026-07-22T00:00:00Z'
ORDER BY m.condition_id, event_id, m.source
LIMIT 5000
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.attempt <= 10:
        raise ValueError("Bounded attempt identifier required")
    targets = json.loads((ROOT / "data/v5/recovery_requests_20260909/polymarket_targets.json").read_text())
    wanted = {r["condition_id"]: r["cached_market_id"] for r in targets}
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "report.json").exists():
        raise SystemExit("Completed recovery exists; create a new version")
    recovered, evidence = [], []
    for start in range(0, len(targets), 50):
        batch = targets[start:start+50]
        name = f"embedded_events_{start//50:03d}_20260910_attempt{args.attempt}"
        path = OUT / f"{name}.sql"
        sql = query([r["condition_id"] for r in batch])
        if path.exists() and path.read_text() != sql:
            raise ValueError("Existing query differs; version the request")
        if not path.exists():
            path.write_text(sql)
        receipt_path = RECEIPTS / f"{name}.json"
        if not receipt_path.exists():
            subprocess.run([sys.executable, "-m", "eventx.tasks.recover_v5_provenance", name,
                            "--sql-file", str(path)], check=True, cwd=ROOT)
        receipt = json.loads(receipt_path.read_text())
        if receipt["status"] != "complete" or receipt["rows"] >= 5000:
            raise ValueError("Failed/censored request: stop, never convert to zero membership")
        data = ROOT / receipt["data_path"]
        if hashlib.sha256(data.read_bytes()).hexdigest() != receipt["data_sha256"]:
            raise ValueError("Downloaded data hash mismatch")
        rows = [json.loads(line) for line in data.open()]
        if len(rows) != receipt["rows"]:
            raise ValueError("Receipt row count mismatch")
        for row in rows:
            if row["condition_id"] not in wanted or str(row["cached_market_id"]) != wanted[row["condition_id"]]:
                raise ValueError("Condition/market identity mismatch")
        recovered.extend(rows)
        evidence.extend([path, receipt_path, data])
    queue, counts = [], {}
    for cid in wanted:
        rows = [r for r in recovered if r["condition_id"] == cid]
        event_ids = sorted({r["event_id"] for r in rows if r.get("event_id")
                            and r.get("member_type") == "object"})
        status = "single_candidate" if len(event_ids) == 1 else "multiple_candidates" if event_ids else "missing"
        counts[status] = counts.get(status, 0)+1
        queue.append({"condition_id": cid, "candidate_event_ids": event_ids,
                      "evidence": rows, "status": status, "family_verified": False,
                      "historical_version_certified": False})
    (OUT / "candidate_memberships.jsonl").write_text("".join(json.dumps(r, sort_keys=True)+"\n" for r in queue))
    report = {"targets": len(wanted), "recovered_rows": len(recovered), "membership_status": counts,
              "unique_candidate_events": len({e for r in queue for e in r["candidate_event_ids"]}),
              "approved_families": 0, "historical_versions_certified": 0,
              "outcome_fields_requested": False}
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    evidence += [OUT / "report.json", OUT / "candidate_memberships.jsonl", Path(__file__)]
    (OUT / "manifest.json").write_text(json.dumps({"artifacts": [
        {"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in evidence]}, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
