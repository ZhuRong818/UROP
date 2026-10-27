"""Launch or inspect the label-blind EventX historical feasibility runner."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.launch_v2_3_news_v2 import process_alive, relative


ROOT = REPO_ROOT / "data/v3_historical/feasibility"
LOCK = ROOT / "runner.lock"
STATE = ROOT / "runner_state.json"
SUPERVISOR_LOG = ROOT / "continuous_supervisor.log"


def read_runner_pid(lock_path: Path) -> int | None:
    try:
        value = lock_path.read_text(encoding="utf-8")
    except OSError:
        return None
    matched = re.search(r"\bpid=(\d+)\b", value)
    return int(matched.group(1)) if matched else None


def load_state(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def status(root: Path) -> dict[str, Any]:
    lock_path = root / LOCK.name
    state_path = root / STATE.name
    pid = read_runner_pid(lock_path)
    return {
        "alive": process_alive(pid),
        "lock_path": relative(lock_path),
        "pid": pid,
        "state": load_state(state_path),
        "state_path": relative(state_path),
        "supervisor_log": relative(root / SUPERVISOR_LOG.name),
    }


def launch(root: Path, retry_wait_seconds: float) -> None:
    current = read_runner_pid(root / LOCK.name)
    if process_alive(current):
        raise SystemExit(f"historical runner already active with PID {current}")
    root.mkdir(parents=True, exist_ok=True)

    first_child = os.fork()
    if first_child:
        os.waitpid(first_child, 0)
        return
    os.setsid()
    second_child = os.fork()
    if second_child:
        os._exit(0)

    os.chdir(REPO_ROOT)
    os.umask(0o027)
    command = [
        "caffeinate",
        "-dimsu",
        sys.executable,
        "-m",
        "eventx.tasks.run_v3_historical_feasibility",
        "--continuous",
        "--retry-wait-seconds",
        str(retry_wait_seconds),
    ]
    log_path = root / SUPERVISOR_LOG.name
    with Path("/dev/null").open("rb") as stdin_handle, log_path.open(
        "ab"
    ) as log_handle:
        os.dup2(stdin_handle.fileno(), 0)
        os.dup2(log_handle.fileno(), 1)
        os.dup2(log_handle.fileno(), 2)
        os.execvp("caffeinate", command)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--retry-wait-seconds", type=float, default=900.0)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.status:
        print(json.dumps(status(args.root), indent=2, sort_keys=True))
        return
    if args.retry_wait_seconds < 60:
        raise SystemExit("--retry-wait-seconds must be at least 60")
    launch(args.root, args.retry_wait_seconds)
    deadline = time.monotonic() + 15
    state = status(args.root)
    while not state["alive"] and time.monotonic() < deadline:
        time.sleep(0.25)
        state = status(args.root)
    print(json.dumps(state, indent=2, sort_keys=True))
    if not state["alive"]:
        raise SystemExit("historical runner did not remain alive; inspect its log")


if __name__ == "__main__":
    main()
