"""Reconcile source-only receipts and refresh candidate queues; no admission."""

import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/v5/recovery_summary_20260910"


def main():
    if OUT.exists():
        raise SystemExit("Summary already exists; never overwrite evidence")
    receipts = ROOT / "data/v5/provenance_recovery_20260908"
    originals = [json.loads(l) for l in (ROOT / "data/v5/source_readiness_20260908/family_review_queue.jsonl").open()]
    recovered = {r["condition_id"]: r for l in
                 (ROOT/"data/v5/embedded_membership_recovery_20260910/candidate_memberships.jsonl").open()
                 if (r := json.loads(l))}
    artifacts, snapshots, attempts = [], [], []
    for path in sorted(receipts.glob("*20260910*.json")):
        r = json.loads(path.read_text())
        attempts.append({"path": str(path.relative_to(ROOT)), "status": r["status"],
                         "http_status": r.get("http_status"), "error_type": r.get("error_type")})
        artifacts.append(path)
        if r["status"] != "complete":
            continue
        data = ROOT/r["data_path"]
        if hashlib.sha256(data.read_bytes()).hexdigest() != r["data_sha256"]:
            raise ValueError("Recovered data hash mismatch")
        rows = [json.loads(l) for l in data.open()]
        if len(rows) != r["rows"]:
            raise ValueError("Receipt count mismatch")
        artifacts.append(data)
        if r["name"].startswith("metadata_snapshots_"):
            if len(rows) >= 5000:
                raise ValueError("Censored snapshot batch")
            snapshots.extend(rows)
    wanted = {r["market_id"] for r in originals if r["venue"] == "polymarket"}
    found = collections.Counter(r["condition_id"] for r in snapshots)
    if set(found) != wanted or any(n != 1 for n in found.values()):
        raise ValueError("Snapshot target coverage/uniqueness mismatch")
    queue = []
    for original in originals:
        row = dict(original)
        if row["venue"] == "polymarket":
            record = recovered[row["market_id"]]
            if len(record["candidate_event_ids"]) != 1:
                raise ValueError("Do not silently choose ambiguous membership")
            row["candidate_family_id"] = "polymarket:event:"+record["candidate_event_ids"][0]
            row["membership_evidence"] = record["evidence"]
        row["family_verified"] = False
        row["approved_family_id"] = None
        queue.append(row)
    counts = collections.Counter(r["candidate_family_id"] for r in queue)
    report = {"metadata_snapshots": len(snapshots), "unique_snapshot_targets": len(found),
        "snapshot_versions_per_target": 1, "snapshot_version_history_certified": False,
        "queue_markets": len(queue), "candidate_groups": len(counts),
        "missing_candidate_memberships": sum(r["candidate_family_id"] is None for r in queue),
        "final_approved_families": 0, "news_intervals_reconciled": 0,
        "attempt_status_counts": dict(collections.Counter(r["status"] for r in attempts)),
        "attempts": attempts, "labels_or_outcomes_read": False,
        "remaining": ["semantic dependency/cross-venue review", "metadata and exact news-content version evidence",
                      "news interval completeness reconciliation", "bootstrap temporal-dependence validation"]}
    OUT.mkdir(parents=True)
    (OUT/"candidate_family_queue.jsonl").write_text("".join(json.dumps(r, sort_keys=True)+"\n" for r in queue))
    (OUT/"report.json").write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    artifacts += [Path(__file__), *sorted(OUT.iterdir())]
    (OUT/"manifest.json").write_text(json.dumps({"status": "source_only_not_admitted",
        "artifacts": [{"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in artifacts]}, indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k != "attempts"}, indent=2))


if __name__ == "__main__":
    main()
