"""Read process/checkpoint/receipt metadata only, never sealed payload contents."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SEALED = ROOT / "data/v4/confirmatory/sealed_inputs"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guard-pid", type=int, required=True)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    out = ROOT / "data/v4/health_checks" / now.strftime("%Y%m%dT%H%M%SZ")
    state_path = SEALED / "collector_state.json"
    state_bytes = state_path.read_bytes()
    state = json.loads(state_bytes)
    lock = json.loads((SEALED / "collector.lock").read_text())
    launch = json.loads((SEALED / "launch_receipt.json").read_text())
    pid = int(lock["pid"])
    process = subprocess.run(["ps", "-o", "pid=,ppid=,stat=,etime=,comm=", "-p",
                              f"{pid},{args.guard_pid}"], check=True, capture_output=True, text=True)
    processes = []
    for line in process.stdout.splitlines():
        process_id, parent, status, elapsed, command = line.split(None, 4)
        processes.append(dict(pid=int(process_id), ppid=int(parent), status=status,
                              elapsed=elapsed, executable=command))
    present = {p["pid"] for p in processes if not p["status"].startswith("Z")}
    protected = ["consumption_receipt.json", "examples/examples.bin", "evaluation/result.json",
                 "evaluation/predictions.bin", "evaluation/evaluation_attempt_receipt.json"]
    # Existence checks ONLY. Do not read these files even if unexpectedly present.
    protected_exists = {p: (SEALED.parent / p).exists() for p in protected}
    expected, problems = {}, []
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    stop = min(today, datetime(2026, 10, 30, tzinfo=timezone.utc))
    for kind, start, names in [
        ("news", datetime(2026, 8, 30, tzinfo=timezone.utc), ["articles"]),
        ("trades", datetime(2026, 9, 6, tzinfo=timezone.utc),
         [f"batch_{i:03d}" for i in range(1, 11)])]:
        completed = datetime.fromisoformat(state[f"next_{kind[:-1] if kind == 'trades' else kind}_day"].replace("Z", "+00:00"))
        complete_receipts = 0
        for offset in range((completed-start).days):
            day = (start+timedelta(days=offset)).date().isoformat()
            for name in names:
                base = SEALED / kind / day
                receipt = base / f"{name}_receipt.json"
                if not all((base / f"{name}{s}").is_file() for s in
                           (".jsonl", ".sql", "_receipt.json")):
                    problems.append(f"missing batch file: {kind}/{day}/{name}")
                    continue
                r = json.loads(receipt.read_text())
                if not (len(r.get("data_sha256", "")) == 64 and
                        len(r.get("sql_sha256", "")) == 64 and r.get("receipt", {}).get("run_id")):
                    problems.append(f"malformed receipt: {kind}/{day}/{name}")
                    continue
                complete_receipts += 1
        expected[kind] = {"checkpointed_days": (completed-start).days,
                          "receipts_present_with_payload_and_sql_files": complete_receipts,
                          "closed_days_pending": max(0, (stop-completed).days)}
        state_count = state["completed_trade_days" if kind == "trades" else "completed_news_days"]
        if state_count != expected[kind]["checkpointed_days"]:
            problems.append(f"{kind}: checkpoint counter mismatch")
    manifest = json.loads((ROOT / "eventx/release/v4/holdout_implementation_manifest.json").read_text())
    frozen = [{"path": a["path"], "matches": hashlib.sha256((ROOT/a["path"]).read_bytes()).hexdigest() == a["sha256"]}
              for a in manifest["artifacts"]]
    code_hash = hashlib.sha256((ROOT / "eventx/tasks/collect_v4_confirmatory_warehouse.py").read_bytes()).hexdigest()
    report = {"checked_at": now.isoformat(), "scope": "process_checkpoint_receipt_metadata_only",
              "state": state, "state_sha256": hashlib.sha256(state_bytes).hexdigest(),
              "processes": processes, "collector_alive": pid in present,
              "guard_alive": args.guard_pid in present,
              "guard_parent_matches_collector": any(p["pid"] == args.guard_pid and p["ppid"] == pid for p in processes),
              "launch_pid_matches_lock": launch["pid"] == pid,
              "collector_code_matches_launch": code_hash == launch["collector_code_sha256"],
              "partition_checks": expected, "problems": problems,
              "protected_artifact_existence_only": protected_exists,
              "frozen_hash_checks": frozen,
              "sealed_payloads_or_outcomes_opened": False,
              "source_completeness_or_payload_integrity_certified": False,
              "process_restarted_or_code_changed": False}
    out.mkdir(parents=True, exist_ok=False)
    (out/"report.json").write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print(json.dumps({"report": str((out/"report.json").relative_to(ROOT)),
                      **{k:report[k] for k in ("collector_alive", "guard_alive", "partition_checks",
                           "problems", "protected_artifact_existence_only", "collector_code_matches_launch")},
                      "frozen_hashes_matching": sum(a["matches"] for a in frozen)}, indent=2))


if __name__ == "__main__":
    main()
