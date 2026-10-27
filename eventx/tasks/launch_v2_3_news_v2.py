"""Launch or inspect the detached EventX v2.3 news implementation-v2 collector."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import time

from eventx.settings import REPO_ROOT


DEFAULT_ROOT = REPO_ROOT / "data" / "v2_3_1" / "prospective_news"
DEFAULT_LOG = REPO_ROOT / "data" / "v2_3_1" / "logs" / "news_collector.log"
DEFAULT_UNRESOLVED_START = "2026-08-08T00:00:00Z"


def read_pid(root: Path) -> int | None:
    path = root / "collector.lock"
    if not path.is_file():
        return None
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None


def process_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def status(root: Path, log_path: Path) -> dict[str, object]:
    pid = read_pid(root)
    health_path = root / "health.json"
    receipt_path = root / "launch_receipt.json"
    return {
        "alive": process_alive(pid),
        "health_exists": health_path.is_file(),
        "health_path": relative(health_path),
        "launch_receipt_exists": receipt_path.is_file(),
        "launch_receipt_path": relative(receipt_path),
        "log_path": relative(log_path),
        "pid": pid,
    }


def launch(
    root: Path,
    log_path: Path,
    *,
    since: str | None,
    unresolved_start: str,
    legacy_pid: int | None,
) -> None:
    current = read_pid(root)
    if process_alive(current):
        raise SystemExit(f"collector already running with PID {current}")
    root.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    state_exists = (root / "state" / "news_collector.sqlite3").is_file()
    if not state_exists and since is None:
        since = (
            datetime.now(timezone.utc) - timedelta(minutes=5)
        ).isoformat().replace("+00:00", "Z")

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
        sys.executable,
        "-m",
        "eventx.tasks.collect_v2_3_news_v2",
        "--root",
        str(root),
    ]
    if not state_exists:
        assert since is not None
        command.extend(["--since", since, "--unresolved-start", unresolved_start])
        if legacy_pid is not None:
            command.extend(["--legacy-pid", str(legacy_pid)])
    with Path("/dev/null").open("rb") as stdin_handle, log_path.open("ab") as log_handle:
        os.dup2(stdin_handle.fileno(), 0)
        os.dup2(log_handle.fileno(), 1)
        os.dup2(log_handle.fileno(), 2)
        os.execv(sys.executable, command)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--since")
    parser.add_argument("--unresolved-start", default=DEFAULT_UNRESOLVED_START)
    parser.add_argument("--legacy-pid", type=int, default=94663)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    if args.status:
        print(json.dumps(status(args.root, args.log), indent=2, sort_keys=True))
        return
    launch(
        args.root,
        args.log,
        since=args.since,
        unresolved_start=args.unresolved_start,
        legacy_pid=args.legacy_pid,
    )
    deadline = time.monotonic() + 15
    state = status(args.root, args.log)
    while not state["alive"] and time.monotonic() < deadline:
        time.sleep(0.25)
        state = status(args.root, args.log)
    print(json.dumps(state, indent=2, sort_keys=True))
    if not state["alive"]:
        raise SystemExit("collector did not remain alive; inspect the log")


if __name__ == "__main__":
    main()
