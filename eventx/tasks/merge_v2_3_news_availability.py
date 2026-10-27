"""Merge verified EventX news-availability receipts without backdating articles.

Repeated Lumid warehouse exports may contain the same warehouse article.  A later
reconciliation must not replace an earlier, already-recorded EventX availability
receipt.  This label-blind task verifies every reconciliation artifact, selects the
earliest valid EventX first-seen time per warehouse ID, recomputes
``available_at=max(published_at, eventx_first_seen_at)``, and quarantines publication
timestamp conflicts across all supplied snapshots.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

from eventx.settings import REPO_ROOT


IMPLEMENTATION_MANIFEST = (
    REPO_ROOT / "eventx/release/v2_3_3/implementation_manifest.json"
)

def parse_utc(value: Any) -> datetime:
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


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            yield value


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def atomic_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    os.replace(temporary, path)


def id_sort(value: str) -> tuple[int, int | str]:
    try:
        return (0, int(value))
    except ValueError:
        return (1, value)


def load_receipts(
    manifest_paths: list[Path],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    candidates: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    input_hashes: dict[str, str] = {}
    for supplied_path in manifest_paths:
        manifest_path = resolve(supplied_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("integrity_pass") is not True:
            raise ValueError(f"reconciliation integrity failed: {manifest_path}")
        if manifest.get("labels_or_outcomes_read") is not False:
            raise ValueError(f"reconciliation is not label-blind: {manifest_path}")
        artifact = manifest.get("artifacts", {}).get("availability_index", {})
        index_path = resolve(Path(str(artifact.get("path", ""))))
        if not index_path.is_file():
            raise ValueError(f"availability index missing: {index_path}")
        if index_path.stat().st_size != artifact.get("bytes"):
            raise ValueError(f"availability byte count mismatch: {index_path}")
        if sha256(index_path) != artifact.get("sha256"):
            raise ValueError(f"availability hash mismatch: {index_path}")
        manifest_name = relative(manifest_path)
        input_hashes[manifest_name] = sha256(manifest_path)
        input_hashes[relative(index_path)] = sha256(index_path)
        for row in iter_jsonl(index_path):
            warehouse_id = str(row.get("warehouse_id") or "")
            if not warehouse_id:
                raise ValueError(f"missing warehouse_id in {index_path}")
            published = parse_utc(row.get("published_at"))
            first_seen = parse_utc(row.get("eventx_first_seen_at"))
            available = parse_utc(row.get("available_at"))
            if available != max(published, first_seen):
                raise ValueError(
                    f"invalid availability rule for warehouse ID {warehouse_id}"
                )
            candidates[warehouse_id].append(
                {
                    **row,
                    "_receipt_manifest": manifest_name,
                    "_receipt_manifest_sha256": input_hashes[manifest_name],
                }
            )
    return dict(candidates), dict(sorted(input_hashes.items()))


def merge(
    manifest_paths: list[Path], output_root: Path
) -> dict[str, Any]:
    candidates, input_hashes = load_receipts(manifest_paths)
    publications_by_url: defaultdict[str, set[str]] = defaultdict(set)
    identity_conflict_ids: set[str] = set()
    duplicate_receipt_ids = 0
    earlier_receipt_ids = 0

    for warehouse_id, rows in candidates.items():
        if len(rows) > 1:
            duplicate_receipt_ids += 1
        urls = {str(row.get("normalized_url") or "") for row in rows}
        publications = {rfc3339(parse_utc(row["published_at"])) for row in rows}
        if "" in urls or len(urls) != 1 or len(publications) != 1:
            identity_conflict_ids.add(warehouse_id)
        for row in rows:
            publications_by_url[str(row.get("normalized_url") or "")].add(
                rfc3339(parse_utc(row["published_at"]))
            )

    conflicting_urls = {
        url for url, publications in publications_by_url.items()
        if url and len(publications) > 1
    }
    merged: list[dict[str, Any]] = []
    for warehouse_id in sorted(candidates, key=id_sort):
        rows = candidates[warehouse_id]
        ordered = sorted(
            rows,
            key=lambda row: (
                parse_utc(row["eventx_first_seen_at"]),
                str(row["_receipt_manifest"]),
            ),
        )
        selected = ordered[0]
        if len(rows) > 1 and parse_utc(selected["eventx_first_seen_at"]) < max(
            parse_utc(row["eventx_first_seen_at"]) for row in rows
        ):
            earlier_receipt_ids += 1
        published = parse_utc(selected["published_at"])
        first_seen = parse_utc(selected["eventx_first_seen_at"])
        normalized_url = str(selected.get("normalized_url") or "")
        quarantined = (
            warehouse_id in identity_conflict_ids
            or normalized_url in conflicting_urls
            or any(bool(row.get("quarantined_timestamp_conflict")) for row in rows)
        )
        output = {
            key: value for key, value in selected.items() if not key.startswith("_")
        }
        output.update(
            {
                "availability_receipt_count": len(rows),
                "availability_receipt_manifest": selected["_receipt_manifest"],
                "availability_receipt_manifest_sha256": selected[
                    "_receipt_manifest_sha256"
                ],
                "available_at": rfc3339(max(published, first_seen)),
                "eventx_first_seen_at": rfc3339(first_seen),
                "quarantined_timestamp_conflict": quarantined,
            }
        )
        merged.append(output)

    conflict_rows = [
        {
            "normalized_url": url,
            "published_at_values": sorted(publications_by_url[url]),
            "quarantine_for_primary_b1": True,
            "reason": "publication_timestamp_conflict_across_reconciliation_receipts",
        }
        for url in sorted(conflicting_urls)
    ]
    index_path = output_root / "availability_index.jsonl"
    conflict_path = output_root / "cross_snapshot_timestamp_conflicts.jsonl"
    atomic_jsonl(index_path, merged)
    atomic_jsonl(conflict_path, conflict_rows)
    report = {
        "code": {
            "path": relative(Path(__file__)),
            "sha256": sha256(Path(__file__)),
        },
        "created_at": rfc3339(datetime.now(timezone.utc)),
        "input_hashes": input_hashes,
        "integrity_pass": not identity_conflict_ids,
        "label_blind": True,
        "labels_or_outcomes_read": False,
        "implementation_manifest": {
            "path": relative(IMPLEMENTATION_MANIFEST),
            "sha256": sha256(IMPLEMENTATION_MANIFEST),
        },
        "point_in_time_rule": (
            "select the earliest verified EventX first-seen receipt per warehouse ID; "
            "available_at=max(published_at,eventx_first_seen_at); quarantine any "
            "publication-time conflict across snapshots"
        ),
        "protocol_id": "eventx-v2.3-news-availability-clarifications-20260817",
        "summary": {
            "cross_snapshot_timestamp_conflict_urls": len(conflicting_urls),
            "duplicate_receipt_warehouse_ids": duplicate_receipt_ids,
            "earlier_receipt_preserved_warehouse_ids": earlier_receipt_ids,
            "identity_conflict_warehouse_ids": len(identity_conflict_ids),
            "input_receipts": len(manifest_paths),
            "input_rows": sum(len(rows) for rows in candidates.values()),
            "output_rows": len(merged),
            "quarantined_output_rows": sum(
                bool(row["quarantined_timestamp_conflict"]) for row in merged
            ),
        },
        "artifacts": {
            "availability_index": {
                "bytes": index_path.stat().st_size,
                "path": relative(index_path),
                "sha256": sha256(index_path),
            },
            "cross_snapshot_timestamp_conflicts": {
                "bytes": conflict_path.stat().st_size,
                "path": relative(conflict_path),
                "sha256": sha256(conflict_path),
            },
        },
    }
    report_path = output_root / "merge_manifest.json"
    atomic_json(report_path, report)
    return {"manifest": relative(report_path), **report}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reconciliation-manifest",
        action="append",
        type=Path,
        required=True,
        help="verified reconciliation manifest; repeat for each snapshot",
    )
    parser.add_argument("--output-root", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = resolve(args.output_root)
    report = merge(args.reconciliation_manifest, output_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["integrity_pass"]:
        raise SystemExit("availability merge integrity failed")


if __name__ == "__main__":
    main()
