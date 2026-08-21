"""Launch or inspect the detached EventX v2.1 prospective collector."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

from eventx.settings import REPO_ROOT


DEFAULT_ROOT = REPO_ROOT / "data" / "v2_1" / "prospective"
DEFAULT_LOG = REPO_ROOT / "data" / "v2_1" / "logs" / "prospective_collector.log"


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
        # Sandboxed status probes may not be allowed to signal an unsandboxed daemon,
        # but permission denial proves that the PID exists.
        return True
    except OSError:
        return False
    return True


def status(root: Path, log_path: Path) -> dict[str, object]:
    pid = read_pid(root)
    health_path = root / "health.json"
    return {
        "alive": process_alive(pid),
        "health_exists": health_path.is_file(),
        "health_path": str(health_path.relative_to(REPO_ROOT)),
        "log_path": str(log_path.relative_to(REPO_ROOT)),
        "pid": pid,
    }


def launch(root: Path, log_path: Path) -> None:
    current = read_pid(root)
    if process_alive(current):
        raise SystemExit(f"collector already running with PID {current}")
    root.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

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
    with Path("/dev/null").open("rb") as stdin_handle, log_path.open("ab") as log_handle:
        os.dup2(stdin_handle.fileno(), 0)
        os.dup2(log_handle.fileno(), 1)
        os.dup2(log_handle.fileno(), 2)
        os.execv(
            sys.executable,
            [
                sys.executable,
                "-m",
                "eventx.tasks.collect_v2_1_prospective",
                "--root",
                str(root),
            ],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        print(json.dumps(status(args.root, args.log), indent=2, sort_keys=True))
        return

    launch(args.root, args.log)
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
