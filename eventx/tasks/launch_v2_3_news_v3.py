"""Launch or inspect the hardened EventX v2.3 implementation-v3 collector."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import time

from eventx.settings import REPO_ROOT
from eventx.tasks.launch_v2_3_news_v2 import process_alive, read_pid, relative


DEFAULT_ROOT = REPO_ROOT / "data" / "v2_3_1" / "prospective_news"
DEFAULT_LOG = REPO_ROOT / "data" / "v2_3_1" / "logs" / "news_collector_v3.log"


def status(root: Path, log_path: Path) -> dict[str, object]:
    pid = read_pid(root)
    receipts = sorted((root / "restart_receipts").glob("*.json"))
    return {
        "alive": process_alive(pid),
        "health_exists": (root / "health.json").is_file(),
        "health_path": relative(root / "health.json"),
        "latest_restart_receipt": relative(receipts[-1]) if receipts else None,
        "log_path": relative(log_path),
        "pid": pid,
        "restart_receipt_count": len(receipts),
    }


def launch(root: Path, log_path: Path, *, since: str | None) -> None:
    current = read_pid(root)
    if process_alive(current):
        raise SystemExit(f"collector already running with PID {current}")
    root.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    state_exists = (root / "state" / "news_collector.sqlite3").is_file()
    if not state_exists and since is None:
        since = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat().replace(
            "+00:00", "Z"
        )

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
        "eventx.tasks.collect_v2_3_news_v3",
        "--root",
        str(root),
    ]
    if not state_exists:
        assert since is not None
        command.extend(["--since", since])
    with Path("/dev/null").open("rb") as stdin_handle, log_path.open("ab") as log_handle:
        os.dup2(stdin_handle.fileno(), 0)
        os.dup2(log_handle.fileno(), 1)
        os.dup2(log_handle.fileno(), 2)
        os.execvp("caffeinate", command)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--since")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.status:
        print(json.dumps(status(args.root, args.log), indent=2, sort_keys=True))
        return
    launch(args.root, args.log, since=args.since)
    deadline = time.monotonic() + 15
    state = status(args.root, args.log)
    while not state["alive"] and time.monotonic() < deadline:
        time.sleep(0.25)
        state = status(args.root, args.log)
    print(json.dumps(state, indent=2, sort_keys=True))
    if not state["alive"]:
        raise SystemExit("collector did not remain alive; inspect the v3 log")


if __name__ == "__main__":
    main()
