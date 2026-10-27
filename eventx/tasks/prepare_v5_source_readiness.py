"""Stage outcome-blind V5 provenance inputs from explicitly allowlisted local files.

This does not create eligible examples, infer verified families, or train a model.
Only the opened discovery window is inventoried; no holdout outcome files are read.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
START = "2026-05-17T00:00:00+00:00"
END = "2026-07-22T00:00:00+00:00"
INDEX = Path("data/v3_1_historical/primary/development/prepared/market_index.jsonl")
PREPARED_MANIFEST = INDEX.parent / "manifest.json"
NEWS = Path("data/v3_historical/primary/label_blind_inputs/news.jsonl")
NEWS_RECEIPT = NEWS.parent / "news_receipt.json"
RAW = Path("data/v3_historical/feasibility/raw")
METADATA = {v: RAW / f"{v}_markets" / f"{v}_markets.jsonl"
            for v in ("kalshi", "polymarket")}
FORBIDDEN = {"label", "labels", "y", "resolved_outcome", "winning_outcome", "winner",
             "settlement_price", "forward_return", "b0", "b1", "b2", "b3"}


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Missing timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Naive timestamp cannot establish availability")
    return result.astimezone(timezone.utc)


def rows(path):
    with path.open() as handle:
        for number, line in enumerate(handle, 1):
            row = json.loads(line)
            if not isinstance(row, dict) or FORBIDDEN.intersection(row):
                raise ValueError(f"Non-object or forbidden outcome field in {path}:{number}")
            yield number, row


def family_candidate(venue, row):
    # A venue event key is evidence for a within-venue group, not a verified
    # independent semantic family across series, adjacent events, or venues.
    event = row.get("event_ticker") if venue == "kalshi" else row.get("event_id")
    return {"candidate_family_id": f"{venue}:event:{event}" if event else None,
            "source_event_id": str(event) if event else None,
            "family_verified": False,
            "review_status": "needs_semantic_and_cross_event_review" if event else "missing_event_mapping"}


def inspect_news(row):
    published = timestamp(row.get("published_at"))
    ingest = timestamp(row.get("ingest_ts"))
    started = timestamp(row.get("run_started_at"))
    ended = timestamp(row["run_ended_at"]) if row.get("run_ended_at") else ingest
    available = timestamp(row.get("available_at"))
    clock_ok = (available == max(published, ingest, started, ended)
                and published <= ingest and started <= ingest and started <= ended)
    return available, clock_ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/v5/source_readiness_20260908")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("Use a new release directory; existing evidence cannot be overwritten")
    start, end = timestamp(START), timestamp(END)
    prepared = json.loads((ROOT / PREPARED_MANIFEST).read_text())
    # Verify only explicitly allowed input artifacts, never the prices in this manifest.
    locked = {r["path"]: r["sha256"] for r in prepared["artifacts"]}
    inputs = [INDEX, *METADATA.values(), PREPARED_MANIFEST, NEWS, NEWS_RECEIPT]
    for path in [INDEX, *METADATA.values()]:
        if digest(ROOT / path) != locked[str(path)]:
            raise RuntimeError(f"Frozen input mismatch: {path}")
    index = {}
    for _, row in rows(ROOT / INDEX):
        key = (row["venue"], row["market_id"])
        if key in index:
            raise ValueError("Duplicate market index")
        # Deliberately do not retain activity counts, trade spans or any outcome data.
        index[key] = {k: row[k] for k in ["venue", "market_id", "question", "category"]}
    metadata, manifests = {}, {}
    for venue, path in METADATA.items():
        manifest_path = path.parent / "manifest.json"
        inputs.append(manifest_path)
        manifests[venue] = json.loads((ROOT / manifest_path).read_text())
        for line, row in rows(ROOT / path):
            key = (venue, str(row["ticker" if venue == "kalshi" else "condition_id"]))
            if key not in index:
                continue
            metadata.setdefault(key, []).append((line, row))
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".source-readiness-", dir=output.parent))
    summary, groups = Counter(), Counter()
    with (stage / "metadata_staging.jsonl").open("w") as normalized, \
            (stage / "family_review_queue.jsonl").open("w") as review:
        for key, market in sorted(index.items()):
            venue, market_id = key
            summary[f"{venue}_markets"] += 1
            versions = metadata.get(key, [])
            summary["markets_with_multiple_cached_versions"] += int(len(versions) > 1)
            if not versions:
                summary["markets_missing_metadata"] += 1
                continue
            family_values = set()
            for line, row in versions:
                ingest = timestamp(row["ingest_ts"])
                timing = "before_start" if ingest < start else "within_window" if ingest < end else "after_window"
                summary[f"metadata_ingest_{timing}"] += 1
                candidate = family_candidate(venue, row)
                family_values.add(candidate["candidate_family_id"])
                terminal = {field: row.get(field) for field in
                            (["close_time", "expiration_time"] if venue == "kalshi" else ["end_date"])}
                staged = {"venue": venue, "market_id": market_id,
                          "question": row.get("title" if venue == "kalshi" else "question"),
                          "category": market["category"], "category_status": "legacy_taxonomy_needs_asof_rebuild",
                          "source_ingest_ts": row["ingest_ts"],
                          "local_content_observed_at": manifests[venue]["completed_at"],
                          "historical_content_available_at": None,
                          "valid_from": None, "valid_until": None, "is_open": None,
                          "terminal_fields": terminal, "candidate_family": candidate,
                          "source": row.get("source"), "source_endpoint": row.get("source_endpoint"),
                          "source_run_id": row.get("source_run_id"),
                          "source_file": str(METADATA[venue]), "source_line": line,
                          "training_admissible": False,
                          "missing_proofs": ["historical_content_version", "trading_status_history",
                                             "metadata_validity", "verified_semantic_family"]}
                normalized.write(json.dumps(staged, sort_keys=True) + "\n")
                summary["metadata_rows_staged"] += 1
            distinct = family_values - {None}
            candidate_id = next(iter(distinct)) if len(distinct) == 1 and None not in family_values else None
            if candidate_id:
                groups[candidate_id] += 1
                summary[f"{venue}_markets_with_event_key"] += 1
            else:
                summary[f"{venue}_markets_without_unambiguous_event_key"] += 1
            review.write(json.dumps({**market, "candidate_family_id": candidate_id,
                                     "family_verified": False, "reviewer": None,
                                     "evidence": None, "approved_family_id": None,
                                     "review_requirements": ["contract_semantics", "adjacent_event_dependencies",
                                                             "cross_venue_duplicates"]}, sort_keys=True) + "\n")

    receipt = json.loads((ROOT / NEWS_RECEIPT).read_text())
    observed = max(r["completed_at"] for r in receipt["retry_ledger"] if r["status"] == "success")
    news_stats, days, statuses = Counter(), Counter(), Counter()
    unique_ids = set()
    with (stage / "news_provenance_staging.jsonl").open("w") as handle:
        for line, row in rows(ROOT / NEWS):
            news_stats["export_rows_scanned"] += 1
            available, clock_ok = inspect_news(row)
            if not start <= available < end:
                continue
            news_stats["discovery_rows"] += 1
            news_stats["clock_consistent_rows"] += int(clock_ok)
            news_stats["clock_inconsistent_rows"] += int(not clock_ok)
            news_stats["rows_with_run_id"] += int(bool(row.get("source_run_id")))
            news_stats["rows_with_text"] += int(bool(row.get("headline") or row.get("summary")))
            statuses[str(row.get("run_status"))] += 1
            days[available.date().isoformat()] += 1
            identity = str(row["id"])
            news_stats["duplicate_id_rows"] += int(identity in unique_ids)
            unique_ids.add(identity)
            text_hash = hashlib.sha256(json.dumps(
                {k: row.get(k) for k in ["headline", "summary"]}, sort_keys=True).encode()).hexdigest()
            handle.write(json.dumps({"article_id": identity, "source_file": str(NEWS), "source_line": line,
                                     "source_run_id": row.get("source_run_id"),
                                     "source_clock_available_at": row["available_at"],
                                     "local_content_observed_at": observed, "content_sha256": text_hash,
                                     "historical_content_available_at": None,
                                     "clock_consistent": clock_ok, "training_admissible": False}, sort_keys=True) + "\n")
    if news_stats["export_rows_scanned"] != receipt["receipt"]["rowcount"]:
        raise RuntimeError("News export count disagrees with receipt; staged release not published")
    news_stats["unique_discovery_ids"] = len(unique_ids)
    report = {"status": "blocked_on_provenance_and_family_verification",
              "scope": "local source-only audit of opened discovery, not a new cohort or experiment",
              "window": {"start": START, "end_exclusive": END},
              "created_at": datetime.now(timezone.utc).isoformat(),
              "market_metadata": dict(summary),
              "family_candidates": {"distinct_source_event_groups": len(groups),
                                    "multi_market_groups": sum(n > 1 for n in groups.values()),
                                    "largest_group_markets": max(groups.values(), default=0),
                                    "verified_semantic_families": 0},
              "news": {**dict(news_stats), "availability_days": dict(sorted(days.items())),
                       "run_status_counts": dict(statuses),
                       "historical_exact_content_version_proven_rows": 0,
                       "coverage_complete": False},
              "eligible_examples_built": 0, "models_fitted": 0,
              "outcome_files_read": [], "protected_holdouts_touched": False,
              "gates": {"source_event_mapping_complete": False,
                        "semantic_families_verified": False,
                        "metadata_status_and_validity_history": False,
                        "historical_exact_content_version_proof": False,
                        "source_completeness_reconciled": False},
              "interpretation": "Export hashes prove downloaded bytes, not that those exact bytes existed at original ingest_ts. Missing proof is not proof of revisions or absence at the source."}
    (stage / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    manifest = {"artifact_type": "non_admissible_source_staging_not_research_freeze",
                "inputs": [{"path": str(p), "sha256": digest(ROOT / p)} for p in inputs],
                "implementation": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": digest(Path(__file__))},
                "outputs": [{"path": p.name, "sha256": digest(p)} for p in sorted(stage.iterdir())]}
    (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    if output.exists():
        raise FileExistsError("Output appeared during staging; refusing overwrite")
    os.rename(stage, output)
    print(json.dumps({k: v for k, v in report.items() if k != "news"}, indent=2))
    print(json.dumps({"news": {k: v for k, v in report["news"].items() if k != "availability_days"}}, indent=2))


if __name__ == "__main__":
    main()
