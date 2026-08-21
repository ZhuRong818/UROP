"""Seal the fresh KOL-v2 blind packet and hidden key before review."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT


ROOT = REPO_ROOT / "data" / "v2_1" / "association" / "kol_v2_audit"
PREPARATION = ROOT / "kol_v2_audit_preparation_report.json"
KEY = ROOT / "kol_v2_blind_key.jsonl"
POOL = ROOT / "kol_v2_candidate_pool.jsonl"
BLIND = REPO_ROOT / "eventx" / "release" / "v2_1" / "eventx_v2_1_kol_v2_blind_review.jsonl"
GUIDE = REPO_ROOT / "eventx" / "release" / "v2_1" / "KOL_V2_BLIND_REVIEW_GUIDE.md"
CANDIDATE_FREEZE = REPO_ROOT / "data" / "v2_1" / "association" / "kol_v2_candidate" / "candidate_freeze_manifest.json"
EXCLUSIONS = REPO_ROOT / "data" / "v2_1" / "association" / "v1_audit" / "opened_pair_content_exclusions.jsonl"
MANIFEST = ROOT / "kol_v2_audit_freeze_manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_once(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.read_bytes() != payload:
            raise SystemExit(f"refusing to overwrite audit freeze: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def main() -> None:
    preparation = load(PREPARATION)
    candidate = load(CANDIDATE_FREEZE)
    if preparation.get("status") != "awaiting_independent_blind_review":
        raise SystemExit("audit preparation is not awaiting review")
    if preparation.get("label_blind") is not True or preparation.get("labels_read") != []:
        raise SystemExit("audit preparation lost its blind seal")
    if preparation.get("fresh_unopened_pairs") is not True:
        raise SystemExit("audit preparation does not certify unopened pairs")
    if candidate.get("status") != "frozen_candidate_awaiting_fresh_blind_audit":
        raise SystemExit("candidate freeze status is invalid")
    for name, path in (("blind_key", KEY), ("blind_review", BLIND), ("candidate_pool", POOL)):
        expected = preparation["outputs"][name]["sha256"]
        if sha256_file(path) != expected:
            raise SystemExit(f"preparation hash mismatch for {path}")

    blind = read_jsonl(BLIND)
    key = read_jsonl(KEY)
    if len(blind) != 150 or len(key) != 150:
        raise SystemExit("fresh KOL audit must contain 150 rows")
    blind_ids = [row.get("audit_id") for row in blind]
    key_ids = [row.get("audit_id") for row in key]
    if len(set(blind_ids)) != 150 or set(blind_ids) != set(key_ids):
        raise SystemExit("blind/key audit IDs are not unique and identical")
    for row in blind:
        if any(row.get(field) for field in ("review_label", "review_confidence", "review_rationale", "reviewer")):
            raise SystemExit("blind review packet already contains review values")

    exclusions = read_jsonl(EXCLUSIONS)
    pair_keys = {(row["market_id"], row["content_hash"]) for row in exclusions}
    pair_ids = {row["pair_id"] for row in exclusions}
    if any(
        (row["market_id"], row["content_hash"]) in pair_keys or row["pair_id"] in pair_ids
        for row in key
    ):
        raise SystemExit("opened v1 pair leaked into frozen KOL-v2 audit")

    frozen_paths = [PREPARATION, KEY, POOL, BLIND, GUIDE, CANDIDATE_FREEZE, EXCLUSIONS]
    manifest = {
        "association_rule": preparation["association_rule"],
        "blind_review_rows": len(blind),
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "frozen_files": {
            relative(path): {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in frozen_paths
        },
        "independent_review_required": True,
        "label_blind": True,
        "opened_pair_leakage": 0,
        "predictions_hidden": True,
        "protocol_id": preparation["protocol_id"],
        "status": "frozen_awaiting_independent_blind_review",
        "validation_gates": candidate["validation_gates"],
    }
    if MANIFEST.exists():
        existing = load(MANIFEST)
        manifest["frozen_at"] = existing.get("frozen_at")
    payload = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    write_once(MANIFEST, payload)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
