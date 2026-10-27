"""Run the resumable, label-blind EventX v3 historical feasibility pipeline."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
import subprocess
import sys
import time
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.export_v3_historical_feasibility import DATASETS


ROOT = REPO_ROOT / "data/v3_historical/feasibility"
STATE = ROOT / "runner_state.json"
LOG = ROOT / "runner.log"
LOCK = ROOT / "runner.lock"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_state(value: dict[str, Any]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(STATE)


def run(command: list[str], log_handle: Any) -> None:
    log_handle.write(f"{now()} START {' '.join(command)}\n")
    log_handle.flush()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
    )
    log_handle.write(f"{now()} END status={completed.returncode}\n")
    log_handle.flush()
    if completed.returncode != 0:
        raise RuntimeError(f"command failed with status {completed.returncode}: {command}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--continuous", action="store_true")
    parser.add_argument("--retry-wait-seconds", type=float, default=900.0)
    return parser.parse_args()


def run_once() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    state: dict[str, Any] = {
        "protocol_id": "eventx-v3-historical-feasibility-20260830",
        "status": "running",
        "started_at": now(),
        "updated_at": now(),
        "current_dataset": None,
        "completed_datasets": [],
        "failed_dataset": None,
        "labels_or_outcomes_read": False,
    }
    write_state(state)
    try:
        with LOG.open("a", encoding="utf-8") as log_handle:
            for dataset in DATASETS:
                state["current_dataset"] = dataset
                state["updated_at"] = now()
                write_state(state)
                run(
                    [
                        sys.executable,
                        "-m",
                        "eventx.tasks.export_v3_historical_feasibility",
                        dataset,
                    ],
                    log_handle,
                )
                state["completed_datasets"].append(dataset)
                state["updated_at"] = now()
                write_state(state)
            state["current_dataset"] = "contract_verification"
            write_state(state)
            run(
                [sys.executable, "-m", "eventx.tasks.verify_v3_historical_feasibility_contract"],
                log_handle,
            )
            state["current_dataset"] = "feasibility_audit"
            write_state(state)
            run(
                [sys.executable, "-m", "eventx.tasks.audit_v3_historical_feasibility"],
                log_handle,
            )
        state["status"] = "complete"
        state["current_dataset"] = None
        state["completed_at"] = now()
        state["updated_at"] = now()
        write_state(state)
    except Exception as exc:
        state["status"] = "failed"
        state["failed_dataset"] = state.get("current_dataset")
        state["error_type"] = type(exc).__name__
        state["error"] = str(exc)[:2000]
        state["updated_at"] = now()
        write_state(state)
        raise


def main() -> None:
    args = parse_args()
    if args.retry_wait_seconds < 60:
        raise SystemExit("--retry-wait-seconds must be at least 60")
    ROOT.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SystemExit("historical feasibility runner is already active") from exc
        lock_handle.seek(0)
        lock_handle.truncate()
        lock_handle.write(f"pid={os.getpid()} started_at={now()}\n")
        lock_handle.flush()
        consecutive_failures = 0
        while True:
            try:
                run_once()
                return
            except Exception as exc:
                if not args.continuous:
                    raise
                consecutive_failures += 1
                retry_at = datetime.now(timezone.utc) + timedelta(
                    seconds=args.retry_wait_seconds
                )
                state = json.loads(STATE.read_text(encoding="utf-8"))
                state.update(
                    {
                        "status": "retry_wait",
                        "continuous": True,
                        "consecutive_failures": consecutive_failures,
                        "last_error": str(exc)[:2000],
                        "next_retry_at": retry_at.isoformat().replace("+00:00", "Z"),
                        "retry_wait_seconds": args.retry_wait_seconds,
                        "updated_at": now(),
                    }
                )
                write_state(state)
                with LOG.open("a", encoding="utf-8") as log_handle:
                    log_handle.write(
                        f"{now()} RETRY_WAIT seconds={args.retry_wait_seconds} "
                        f"failure={consecutive_failures} error={exc!s}\n"
                    )
                time.sleep(args.retry_wait_seconds)


if __name__ == "__main__":
    main()
