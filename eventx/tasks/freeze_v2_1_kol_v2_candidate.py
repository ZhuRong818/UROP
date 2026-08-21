"""Freeze the KOL-only v2 candidate before drawing its fresh blind audit."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from eventx.features.v2_1_kol_association_v2 import LEXICAL_SPEC, RULE_VERSION, lexical_spec
from eventx.settings import REPO_ROOT


V1_ROOT = REPO_ROOT / "data" / "v2_1" / "association" / "v1_audit"
OUTPUT_ROOT = REPO_ROOT / "data" / "v2_1" / "association" / "kol_v2_candidate"
RULE_SOURCE = REPO_ROOT / "eventx" / "features" / "v2_1_kol_association_v2.py"
NEWS_V1_SOURCE = REPO_ROOT / "eventx" / "features" / "v2_1_association.py"
DEV_REPORT = V1_ROOT / "kol_v2_opened_development_report.json"
DEV_PREDICTIONS = V1_ROOT / "kol_v2_opened_development_predictions.jsonl"
TAXONOMY = V1_ROOT / "kol_error_taxonomy.json"
TAXONOMY_ROWS = V1_ROOT / "kol_error_taxonomy_rows.jsonl"
ERROR_ANALYSIS = V1_ROOT / "KOL_ERROR_ANALYSIS.md"
V1_FREEZE = V1_ROOT / "audit_freeze_manifest.json"
V1_SCORE = V1_ROOT / "association_audit_report.json"
MANIFEST = OUTPUT_ROOT / "candidate_freeze_manifest.json"


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


def write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise SystemExit(f"refusing to overwrite candidate freeze: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def main() -> None:
    v1_freeze = load(V1_FREEZE)
    v1_score = load(V1_SCORE)
    dev = load(DEV_REPORT)
    taxonomy = load(TAXONOMY)
    spec = lexical_spec()
    if v1_freeze.get("status") != "frozen_failed_development_audit":
        raise SystemExit("v1 failed audit is not frozen")
    if v1_score.get("by_source", {}).get("news", {}).get("status") != "accepted":
        raise SystemExit("news-v1 source was not accepted")
    if v1_score.get("by_source", {}).get("kol", {}).get("status") != "failed":
        raise SystemExit("KOL-v1 source was not failed")
    if dev.get("candidate_rule") != RULE_VERSION or dev.get("development_only") is not True:
        raise SystemExit("opened development diagnostic is not for this candidate")
    if taxonomy.get("status") != "taxonomy_complete":
        raise SystemExit("KOL-v1 error taxonomy is incomplete")
    if spec.get("rule_version") != RULE_VERSION or spec.get("scope") != "kol_only":
        raise SystemExit("lexical specification is not scoped to the KOL-v2 candidate")

    expected_news_hash = v1_freeze["frozen_files"][relative(NEWS_V1_SOURCE)]["sha256"]
    if sha256_file(NEWS_V1_SOURCE) != expected_news_hash:
        raise SystemExit("accepted news-v1 matcher changed; KOL revision must not alter it")
    expected_sources = dev.get("source_hashes", {})
    for path in (RULE_SOURCE, LEXICAL_SPEC):
        if expected_sources.get(relative(path)) != sha256_file(path):
            raise SystemExit(f"development report source hash is stale for {path}")

    paths = [
        RULE_SOURCE,
        LEXICAL_SPEC,
        DEV_REPORT,
        DEV_PREDICTIONS,
        TAXONOMY,
        TAXONOMY_ROWS,
        ERROR_ANALYSIS,
        V1_FREEZE,
        V1_SCORE,
        NEWS_V1_SOURCE,
    ]
    manifest = {
        "candidate_rule": RULE_VERSION,
        "development_diagnostic": dev["v2"],
        "development_diagnostic_validates_candidate": False,
        "freeze_policy": "Matcher source and lexical spec are immutable before fresh blind sampling.",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "frozen_files": {
            relative(path): {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in paths
        },
        "lexical_spec_version": spec["lexical_spec_version"],
        "news_disposition": "accepted_v1_unchanged_not_resampled",
        "opened_development_rows": 150,
        "protocol_id": v1_score["protocol_id"],
        "scope": "kol_only",
        "status": "frozen_candidate_awaiting_fresh_blind_audit",
        "validation_gates": {"hard_candidate_recall_minimum": 0.90, "precision_minimum": 0.85},
    }
    if MANIFEST.exists():
        existing = load(MANIFEST)
        manifest["frozen_at"] = existing.get("frozen_at")
    payload = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    write_once(MANIFEST, payload)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
