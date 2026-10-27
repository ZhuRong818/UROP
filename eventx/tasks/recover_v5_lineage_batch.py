"""Read-only priority historical run reconciliation; no article/market endpoints."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import httpx

from eventx.settings import ApiSettings, REPO_ROOT

ROOT = REPO_ROOT / "data/v5/lineage_recovery_20260909"
NEWS = REPO_ROOT / "data/v3_historical/primary/label_blind_inputs/news.jsonl"


def main():
    if ROOT.exists():
        raise FileExistsError("Priority lineage release already exists")
    counts, status = Counter(), {}
    with NEWS.open() as handle:
        for line in handle:
            r = json.loads(line)
            if "2026-05-17" <= r["available_at"] < "2026-07-22":
                counts[r["source_run_id"]] += 1
                status[r["source_run_id"]] = r["run_status"]
    selected = []
    for state in ["failed", "partial", "aborted"]:
        selected += [k for k, _ in counts.most_common() if status[k] == state][:8]
    ROOT.mkdir(parents=True)
    plan = {"rule": "top eight discovery article counts per failed/partial/aborted status; all if fewer",
            "selected": [{"run_id": k, "discovery_articles": counts[k], "cached_status": status[k]}
                         for k in selected], "all_discovery_runs": len(counts),
            "all_runs_by_status": dict(Counter(status.values())),
            "outcome_data_used": False}
    (ROOT / "request_plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    settings = ApiSettings.from_env()

    def fetch(run_id):
        row = {"run_id": run_id, "discovery_articles": counts[run_id], "cached_status": status[run_id],
               "retrieved_at": datetime.now(timezone.utc).isoformat()}
        try:
            with httpx.Client(base_url=settings.base_url, timeout=30, follow_redirects=False,
                              headers={"Authorization": f"Bearer {settings.token}"}) as client:
                response = client.get(f"/catalog/lineage/run/{run_id}")
            row["http_status"] = response.status_code
            if response.status_code == 200:
                data = response.json()
                if data.get("run_id") != run_id:
                    raise ValueError("Wrong lineage ID")
                allowed = ["run_id", "endpoint_id", "started_at", "ended_at", "status",
                           "rows_inserted", "rows_updated", "rows_failed", "response_schema_hash"]
                row["lineage"] = {key: data.get(key) for key in allowed}
                row["lineage"]["args"] = {k: v for k, v in (data.get("args") or {}).items()
                                            if k in {"from", "to", "n_symbols", "category", "window_days"}}
                error = str(data.get("error_text") or "")
                row["lineage"]["error_category"] = (
                    "abandoned_run_cleanup" if "abandoned" in error.lower()
                    else "other_error_present" if error else "empty")
                writes = [data.get("rows_inserted"), data.get("rows_updated")]
                row["write_counters_missing"] = any(v is None for v in writes)
                row["local_rows_exceed_reported_writes"] = (
                    False if row["write_counters_missing"] else counts[run_id] > sum(writes))
                row["source_coverage_reconciled"] = False
            else:
                row["source_coverage_reconciled"] = False
        except (httpx.HTTPError, ValueError, TypeError) as error:
            row["error_type"] = type(error).__name__
        return row

    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for future in as_completed([pool.submit(fetch, k) for k in selected]):
            row = future.result()
            results.append(row)
            (ROOT / (row["run_id"] + ".json")).write_text(json.dumps(row, indent=2, sort_keys=True) + "\n")
            print(json.dumps({"completed": len(results), "planned": len(selected),
                              "http_status": row.get("http_status"), "error_type": row.get("error_type")}), flush=True)
    report = {"status": "priority_lineage_recovered_coverage_not_reconciled",
              "requested_runs": len(selected),
              "successful_runs": sum("lineage" in r for r in results),
              "selected_discovery_articles": sum(counts[k] for k in selected),
              "runs_missing_write_counters": sum(r.get("write_counters_missing", False) for r in results),
              "runs_local_rows_exceed_reported_writes": sum(r.get("local_rows_exceed_reported_writes", False) for r in results),
              "reconciled_runs": 0, "outcome_files_read": [],
              "interpretation": "Run counters and cleanup status are not per-row validity or complete coverage receipts; this priority sample is not a random or full audit."}
    (ROOT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    manifest = {"artifacts": [{"path": str(p.relative_to(REPO_ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                              for p in [*sorted(ROOT.glob("*.json")), Path(__file__).resolve()]]}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
