"""Reconcile a Lumid news warehouse snapshot with EventX endpoint receipts.

The output is a compact availability index keyed to warehouse IDs.  It preserves the
frozen rule that ``first_seen_at`` is an EventX retrieval time: Lumid ``ingest_ts`` is
kept as provenance but never substituted for EventX first-seen time.  Warehouse-only
rows therefore become available no earlier than completion of the export.

This task is label-blind and does not read prediction-market outcomes.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

from eventx.settings import REPO_ROOT
from eventx.tasks.collect_v2_3_news_v2 import normalize_url


DEFAULT_EVENTX_SOURCES = (
    REPO_ROOT / "data/v2_1/prospective/raw/news_latest.jsonl",
    REPO_ROOT / "data/v2_3_1/prospective_news/raw/news.jsonl",
    REPO_ROOT / "data/v2_1/association/candidate_retrieval/news_targeted.jsonl",
    REPO_ROOT / "data/v2_2/planning/lumid_subwindow_20260808_20260817/news.jsonl",
    REPO_ROOT / "data/v2_2/planning/lumid_reprobe_20260824_20260827/news.jsonl",
)


def parse_utc(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def iter_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            yield line_number, value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def canonical_url(row: dict[str, Any]) -> str | None:
    value = row.get("url")
    if value in (None, ""):
        return None
    normalized = normalize_url(str(value))
    return normalized or None


def load_eventx_observations(
    paths: list[Path],
    *,
    start: datetime,
    end: datetime,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    observations: dict[str, dict[str, Any]] = {}
    rows_by_path: Counter[str] = Counter()
    rows_by_endpoint: Counter[str] = Counter()
    malformed_rows = 0
    missing_url_rows = 0
    missing_retrieval_rows = 0
    out_of_window_rows = 0
    total_rows = 0

    for path in paths:
        if not path.exists():
            continue
        for _, envelope in iter_jsonl(path):
            total_rows += 1
            record = envelope.get("record")
            if not isinstance(record, dict):
                malformed_rows += 1
                continue
            published = parse_utc(record.get("published_at") or envelope.get("_event_ts"))
            if published is None or not start <= published < end:
                out_of_window_rows += 1
                continue
            normalized = canonical_url(record)
            if normalized is None:
                missing_url_rows += 1
                continue
            retrieved = parse_utc(
                envelope.get("_retrieved_at") or envelope.get("_first_seen_at")
            )
            if retrieved is None:
                missing_retrieval_rows += 1
                continue
            endpoint = str(envelope.get("_source_endpoint") or "<missing>")
            source_path = relative(path)
            rows_by_path[source_path] += 1
            rows_by_endpoint[endpoint] += 1
            current = observations.get(normalized)
            candidate = {
                "first_seen_at": retrieved,
                "published_at": published,
                "source_endpoint": endpoint,
                "source_path": source_path,
            }
            if current is None or retrieved < current["first_seen_at"]:
                observations[normalized] = candidate

    audit = {
        "input_rows": total_rows,
        "in_window_usable_rows": sum(rows_by_path.values()),
        "unique_normalized_urls": len(observations),
        "malformed_rows": malformed_rows,
        "missing_url_rows": missing_url_rows,
        "missing_retrieval_rows": missing_retrieval_rows,
        "out_of_window_rows": out_of_window_rows,
        "rows_by_endpoint": dict(sorted(rows_by_endpoint.items())),
        "rows_by_path": dict(sorted(rows_by_path.items())),
    }
    return observations, audit


def reconcile(
    warehouse_manifest_path: Path,
    eventx_paths: list[Path],
    output_root: Path | None,
) -> dict[str, Any]:
    warehouse_manifest = json.loads(warehouse_manifest_path.read_text(encoding="utf-8"))
    if not warehouse_manifest.get("integrity_pass"):
        raise ValueError("warehouse manifest integrity_pass is not true")
    start = parse_utc(warehouse_manifest["window"]["start_inclusive"])
    end = parse_utc(warehouse_manifest["window"]["end_exclusive"])
    export_seen = parse_utc(warehouse_manifest.get("completed_at"))
    assert start is not None and end is not None and export_seen is not None
    data_path = REPO_ROOT / warehouse_manifest["artifacts"]["data"]["path"]
    if sha256(data_path) != warehouse_manifest["artifacts"]["data"]["sha256"]:
        raise ValueError("warehouse data hash does not match manifest")

    eventx_observations, eventx_audit = load_eventx_observations(
        eventx_paths, start=start, end=end
    )
    if output_root is None:
        output_root = warehouse_manifest_path.parent / "reconciled"
    output_root.mkdir(parents=True, exist_ok=True)
    index_path = output_root / "availability_index.jsonl"
    eventx_only_path = output_root / "eventx_only.jsonl"
    conflicts_path = output_root / "timestamp_conflicts.jsonl"

    warehouse_urls: set[str] = set()
    warehouse_url_rows: Counter[str] = Counter()
    warehouse_publications: defaultdict[str, set[str]] = defaultdict(set)
    warehouse_ids: defaultdict[str, list[int | str | None]] = defaultdict(list)
    warehouse_rows = 0
    for line_number, row in iter_jsonl(data_path):
        warehouse_rows += 1
        normalized = canonical_url(row)
        if normalized is None:
            raise ValueError(f"warehouse row {line_number} has no usable URL")
        published = parse_utc(row.get("published_at"))
        if published is None:
            raise ValueError(f"warehouse row {line_number} has no published_at")
        warehouse_urls.add(normalized)
        warehouse_url_rows[normalized] += 1
        warehouse_publications[normalized].add(rfc3339(published))
        warehouse_ids[normalized].append(row.get("id"))

    timestamp_conflict_urls = {
        url for url, values in warehouse_publications.items() if len(values) > 1
    }
    conflicts_temp = conflicts_path.with_suffix(conflicts_path.suffix + ".tmp")
    with conflicts_temp.open("w", encoding="utf-8") as output:
        for url in sorted(timestamp_conflict_urls):
            output.write(
                json.dumps(
                    {
                        "normalized_url": url,
                        "published_at_values": sorted(warehouse_publications[url]),
                        "quarantine_for_primary_b1": True,
                        "warehouse_ids": warehouse_ids[url],
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                )
                + "\n"
            )
    os.replace(conflicts_temp, conflicts_path)

    first_seen_sources: Counter[str] = Counter()
    overlap_rows = 0
    warehouse_only_rows = 0
    available_after_publication = 0
    temporary = index_path.with_suffix(index_path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        for line_number, row in iter_jsonl(data_path):
            normalized = canonical_url(row)
            if normalized is None:
                raise ValueError(f"warehouse row {line_number} has no usable URL")
            published = parse_utc(row.get("published_at"))
            if published is None:
                raise ValueError(f"warehouse row {line_number} has no published_at")
            observation = eventx_observations.get(normalized)
            if observation is None:
                first_seen = export_seen
                first_seen_source = "warehouse_export_completion"
                first_seen_endpoint = "/retrieve"
                warehouse_only_rows += 1
            else:
                first_seen = observation["first_seen_at"]
                first_seen_source = observation["source_path"]
                first_seen_endpoint = observation["source_endpoint"]
                overlap_rows += 1
            available = max(published, first_seen)
            if available > published:
                available_after_publication += 1
            first_seen_sources[first_seen_source] += 1
            output.write(
                json.dumps(
                    {
                        "available_at": rfc3339(available),
                        "eventx_first_seen_at": rfc3339(first_seen),
                        "eventx_first_seen_endpoint": first_seen_endpoint,
                        "eventx_first_seen_source": first_seen_source,
                        "normalized_url": normalized,
                        "published_at": rfc3339(published),
                        "quarantined_timestamp_conflict": (
                            normalized in timestamp_conflict_urls
                        ),
                        "warehouse_id": row.get("id"),
                        "warehouse_ingest_ts": row.get("ingest_ts"),
                        "warehouse_source": row.get("source"),
                        "warehouse_source_endpoint": row.get("source_endpoint"),
                        "warehouse_source_run_id": row.get("source_run_id"),
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                )
                + "\n"
            )
    os.replace(temporary, index_path)

    eventx_only_urls = sorted(set(eventx_observations) - warehouse_urls)
    eventx_only_temp = eventx_only_path.with_suffix(eventx_only_path.suffix + ".tmp")
    with eventx_only_temp.open("w", encoding="utf-8") as output:
        for url in eventx_only_urls:
            observation = eventx_observations[url]
            output.write(
                json.dumps(
                    {
                        "eventx_first_seen_at": rfc3339(observation["first_seen_at"]),
                        "eventx_first_seen_endpoint": observation["source_endpoint"],
                        "eventx_first_seen_source": observation["source_path"],
                        "normalized_url": url,
                        "published_at": rfc3339(observation["published_at"]),
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                )
                + "\n"
            )
    os.replace(eventx_only_temp, eventx_only_path)

    duplicate_url_rows = sum(
        count - 1 for count in warehouse_url_rows.values() if count > 1
    )
    timestamp_conflict_rows = sum(
        warehouse_url_rows[url] for url in timestamp_conflict_urls
    )
    input_hashes = {
        relative(path): sha256(path) for path in eventx_paths if path.exists()
    }
    input_hashes[relative(warehouse_manifest_path)] = sha256(warehouse_manifest_path)
    input_hashes[relative(data_path)] = sha256(data_path)

    integrity_pass = (
        warehouse_rows == warehouse_manifest["summary"]["rows"]
        and warehouse_rows == warehouse_manifest["retrieve_rowcount"]
        and warehouse_manifest["summary"]["out_of_window_rows"] == 0
    )
    result = {
        "protocol_id": warehouse_manifest.get("protocol_id"),
        "purpose": "label-blind cross-path news coverage and availability reconciliation",
        "created_at": rfc3339(datetime.now(timezone.utc)),
        "label_blind": True,
        "labels_or_outcomes_read": False,
        "warehouse_window": {
            "start_inclusive": rfc3339(start),
            "end_exclusive": rfc3339(end),
            "field": "published_at",
        },
        "warehouse_export_completed_at": rfc3339(export_seen),
        "integrity_pass": integrity_pass,
        "point_in_time_rule": (
            "first_seen_at is earliest successful EventX endpoint receipt; "
            "warehouse-only rows use export completion; available_at is "
            "max(published_at, first_seen_at); Lumid ingest_ts is provenance only"
        ),
        "summary": {
            "warehouse_rows": warehouse_rows,
            "warehouse_unique_normalized_urls": len(warehouse_urls),
            "warehouse_duplicate_url_rows": duplicate_url_rows,
            "warehouse_timestamp_conflict_urls": len(timestamp_conflict_urls),
            "warehouse_timestamp_conflict_rows": timestamp_conflict_rows,
            "warehouse_rows_observed_by_eventx_endpoint": overlap_rows,
            "warehouse_rows_first_seen_at_export": warehouse_only_rows,
            "warehouse_rows_available_after_publication": available_after_publication,
            "eventx_unique_normalized_urls": len(eventx_observations),
            "eventx_only_urls": len(eventx_only_urls),
            "first_seen_rows_by_source": dict(sorted(first_seen_sources.items())),
            "eventx_input_audit": eventx_audit,
        },
        "input_hashes": dict(sorted(input_hashes.items())),
        "artifacts": {
            "availability_index": {
                "path": relative(index_path),
                "bytes": index_path.stat().st_size,
                "sha256": sha256(index_path),
            },
            "eventx_only": {
                "path": relative(eventx_only_path),
                "bytes": eventx_only_path.stat().st_size,
                "sha256": sha256(eventx_only_path),
            },
            "timestamp_conflicts": {
                "path": relative(conflicts_path),
                "bytes": conflicts_path.stat().st_size,
                "sha256": sha256(conflicts_path),
            },
        },
    }
    manifest_path = output_root / "reconciliation_manifest.json"
    write_json(manifest_path, result)
    return {"manifest": relative(manifest_path), **result}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warehouse-manifest", type=Path, required=True)
    parser.add_argument(
        "--eventx-source",
        action="append",
        type=Path,
        default=None,
        help="EventX news JSONL receipt path; repeat to provide several",
    )
    parser.add_argument("--output-root", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sources = args.eventx_source or list(DEFAULT_EVENTX_SOURCES)
    result = reconcile(args.warehouse_manifest, sources, args.output_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["integrity_pass"]:
        raise SystemExit("reconciliation integrity failed")


if __name__ == "__main__":
    main()
