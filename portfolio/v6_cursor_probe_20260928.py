"""Prereceipted, bounded source-ledger check for opened V6 development."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import httpx

from eventx.settings import ApiSettings

HERE = Path(__file__).resolve().parent
OUT = HERE / "v6_cursor_probe_20260928"
SCRIPT = Path(__file__).resolve()
QUERIES = {
    "cursor.sql": """SELECT endpoint_id, scope_key, last_run_id, last_data_date,
       last_run_at, next_action, retry_count
FROM provenance.scrape_cursor
WHERE endpoint_id = 'finnhub:company-news'
ORDER BY scope_key
LIMIT 20""",
    "successors.sql": """WITH failed(run_id, decision_at) AS (
  VALUES
    ('d8bcb0d0-be28-4a0a-920c-d6087a07e5a8'::uuid, '2026-05-30T13:52:00Z'::timestamptz),
    ('c40c9e49-4a6a-44d1-a0d9-43ca033d21ae'::uuid, '2026-06-01T16:22:01Z'::timestamptz),
    ('fd734424-86f2-4d65-a67c-868d6f80730a'::uuid, '2026-06-23T18:52:01Z'::timestamptz),
    ('592ebc42-79ad-4b33-af2d-628b5edb6167'::uuid, '2026-06-30T04:52:01Z'::timestamptz),
    ('86c568d4-f947-43e2-950b-8cf740690a9e'::uuid, '2026-07-02T18:37:01Z'::timestamptz)
)
SELECT f.run_id::text AS failed_run_id, f.decision_at,
       r.run_id::text AS successor_run_id, r.started_at, r.ended_at,
       r.status, r.rows_inserted, r.rows_failed, r.args->>'to' AS requested_to
FROM failed f
LEFT JOIN LATERAL (
  SELECT r.* FROM provenance.runs r
  WHERE r.endpoint_id = 'finnhub:company-news'
    AND r.started_at > f.decision_at
    AND r.started_at < f.decision_at + interval '7 days'
    AND r.status IN ('ok', 'partial')
  ORDER BY r.started_at
  LIMIT 1
) r ON true
ORDER BY f.decision_at
LIMIT 5""",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def prepare():
    OUT.mkdir(exist_ok=False)
    for name, sql in QUERIES.items():
        (OUT / name).write_text(sql + "\n")
    write(OUT / "receipt.json", {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "written_before_request": True,
        "script_sha256": digest(SCRIPT),
        "query_sha256": {name: digest(OUT / name) for name in QUERIES},
        "scope": "opened V6 finnhub company-news endpoint cursor and five nearest completed successors; read only",
    })


def run():
    receipt = json.loads((OUT / "receipt.json").read_text())
    if receipt["script_sha256"] != digest(SCRIPT):
        raise ValueError("script changed since receipt")
    if receipt["query_sha256"] != {name: digest(OUT / name) for name in QUERIES}:
        raise ValueError("query changed since receipt")
    if (OUT / "report.json").exists():
        raise FileExistsError("report already exists")
    settings = ApiSettings.from_env()
    report = {"base_url": settings.base_url, "queried_at_utc": datetime.now(timezone.utc).isoformat()}
    with httpx.Client(base_url=settings.base_url, headers={"Authorization": "Bearer " + settings.token}, timeout=30) as client:
        for name in QUERIES:
            response = client.post("/retrieve", json={"sql": (OUT / name).read_text(), "output_format": "jsonl"})
            item = {"retrieve_status": response.status_code, "rows": []}
            if response.status_code == 200:
                info = response.json()
                uri = info.get("materialized_uri")
                if uri:
                    result = client.get(uri)
                    item["materialized_status"] = result.status_code
                    if result.status_code == 200:
                        item["rows"] = [json.loads(line) for line in result.text.splitlines() if line.strip()]
                else:
                    item["response_keys"] = sorted(info)
            else:
                try:
                    body = response.json()
                    item["error_keys"] = sorted(body) if isinstance(body, dict) else []
                except ValueError:
                    item["error_keys"] = []
            report[name] = item
    report["coverage_certified"] = False
    report["predictive_admissions"] = 0
    write(OUT / "report.json", report)
    write(OUT / "manifest.json", {"outputs": {name: digest(OUT / name) for name in (*QUERIES, "receipt.json", "report.json")}})
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    {"prepare": prepare, "run": run}[sys.argv[1]]()
