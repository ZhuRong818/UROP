"""Bounded, resumable read-only Lumid catalog/provenance recovery for V5.

No price, outcome or holdout endpoints are called. Credentials stay in settings.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

import httpx

from eventx.settings import ApiSettings, REPO_ROOT

OUTPUT = REPO_ROOT / "data/v5/provenance_recovery_20260908"


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("--path", help="Read-only catalog/OpenAPI path")
    parser.add_argument("--sql-file", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_]+", args.name) or bool(args.path) == bool(args.sql_file):
        raise ValueError("Use a safe name and exactly one path or SQL file")
    if args.path and not (args.path == "/openapi.json" or args.path.startswith("/catalog/")):
        raise ValueError("Only catalog/OpenAPI GET routes allowed")
    sql = args.sql_file.read_text() if args.sql_file else None
    if sql:
        if (not re.match(r"\s*(SELECT|WITH)\b", sql, re.I)
                or re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|COPY|TRUNCATE)\b", sql, re.I)
                or ";" in sql):
            raise ValueError("Only a single read-only SELECT/CTE query allowed")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT / f"{args.name}.json"
    if report_path.exists():
        raise FileExistsError("Use a new attempt name; evidence is append-only")
    settings = ApiSettings.from_env()
    report = {"started_at": now(), "name": args.name, "method": "POST" if sql else "GET",
              "path": "/retrieve" if sql else args.path, "sql": sql,
              "outcomes_requested": False}
    try:
        with httpx.Client(base_url=settings.base_url,
                          headers={"Authorization": f"Bearer {settings.token}"},
                          timeout=40, follow_redirects=False) as client:
            response = (client.post("/retrieve", json={"sql": sql, "output_format": "jsonl"})
                        if sql else client.get(args.path))
            report["http_status"] = response.status_code
            if response.is_error:
                # Avoid persisting arbitrary reflected headers or secret-bearing bodies.
                report["status"] = "http_error"
            elif sql:
                receipt = response.json()
                report["receipt"] = {k: receipt.get(k) for k in
                                     ["run_id", "rowcount", "size_bytes", "materialized_uri"]}
                uri = receipt.get("materialized_uri", "")
                parsed = urlparse(uri)
                if parsed.scheme or parsed.netloc or not uri.startswith("/blobs/"):
                    raise ValueError("Reject non-local materialized URI")
                if (receipt.get("size_bytes") or 0) > 8_000_000:
                    raise ValueError("Result exceeds bounded download budget")
                with client.stream("GET", uri) as downloaded:
                    report["download_status"] = downloaded.status_code
                    downloaded.raise_for_status()
                    raw = bytearray()
                    for chunk in downloaded.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 8_000_000:
                            raise ValueError("Streaming result exceeds download budget")
                rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
                if len(rows) != receipt["rowcount"]:
                    raise ValueError("Download count differs from source receipt")
                path = OUTPUT / f"{args.name}.jsonl"
                path.write_bytes(raw)
                report.update(status="complete", rows=len(rows),
                              data_sha256=hashlib.sha256(raw).hexdigest(), data_path=str(path.relative_to(REPO_ROOT)))
            else:
                data = response.json()
                path = OUTPUT / f"{args.name}_payload.json"
                path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
                report.update(status="complete", data_path=str(path.relative_to(REPO_ROOT)),
                              data_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    except (httpx.HTTPError, ValueError, KeyError) as error:
        report.update(status="failed", error_type=type(error).__name__)
    report["completed_at"] = now()
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"sql", "receipt"}}, indent=2))
    if report["status"] != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
