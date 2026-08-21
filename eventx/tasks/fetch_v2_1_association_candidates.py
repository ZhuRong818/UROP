"""Fetch targeted, pre-label news/KOL candidates for the frozen v2.1 cohort."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from eventx.features.v2_1_association import GENERIC, market_spec
from eventx.ingest.client import FindataClient
from eventx.settings import REPO_ROOT


DEFAULT_PROTOCOL = REPO_ROOT / "eventx" / "release" / "v2_1" / "protocol.json"
DEFAULT_COHORT = REPO_ROOT / "data" / "v2_1" / "cohort" / "selected_markets.jsonl"
DEFAULT_COHORT_MANIFEST = (
    REPO_ROOT / "data" / "v2_1" / "cohort" / "cohort_freeze_manifest.json"
)
DEFAULT_OUTPUT = REPO_ROOT / "data" / "v2_1" / "association" / "candidate_retrieval"


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    yield value


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def response_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        for key in ("data", "articles", "tweets", "results", "items"):
            rows = value.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def timestamp_for(source: str, row: dict[str, Any]) -> str | None:
    value = row.get("published_at") if source == "news" else row.get("created_at")
    return str(value) if value else None


def queries_for(question: str, category: str) -> list[str]:
    spec = market_spec(question, category)
    queries: list[str] = []
    if spec.phrases:
        cleaned = " ".join(
            token
            for token in spec.phrases[0].split()
            if token.lower() not in GENERIC
        )
        if cleaned:
            queries.append(cleaned)
    anchors = [
        anchor
        for anchor in sorted(spec.anchors, key=lambda value: (-len(value), value))
        if anchor not in GENERIC and anchor not in {"and", "control", "feb", "u.s"}
    ]
    event_terms = list(spec.event_terms)
    if anchors:
        focused = [*anchors[:2], *event_terms[:1]]
        queries.append(" ".join(focused))
    elif event_terms:
        queries.append(" ".join(event_terms[:2]))
    return list(dict.fromkeys(query.strip() for query in queries if len(query.strip()) >= 3))


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    parser.add_argument("--cohort-manifest", type=Path, default=DEFAULT_COHORT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--rpm", type=int, default=35)
    args = parser.parse_args()

    protocol = load_object(args.protocol)
    cohort_manifest = load_object(args.cohort_manifest)
    if cohort_manifest.get("status") != "frozen":
        raise SystemExit("cohort is not frozen")
    if sha256_file(args.cohort) != cohort_manifest.get("output", {}).get("sha256"):
        raise SystemExit("cohort hash mismatch")
    markets = list(read_jsonl(args.cohort))
    query_markets: dict[str, list[str]] = {}
    for market in markets:
        for query in queries_for(str(market["question"]), str(market["category"])):
            query_markets.setdefault(query, []).append(str(market["market_id"]))

    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    outputs: dict[str, list[dict[str, Any]]] = {"news": [], "kol": []}
    query_report: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, str]] = []
    seen: dict[str, set[str]] = {"news": set(), "kol": set()}
    endpoints = {"news": "/news/search", "kol": "/kols/tweets/search"}
    with FindataClient(rpm=args.rpm, timeout=60.0) as client:
        for source, endpoint in endpoints.items():
            for query in sorted(query_markets):
                try:
                    rows = response_rows(client.get(endpoint, q=query, limit=args.limit))
                except Exception as exc:
                    errors.append(
                        {
                            "error": f"{type(exc).__name__}: {exc}"[:500],
                            "query": query,
                            "source": source,
                        }
                    )
                    continue
                retained = 0
                for row in rows:
                    natural = str(row.get("url") or row.get("id") or stable_hash(row))
                    record_key = stable_hash([source, natural])
                    if record_key in seen[source]:
                        continue
                    seen[source].add(record_key)
                    outputs[source].append(
                        {
                            "_event_ts": timestamp_for(source, row),
                            "_protocol_id": protocol["protocol_id"],
                            "_record_key": record_key,
                            "_retrieved_at": retrieved_at,
                            "_search_market_ids": sorted(set(query_markets[query])),
                            "_search_query": query,
                            "_source": f"{source}_targeted_search",
                            "_source_endpoint": endpoint,
                            "record": row,
                        }
                    )
                    retained += 1
                query_report[f"{source}:{query}"] = {
                    "response_rows": len(rows),
                    "unique_rows_retained": retained,
                }

    output_paths = {
        source: args.output / f"{source}_targeted.jsonl"
        for source in outputs
    }
    for source, rows in outputs.items():
        rows.sort(key=lambda row: row["_record_key"])
        atomic_jsonl(output_paths[source], rows)
    report = {
        "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "errors": errors,
        "input_hashes": {
            relative(args.cohort): sha256_file(args.cohort),
            relative(args.cohort_manifest): sha256_file(args.cohort_manifest),
            relative(args.protocol): sha256_file(args.protocol),
        },
        "label_blind": True,
        "labels_read": [],
        "limit_per_query": args.limit,
        "outputs": {
            source: {
                "path": relative(path),
                "rows": len(outputs[source]),
                "sha256": sha256_file(path),
            }
            for source, path in output_paths.items()
        },
        "protocol_id": protocol["protocol_id"],
        "queries": len(query_markets),
        "query_report": query_report,
        "status": "complete" if not errors else "complete_with_errors",
    }
    atomic_json(args.output / "retrieval_report.json", report)
    print(
        json.dumps(
            {
                "errors": len(errors),
                "queries": len(query_markets),
                "rows": {source: len(rows) for source, rows in outputs.items()},
                "status": report["status"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
