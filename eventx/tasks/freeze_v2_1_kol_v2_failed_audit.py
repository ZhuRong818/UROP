"""Seal the failed KOL-v2 audit and extend the opened-pair exclusion ledger."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from eventx.settings import REPO_ROOT


ROOT = REPO_ROOT / "data" / "v2_1" / "association" / "kol_v2_audit"
V1_ROOT = REPO_ROOT / "data" / "v2_1" / "association" / "v1_audit"
AUDIT_FREEZE = ROOT / "kol_v2_audit_freeze_manifest.json"
KEY = ROOT / "kol_v2_blind_key.jsonl"
REVIEW = REPO_ROOT / "eventx" / "release" / "v2_1" / "eventx_v2_1_kol_v2_blind_review_completed.jsonl"
REPORT = ROOT / "kol_v2_audit_report.json"
SCORING_CONTRACT = ROOT / "kol_v2_scoring_contract.json"
SCORER = REPO_ROOT / "eventx" / "tasks" / "score_v2_1_kol_v2_audit.py"
V1_EXCLUSIONS = V1_ROOT / "opened_pair_content_exclusions.jsonl"
CUMULATIVE_EXCLUSIONS = ROOT / "opened_pair_content_exclusions_through_kol_v2.jsonl"
MANIFEST = ROOT / "kol_v2_failed_audit_result_manifest.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def indexed(path: Path) -> dict[str, dict[str, Any]]:
    rows = read_jsonl(path)
    result = {str(row.get("audit_id") or ""): row for row in rows}
    if "" in result or len(result) != len(rows):
        raise ValueError(f"{path} has missing or duplicate audit IDs")
    return result


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode()


def write_once(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.read_bytes() != payload:
            raise SystemExit(f"refusing to overwrite frozen result artifact: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def main() -> None:
    audit_freeze = load(AUDIT_FREEZE)
    report = load(REPORT)
    contract = load(SCORING_CONTRACT)
    if audit_freeze.get("status") != "frozen_awaiting_independent_blind_review":
        raise SystemExit("fresh KOL-v2 audit was not frozen before review")
    if report.get("status") != "failed":
        raise SystemExit("KOL-v2 audit result is not failed")
    if report.get("association_rule") != audit_freeze.get("association_rule"):
        raise SystemExit("audit result rule mismatch")
    if report.get("input_hashes", {}).get(relative(REVIEW)) != sha256_file(REVIEW):
        raise SystemExit("completed-review hash does not match scored report")
    if contract.get("scorer", {}).get("sha256") != sha256_file(SCORER):
        raise SystemExit("scorer changed after its pre-review contract")
    if contract.get("audit_freeze_manifest", {}).get("sha256") != sha256_file(AUDIT_FREEZE):
        raise SystemExit("audit freeze changed after its scoring contract")

    key = indexed(KEY)
    review = indexed(REVIEW)
    if len(key) != 150 or set(key) != set(review):
        raise SystemExit("completed review does not cover the exact 150-row key")
    uncertain = sum(row.get("review_label") == "uncertain" for row in review.values())
    if uncertain != int(report.get("uncertain_rows", -1)):
        raise SystemExit("completed-review uncertainty count differs from report")

    combined: dict[tuple[str, str], dict[str, Any]] = {}
    for row in read_jsonl(V1_EXCLUSIONS):
        item = {
            "audit_id": row["audit_id"],
            "content_hash": row["content_hash"],
            "doc_id": row["doc_id"],
            "market_id": row["market_id"],
            "opened_in": "association_v1_audit",
            "pair_id": row["pair_id"],
            "source": row["source"],
        }
        combined[(item["market_id"], item["content_hash"])] = item
    for audit_id, row in key.items():
        item = {
            "audit_id": audit_id,
            "content_hash": row["content_hash"],
            "doc_id": row["doc_id"],
            "market_id": row["market_id"],
            "opened_in": "kol_v2_audit",
            "pair_id": row["pair_id"],
            "source": row["source"],
        }
        pair_key = (item["market_id"], item["content_hash"])
        if pair_key in combined:
            raise SystemExit("fresh KOL-v2 review overlaps an earlier opened pair")
        combined[pair_key] = item
    exclusions = sorted(combined.values(), key=lambda row: (row["source"], row["market_id"], row["content_hash"]))
    if len(exclusions) != 450:
        raise SystemExit(f"expected 450 cumulative opened pairs, found {len(exclusions)}")
    write_once(CUMULATIVE_EXCLUSIONS, jsonl_bytes(exclusions))

    paths = [
        AUDIT_FREEZE,
        KEY,
        REVIEW,
        REPORT,
        SCORING_CONTRACT,
        SCORER,
        V1_EXCLUSIONS,
        CUMULATIVE_EXCLUSIONS,
    ]
    manifest = {
        "association_rule": report["association_rule"],
        "audit_disposition": "failed_opened_development_material_do_not_reuse_for_validation",
        "failed_at_gates": report["failures"],
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "frozen_files": {
            relative(path): {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in paths
        },
        "metrics": {
            "confusion": report["confusion"],
            "f1": report["f1"],
            "hard_candidate_recall": report["hard_candidate_recall"],
            "precision": report["precision"],
            "uncertain_rows": report["uncertain_rows"],
        },
        "opened_pairs_cumulative": len(exclusions),
        "opened_pairs_from_this_audit": len(key),
        "protocol_id": report["protocol_id"],
        "status": "frozen_failed_development_audit",
    }
    if MANIFEST.exists():
        existing = load(MANIFEST)
        manifest["frozen_at"] = existing.get("frozen_at")
    write_once(MANIFEST, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
