"""Freeze the label-blind EventX v4 Polymarket confirmatory cohort."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import glob
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterator

from eventx.settings import REPO_ROOT
from eventx.tasks.audit_v3_historical_feasibility import parse_json_array, parse_utc
from eventx.tasks.build_v2_1_taxonomy import TAXONOMY_VERSION, classify
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file


SOURCE = REPO_ROOT / "data/v4/discovery/future_cohort_feasibility"
ROSTER = SOURCE / "polymarket_active_roster.json"
OUTPUT = REPO_ROOT / "data/v4/confirmatory/cohort_gate"
COHORT = OUTPUT / "cohort.jsonl"
REPORT = OUTPUT / "report.json"
MANIFEST = OUTPUT / "manifest.json"
HOLDOUT_START = "2026-09-06T00:00:00Z"
HOLDOUT_END = "2026-10-30T00:00:00Z"
MINIMUM_MARKETS = 400


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def atomic_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for value in values:
            handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    os.replace(temporary, path)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def main() -> None:
    if any(path.exists() for path in (COHORT, REPORT, MANIFEST)):
        raise SystemExit("v4 confirmatory cohort artifact already exists")
    roster_payload = json.loads(ROSTER.read_text(encoding="utf-8"))
    roster = {
        str(row["market_id"]): row
        for row in roster_payload.get("markets", [])
        if row.get("market_id")
    }
    metadata_paths = [Path(value) for value in sorted(glob.glob(str(SOURCE / "polymarket_metadata_*.jsonl")))]
    if not metadata_paths:
        raise RuntimeError("no source-valid batched Polymarket metadata")
    latest: dict[str, dict[str, Any]] = {}
    for path in metadata_paths:
        for row in read_jsonl(path):
            condition = str(row.get("condition_id") or "")
            if not condition:
                continue
            current = latest.get(condition)
            if current is None or parse_utc(str(row["ingest_ts"])) > parse_utc(
                str(current["ingest_ts"])
            ):
                latest[condition] = row

    counters: Counter[str] = Counter()
    cohort = []
    for market_id, roster_row in sorted(roster.items()):
        counters["active_roster_markets"] += 1
        metadata = latest.get(market_id)
        if metadata is None:
            counters["missing_pre_cutoff_metadata"] += 1
            continue
        outcomes = parse_json_array(metadata.get("outcomes"))
        assets = parse_json_array(metadata.get("clob_token_ids"))
        yes = [index for index, value in enumerate(outcomes) if str(value).lower() == "yes"]
        if len(yes) != 1 or yes[0] >= len(assets):
            counters["no_unique_canonical_yes"] += 1
            continue
        question = str(metadata.get("question") or roster_row.get("question") or "").strip()
        if not question:
            counters["missing_question"] += 1
            continue
        terminal = metadata.get("end_date")
        if not terminal or parse_utc(str(terminal)) < parse_utc(HOLDOUT_END):
            counters["terminal_before_holdout_end"] += 1
            continue
        volume = float(roster_row.get("volume_24h") or 0.0)
        if not volume > 0.0:
            counters["nonpositive_roster_volume"] += 1
            continue
        category, _ = classify(question)
        cohort.append({
            "venue": "polymarket",
            "market_id": market_id,
            "canonical_yes_asset_id": str(assets[yes[0]]),
            "event_cluster": "polymarket:condition:" + market_id,
            "question": question,
            "category": category,
            "market_group": int(hashlib.sha256(("polymarket:" + market_id).encode()).hexdigest(), 16) % 5,
            "selection_volume_24h": volume,
            "selection_liquidity_num": float(roster_row.get("liquidity_num") or 0.0),
            "metadata_ingest_ts": metadata["ingest_ts"],
            "terminal_time": terminal,
            "taxonomy_version": TAXONOMY_VERSION,
        })
    cohort.sort(key=lambda row: row["market_id"])
    atomic_jsonl(COHORT, cohort)
    by_category = Counter(row["category"] for row in cohort)
    by_group = Counter(row["market_group"] for row in cohort)
    as_of = datetime.fromtimestamp(
        int(roster_payload["as_of_ns"]) / 1_000_000_000, tz=timezone.utc
    )
    checks = {
        "at_least_400_markets": len(cohort) >= MINIMUM_MARKETS,
        "at_least_400_event_clusters": len({row["event_cluster"] for row in cohort}) >= MINIMUM_MARKETS,
        "all_unique_canonical_yes": all(bool(row["canonical_yes_asset_id"]) for row in cohort),
        "all_terminal_after_holdout": all(
            parse_utc(str(row["terminal_time"])) >= parse_utc(HOLDOUT_END) for row in cohort
        ),
        "all_positive_selection_volume": all(row["selection_volume_24h"] > 0 for row in cohort),
        "all_groups_nonempty": all(by_group[group] > 0 for group in range(5)),
        "roster_precedes_holdout": as_of < parse_utc(HOLDOUT_START),
        "labels_prices_predictions_or_outcomes_read": False,
    }
    passed = all(
        value is True
        for name, value in checks.items()
        if name != "labels_prices_predictions_or_outcomes_read"
    ) and checks["labels_prices_predictions_or_outcomes_read"] is False
    report = {
        "design_id": "eventx-v4-confirmatory-20260902",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "passed_and_frozen" if passed else "failed",
        "integrity_pass": passed,
        "label_blind": True,
        "selection": {
            "roster_endpoint": "/api/v1/lqt/markets?venue=polymarket",
            "roster_as_of": as_of.isoformat().replace("+00:00", "Z"),
            "metadata_endpoint": "/retrieve",
            "metadata_cutoff_exclusive": "2026-09-02T00:00:00Z",
            "rule": "every active-roster Polymarket condition with positive 24-hour roster volume, pre-cutoff metadata, a nonempty question, exactly one YES asset, and end_date at or after the holdout end",
            "outcome_blind": True,
        },
        "holdout": f"[{HOLDOUT_START}, {HOLDOUT_END})",
        "markets": len(cohort),
        "event_clusters": len({row["event_cluster"] for row in cohort}),
        "by_category": dict(by_category),
        "by_group": {str(group): by_group[group] for group in range(5)},
        "drop_reasons": dict(counters),
        "checks": checks,
        "known_limitation": "Polymarket-only primary confirmation because Lumid could not reconcile the Kalshi active roster to bounded pre-cutoff warehouse metadata and broad activity queries repeatedly exceeded the fixed statement timeout",
        "cohort": {"path": relative(COHORT), "sha256": sha256_file(COHORT)},
        "source_artifacts": [
            {"path": relative(path), "sha256": sha256_file(path)}
            for path in (ROSTER, *metadata_paths)
        ],
    }
    atomic_json(REPORT, report)
    atomic_json(
        MANIFEST,
        {
            "design_id": report["design_id"],
            "status": report["status"],
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in (COHORT, REPORT, Path(__file__).resolve())
            ],
            "source_artifacts": report["source_artifacts"],
        },
    )
    print(json.dumps({
        "status": report["status"],
        "holdout": report["holdout"],
        "markets": report["markets"],
        "event_clusters": report["event_clusters"],
        "by_category": report["by_category"],
        "by_group": report["by_group"],
        "drop_reasons": report["drop_reasons"],
        "checks": report["checks"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
