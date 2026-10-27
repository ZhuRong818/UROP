"""Audit frozen development trades before EventX v3 label construction.

This task is deliberately label blind.  It verifies the retrieved bytes,
receipts, exact interval coverage, cohort membership, execution fields, and
the cohort's predeclared minimum-activity rule.  It refuses to run after any
historical labels or holdout material have been created.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Iterator

from eventx.settings import REPO_ROOT
from eventx.tasks.export_v3_historical_feasibility import parse_utc, rfc3339


PROTOCOL_PATH = REPO_ROOT / "eventx/release/v3_historical_primary/protocol.json"
PREREG_MANIFEST = (
    REPO_ROOT / "eventx/release/v3_historical_primary/preregistration_manifest.json"
)
POWER_MANIFEST = REPO_ROOT / "data/v3_historical/primary/power/manifest.json"
TRADES_ROOT = REPO_ROOT / "data/v3_historical/primary/development/trades"
OUTPUT_ROOT = REPO_ROOT / "data/v3_historical/primary/development/data_gate"
LABEL_PATH = REPO_ROOT / "data/v3_historical/primary/development/labels.jsonl"
HOLDOUT_ROOT = REPO_ROOT / "data/v3_historical/primary/holdout"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RuntimeError(f"{path}:{line_number} is not a JSON object")
            yield value


def verify_hash_manifest(path: Path) -> tuple[bool, int]:
    value = json.loads(path.read_text(encoding="utf-8"))
    checked = 0
    for artifact in value.get("artifacts", []):
        artifact_path = REPO_ROOT / str(artifact["path"])
        if not artifact_path.is_file():
            raise RuntimeError(f"missing locked artifact: {artifact_path}")
        if sha256_file(artifact_path) != str(artifact["sha256"]):
            raise RuntimeError(f"locked artifact hash mismatch: {artifact_path}")
        checked += 1
    return True, checked


def read_cohort(protocol: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    cohort_path = REPO_ROOT / str(protocol["cohort"]["path"])
    if sha256_file(cohort_path) != str(protocol["cohort"]["sha256"]):
        raise RuntimeError("frozen cohort hash mismatch")
    values: dict[tuple[str, str], dict[str, Any]] = {}
    for row in read_jsonl(cohort_path):
        key = (str(row["venue"]), str(row["market_id"]))
        if key in values:
            raise RuntimeError(f"duplicate frozen cohort key: {key}")
        values[key] = row
    if len(values) != int(protocol["cohort"]["markets"]):
        raise RuntimeError("frozen cohort row count mismatch")
    return values


def exact_interval_coverage(
    artifacts: list[dict[str, Any]], start: datetime, end: datetime
) -> bool:
    intervals = sorted(
        (parse_utc(str(item["start"])), parse_utc(str(item["end_exclusive"])))
        for item in artifacts
    )
    if not intervals or intervals[0][0] != start or intervals[-1][1] != end:
        return False
    cursor = start
    for left, right in intervals:
        if left != cursor or right <= left:
            return False
        cursor = right
    return cursor == end


def scan_venue(
    venue: str,
    manifest: dict[str, Any],
    cohort: dict[tuple[str, str], dict[str, Any]],
    development_start: datetime,
    development_end: datetime,
) -> tuple[dict[str, Any], dict[tuple[str, str], dict[str, Any]]]:
    artifacts = list(manifest["artifacts"])
    allowed = {key for key in cohort if key[0] == venue}
    counts: Counter[tuple[str, str]] = Counter()
    raw_counts: Counter[tuple[str, str]] = Counter()
    active_days: dict[tuple[str, str], set[str]] = defaultdict(set)
    first_ts: dict[tuple[str, str], datetime] = {}
    last_ts: dict[tuple[str, str], datetime] = {}
    totals: Counter[str] = Counter()
    invalid_examples: list[dict[str, Any]] = []
    hash_failures = 0
    receipt_failures = 0
    page_rowcount_failures = 0
    summary_failures = 0

    for page_number, artifact in enumerate(artifacts, start=1):
        paths = {
            "query": REPO_ROOT / str(artifact["query_path"]),
            "data": REPO_ROOT / str(artifact["data_path"]),
            "receipt": REPO_ROOT / str(artifact["receipt_path"]),
        }
        for kind, path in paths.items():
            expected = str(artifact[f"{kind}_sha256"])
            if not path.is_file() or sha256_file(path) != expected:
                hash_failures += 1
        receipt = json.loads(paths["receipt"].read_text(encoding="utf-8"))
        receipt_rows = int(receipt["receipt"]["rowcount"])
        expected_rows = int(artifact["summary"]["rows"])
        if receipt_rows != expected_rows:
            receipt_failures += 1

        page_rows = 0
        page_unique = 0
        page_exact_duplicates = 0
        page_conflicts = 0
        seen: dict[tuple[str, str], tuple[Any, ...]] = {}
        left = parse_utc(str(artifact["start"]))
        right = parse_utc(str(artifact["end_exclusive"]))
        for row in read_jsonl(paths["data"]):
            page_rows += 1
            totals["raw_rows"] += 1
            trade_id = str(row.get("trade_id") or "")
            if venue == "kalshi":
                market_key = (venue, str(row.get("ticker") or ""))
                timestamp_text = str(row.get("created_time") or "")
                price = float(row.get("yes_price")) / 100.0
                notional = float(row.get("count"))
                signature = (market_key, row.get("count"), row.get("yes_price"))
            else:
                market_key = (venue, str(row.get("condition_id") or ""))
                timestamp_text = str(row.get("ts") or "")
                price = float(row.get("price"))
                notional = float(row.get("size"))
                signature = (
                    market_key,
                    str(row.get("asset_id") or ""),
                    row.get("size"),
                    row.get("price"),
                )
            timestamp = parse_utc(timestamp_text)
            raw_counts[market_key] += 1
            issue = None
            if not trade_id:
                issue = "missing_trade_id"
                totals[issue] += 1
            elif market_key not in allowed:
                issue = "out_of_cohort"
                totals[issue] += 1
            elif not (development_start <= timestamp < development_end):
                issue = "outside_development_window"
                totals[issue] += 1
            elif not (left <= timestamp < right):
                issue = "outside_artifact_interval"
                totals[issue] += 1
            elif not math.isfinite(price) or not 0.0 <= price <= 1.0:
                issue = "invalid_price"
                totals[issue] += 1
            elif not math.isfinite(notional) or notional < 0.0:
                issue = "invalid_notional"
                totals[issue] += 1
            elif notional == 0.0:
                issue = "zero_notional_excluded"
                totals[issue] += 1
            elif venue == "polymarket" and str(row.get("asset_id") or "") != str(
                cohort[market_key]["canonical_yes_asset_id"]
            ):
                issue = "noncanonical_polymarket_asset"
                totals[issue] += 1
            if issue and len(invalid_examples) < 20:
                invalid_examples.append(
                    {"issue": issue, "page": page_number, "row": row}
                )

            execution_key = (trade_id, rfc3339(timestamp))
            previous = seen.get(execution_key)
            if previous is not None:
                if previous == signature:
                    page_exact_duplicates += 1
                    totals["exact_duplicate_rows"] += 1
                    continue
                page_conflicts += 1
                totals["conflicting_duplicate_keys"] += 1
                continue
            seen[execution_key] = signature
            page_unique += 1
            if issue is not None:
                continue
            counts[market_key] += 1
            active_days[market_key].add(timestamp.date().isoformat())
            first_ts[market_key] = min(first_ts.get(market_key, timestamp), timestamp)
            last_ts[market_key] = max(last_ts.get(market_key, timestamp), timestamp)

        if page_rows != expected_rows:
            page_rowcount_failures += 1
        summary = artifact["summary"]
        if (
            page_unique != int(summary["unique_trade_keys"])
            or page_exact_duplicates
            != int(summary.get("exact_duplicate_rows_to_collapse", 0))
            or page_conflicts != int(summary.get("conflicting_duplicate_keys", 0))
        ):
            summary_failures += 1

    market_rows: dict[tuple[str, str], dict[str, Any]] = {}
    below_trade_gate = 0
    below_day_gate = 0
    selected_count_disagreements = 0
    selected_day_disagreements = 0
    for key in sorted(allowed):
        frozen = cohort[key]
        observed_trades = int(counts[key])
        observed_days = len(active_days[key])
        selected_trades = int(frozen["trades"])
        selected_days = int(frozen["active_days"])
        if observed_trades < 100:
            below_trade_gate += 1
        if observed_days < 10:
            below_day_gate += 1
        if observed_trades < selected_trades:
            selected_count_disagreements += 1
        if observed_days < selected_days:
            selected_day_disagreements += 1
        market_rows[key] = {
            "venue": venue,
            "market_id": key[1],
            "raw_rows": int(raw_counts[key]),
            "unique_executions": observed_trades,
            "active_utc_days": observed_days,
            "first_trade_ts": rfc3339(first_ts[key]) if key in first_ts else None,
            "last_trade_ts": rfc3339(last_ts[key]) if key in last_ts else None,
            "frozen_selection_trades": selected_trades,
            "frozen_selection_active_days": selected_days,
        }

    fatal_invariant_failure_rows = sum(
        totals[name]
        for name in (
            "missing_trade_id",
            "out_of_cohort",
            "outside_development_window",
            "outside_artifact_interval",
            "invalid_price",
            "invalid_notional",
            "noncanonical_polymarket_asset",
            "conflicting_duplicate_keys",
        )
    )
    exact_coverage = exact_interval_coverage(
        artifacts, development_start, development_end
    )
    report = {
        "venue": venue,
        "cohort_markets": len(allowed),
        "pages": len(artifacts),
        "raw_rows": totals["raw_rows"],
        "unique_executions": sum(counts.values()),
        "exact_duplicate_rows_collapsed": totals["exact_duplicate_rows"],
        "zero_notional_rows_excluded": totals["zero_notional_excluded"],
        "conflicting_duplicate_keys": totals["conflicting_duplicate_keys"],
        "markets_with_any_trade": sum(1 for key in allowed if counts[key] > 0),
        "markets_below_100_unique_executions": below_trade_gate,
        "markets_below_10_active_days": below_day_gate,
        "markets_below_frozen_selection_trade_count": selected_count_disagreements,
        "markets_below_frozen_selection_active_days": selected_day_disagreements,
        "invalid_rows_by_reason": {
            name: totals[name]
            for name in (
                "missing_trade_id",
                "out_of_cohort",
                "outside_development_window",
                "outside_artifact_interval",
                "invalid_price",
                "invalid_notional",
                "zero_notional_excluded",
                "noncanonical_polymarket_asset",
            )
        },
        "invalid_examples": invalid_examples,
        "checks": {
            "source_manifest_integrity_pass": manifest.get("integrity_pass") is True,
            "source_manifest_is_development_only": manifest.get("holdout_prices_read") is False
            and manifest.get("labels_or_outcomes_read") is False,
            "all_artifact_hashes_match": hash_failures == 0,
            "all_receipt_rowcounts_match": receipt_failures == 0,
            "all_physical_page_rowcounts_match": page_rowcount_failures == 0,
            "all_page_summaries_reproduced": summary_failures == 0,
            "exact_half_open_interval_coverage": exact_coverage,
            "no_fatal_invalid_or_out_of_scope_rows": fatal_invariant_failure_rows
            == 0,
            "all_frozen_markets_have_data": all(counts[key] > 0 for key in allowed),
            "all_frozen_markets_retain_100_execution_gate": below_trade_gate == 0,
            "all_frozen_markets_retain_10_active_day_gate": below_day_gate == 0,
            "observed_counts_not_below_frozen_selection_counts": selected_count_disagreements
            == 0,
            "observed_days_not_below_frozen_selection_days": selected_day_disagreements
            == 0,
            "no_conflicting_duplicate_execution_keys": totals[
                "conflicting_duplicate_keys"
            ]
            == 0,
        },
    }
    report["integrity_pass"] = all(report["checks"].values())
    return report, market_rows


def main() -> None:
    if LABEL_PATH.exists():
        raise SystemExit("refusing label-blind gate after development labels exist")
    if HOLDOUT_ROOT.exists():
        raise SystemExit("refusing label-blind gate after historical holdout material exists")
    prereg_ok, prereg_artifacts = verify_hash_manifest(PREREG_MANIFEST)
    power_ok, power_artifacts = verify_hash_manifest(POWER_MANIFEST)
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    cohort = read_cohort(protocol)
    development_start = parse_utc("2026-05-17T00:00:00Z")
    development_end = parse_utc("2026-07-22T00:00:00Z")

    venue_reports: dict[str, Any] = {}
    all_market_rows: dict[tuple[str, str], dict[str, Any]] = {}
    source_manifest_hashes: dict[str, str] = {}
    for venue in ("kalshi", "polymarket"):
        manifest_path = TRADES_ROOT / venue / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_manifest_hashes[relative(manifest_path)] = sha256_file(manifest_path)
        venue_report, market_rows = scan_venue(
            venue,
            manifest,
            cohort,
            development_start,
            development_end,
        )
        venue_reports[venue] = venue_report
        all_market_rows.update(market_rows)

    market_stats_path = OUTPUT_ROOT / "market_stats.jsonl"
    atomic_jsonl(market_stats_path, [all_market_rows[key] for key in sorted(all_market_rows)])
    prior_input_report = json.loads(
        (REPO_ROOT / "data/v3_historical/primary/label_blind_inputs/report.json").read_text()
    )
    provenance_report = json.loads(
        (REPO_ROOT / "data/v3_historical/provenance_audit_v2/report.json").read_text()
    )
    checks = {
        "preregistration_hash_lock_passed": prereg_ok,
        "power_hash_lock_passed": power_ok,
        "both_venue_trade_gates_passed": all(
            report["integrity_pass"] for report in venue_reports.values()
        ),
        "frozen_news_support_gate_passed": prior_input_report.get("integrity_pass")
        is True,
        "frozen_news_provenance_gate_passed": provenance_report.get("integrity_pass")
        is True,
        "market_stats_cover_exact_cohort": len(all_market_rows) == len(cohort),
        "labels_or_outcomes_read": False,
        "holdout_prices_read": False,
    }
    gate_pass = all(
        value is True
        for key, value in checks.items()
        if key not in {"labels_or_outcomes_read", "holdout_prices_read"}
    ) and checks["labels_or_outcomes_read"] is False and checks[
        "holdout_prices_read"
    ] is False
    report_path = OUTPUT_ROOT / "report.json"
    report = {
        "protocol_id": protocol["protocol_id"],
        "created_at": rfc3339(datetime.now(timezone.utc)),
        "status": "passed" if gate_pass else "failed",
        "development_window": {
            "start": rfc3339(development_start),
            "end_exclusive": rfc3339(development_end),
        },
        "label_blind": True,
        "labels_or_outcomes_read": False,
        "holdout_prices_read": False,
        "locked_artifacts_checked": prereg_artifacts + power_artifacts,
        "source_manifest_hashes": source_manifest_hashes,
        "venue_reports": venue_reports,
        "news_support": {
            "documents": prior_input_report["news"]["development_documents"],
            "usable_calendar_days": prior_input_report["news"]["usable_calendar_days"],
            "associations": prior_input_report["development_associations"]["total"],
            "provenance_status": provenance_report.get("status"),
        },
        "market_stats": {
            "path": relative(market_stats_path),
            "sha256": sha256_file(market_stats_path),
            "rows": len(all_market_rows),
        },
        "checks": checks,
        "integrity_pass": gate_pass,
    }
    atomic_json(report_path, report)
    manifest_path = OUTPUT_ROOT / "manifest.json"
    artifacts = [
        PROTOCOL_PATH,
        PREREG_MANIFEST,
        POWER_MANIFEST,
        Path(__file__).resolve(),
        *(REPO_ROOT / path for path in sorted(source_manifest_hashes)),
        market_stats_path,
        report_path,
    ]
    atomic_json(
        manifest_path,
        {
            "protocol_id": protocol["protocol_id"],
            "status": "frozen_label_blind_development_data_gate",
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in artifacts
            ],
            "labels_or_outcomes_read": False,
            "holdout_prices_read": False,
        },
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if not gate_pass:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
