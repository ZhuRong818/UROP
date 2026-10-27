"""Audit label-blind historical market/news overlap for EventX v3 feasibility."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterator

from eventx.features.v2_1_association import associate, market_spec, normalized_tokens
from eventx.settings import REPO_ROOT
from eventx.tasks.build_v2_1_taxonomy import TAXONOMY_VERSION, classify
from eventx.tasks.collect_v2_3_news_v2 import normalize_url


DEFAULT_PROTOCOL = REPO_ROOT / "eventx/release/v3_historical/feasibility_protocol.json"
DEFAULT_RAW = REPO_ROOT / "data/v3_historical/feasibility/raw"
DEFAULT_OUTPUT = REPO_ROOT / "data/v3_historical/feasibility/audit"
PROHIBITED_FIELDS = {
    "forward_logodds",
    "forward_return",
    "label",
    "metric",
    "prediction",
    "target",
    "y",
    "y_jump",
}


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not an object")
            prohibited = PROHIBITED_FIELDS.intersection(key.lower() for key in value)
            if prohibited:
                raise ValueError(f"{path} contains prohibited fields: {sorted(prohibited)}")
            yield value


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def load_manifest(
    raw_root: Path,
    dataset: str,
    protocol_id: str,
    expected_window: dict[str, Any],
) -> tuple[dict[str, Any], Path]:
    manifest_path = raw_root / dataset / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("protocol_id") != protocol_id:
        raise ValueError(f"{dataset} protocol mismatch")
    if manifest.get("window") != expected_window:
        raise ValueError(f"{dataset} window mismatch")
    if manifest.get("integrity_pass") is not True:
        raise ValueError(f"{dataset} input integrity did not pass")
    if manifest.get("labels_or_outcomes_read") is not False:
        raise ValueError(f"{dataset} did not preserve outcome seal")
    data_path = Path(manifest["artifacts"]["data"]["path"])
    if not data_path.is_absolute():
        data_path = REPO_ROOT / data_path
    if sha256_file(data_path) != manifest["artifacts"]["data"]["sha256"]:
        raise ValueError(f"{dataset} data hash mismatch")
    return manifest, data_path


def parse_json_array(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return []


def build_markets(
    raw_root: Path,
    protocol_id: str,
    expected_window: dict[str, Any],
    min_days: int,
    min_trades: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Path]]:
    paths: dict[str, Path] = {}
    for dataset in (
        "kalshi_activity",
        "polymarket_activity",
        "kalshi_markets",
        "polymarket_markets",
    ):
        _, paths[dataset] = load_manifest(
            raw_root, dataset, protocol_id, expected_window
        )

    kalshi_market_rows = list(read_jsonl(paths["kalshi_markets"]))
    polymarket_market_rows = list(read_jsonl(paths["polymarket_markets"]))
    desired_kalshi = {
        str(row.get("ticker") or "") for row in kalshi_market_rows
    }
    desired_poly: set[tuple[str, str]] = set()
    for row in polymarket_market_rows:
        outcomes = parse_json_array(row.get("outcomes"))
        asset_ids = parse_json_array(row.get("clob_token_ids"))
        yes_indices = [
            index
            for index, outcome in enumerate(outcomes)
            if outcome.strip().lower() == "yes"
        ]
        if len(yes_indices) == 1 and yes_indices[0] < len(asset_ids):
            desired_poly.add(
                (str(row.get("condition_id") or ""), asset_ids[yes_indices[0]])
            )
    kalshi_activity: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(paths["kalshi_activity"]):
        ticker = str(row.get("ticker") or "")
        if ticker in desired_kalshi:
            kalshi_activity[ticker] = row
    poly_activity: dict[tuple[str, str], dict[str, Any]] = {}
    for row in read_jsonl(paths["polymarket_activity"]):
        key = (str(row.get("condition_id") or ""), str(row.get("asset_id") or ""))
        if key in desired_poly:
            poly_activity[key] = row
    markets: list[dict[str, Any]] = []
    drops: Counter[str] = Counter()
    for row in kalshi_market_rows:
        ticker = str(row.get("ticker") or "")
        activity = kalshi_activity.get(ticker)
        if activity is None:
            drops["kalshi_missing_activity"] += 1
            continue
        question = str(row.get("title") or "").strip()
        if not question:
            drops["kalshi_missing_question"] += 1
            continue
        if int(activity.get("active_days", 0)) < min_days:
            drops["below_min_active_days"] += 1
            continue
        if int(activity.get("trades", 0)) < min_trades:
            drops["below_min_trades"] += 1
            continue
        category, _ = classify(question)
        markets.append(
            {
                "active_days": int(activity["active_days"]),
                "canonical_yes_asset_id": "YES",
                "category": category,
                "first_trade_ts": activity.get("first_trade_ts"),
                "last_trade_ts": activity.get("last_trade_ts"),
                "market_id": ticker,
                "notional": float(activity.get("notional") or 0),
                "question": question,
                "taxonomy_version": TAXONOMY_VERSION,
                "trades": int(activity["trades"]),
                "venue": "kalshi",
            }
        )

    for row in polymarket_market_rows:
        condition_id = str(row.get("condition_id") or "")
        question = str(row.get("question") or "").strip()
        outcomes = parse_json_array(row.get("outcomes"))
        asset_ids = parse_json_array(row.get("clob_token_ids"))
        yes_indices = [
            index for index, outcome in enumerate(outcomes) if outcome.strip().lower() == "yes"
        ]
        if len(yes_indices) != 1 or yes_indices[0] >= len(asset_ids):
            drops["polymarket_no_unique_canonical_yes"] += 1
            continue
        yes_asset = asset_ids[yes_indices[0]]
        activity = poly_activity.get((condition_id, yes_asset))
        if activity is None:
            drops["polymarket_missing_yes_activity"] += 1
            continue
        if not question:
            drops["polymarket_missing_question"] += 1
            continue
        if int(activity.get("active_days", 0)) < min_days:
            drops["below_min_active_days"] += 1
            continue
        if int(activity.get("trades", 0)) < min_trades:
            drops["below_min_trades"] += 1
            continue
        category, _ = classify(question)
        markets.append(
            {
                "active_days": int(activity["active_days"]),
                "canonical_yes_asset_id": yes_asset,
                "category": category,
                "first_trade_ts": activity.get("first_trade_ts"),
                "last_trade_ts": activity.get("last_trade_ts"),
                "market_id": condition_id,
                "notional": float(activity.get("notional") or 0),
                "question": question,
                "taxonomy_version": TAXONOMY_VERSION,
                "trades": int(activity["trades"]),
                "venue": "polymarket",
            }
        )
    markets.sort(key=lambda row: (row["venue"], row["market_id"]))
    if len({(row["venue"], row["market_id"]) for row in markets}) != len(markets):
        raise ValueError("duplicate eligible market keys")
    return markets, {"drop_reasons": dict(sorted(drops.items()))}, paths


def load_timely_news(
    path: Path,
    start: datetime,
    end: datetime,
    max_lag_hours: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    identities: dict[str, dict[str, Any]] = {}
    late = 0
    missing = 0
    duplicate_identity_rows = 0
    for row in read_jsonl(path):
        published_text = row.get("published_at")
        ingest_text = row.get("ingest_ts")
        if not published_text or not ingest_text:
            missing += 1
            continue
        published = parse_utc(str(published_text))
        ingest = parse_utc(str(ingest_text))
        if ingest < published:
            raise ValueError("news ingest_ts precedes published_at")
        available = max(published, ingest)
        if not start <= available < end:
            raise ValueError("news row outside feasibility available_at window")
        if (ingest - published).total_seconds() > max_lag_hours * 3600:
            late += 1
            continue
        text = " ".join(
            str(row.get(field) or "").strip()
            for field in ("headline", "summary")
            if str(row.get(field) or "").strip()
        )
        if not text:
            continue
        url = str(row.get("url") or "").strip()
        try:
            normalized_url = normalize_url(url) if url else ""
        except ValueError:
            normalized_url = ""
        identity = f"url:{normalized_url}" if normalized_url else f"id:{row['id']}"
        candidate = {
            "available_at": available,
            "doc_id": str(row["id"]),
            "published_at": published,
            "text": text,
            "tokens": normalized_tokens(text),
        }
        current = identities.get(identity)
        if current is None:
            identities[identity] = {
                "document": candidate,
                "published_at_values": {rfc3339(published)},
                "rows": 1,
            }
            continue
        duplicate_identity_rows += 1
        current["rows"] = int(current["rows"]) + 1
        current["published_at_values"].add(rfc3339(published))
        existing = current["document"]
        if (candidate["available_at"], candidate["doc_id"]) < (
            existing["available_at"],
            existing["doc_id"],
        ):
            current["document"] = candidate

    documents: list[dict[str, Any]] = []
    timestamp_conflicts = 0
    for identity, value in identities.items():
        if identity.startswith("url:") and len(value["published_at_values"]) > 1:
            timestamp_conflicts += 1
            continue
        documents.append(value["document"])
    documents.sort(key=lambda row: (row["available_at"], row["doc_id"]))
    available_days = {row["available_at"].date().isoformat() for row in documents}
    return documents, {
        "timely_documents": len(documents),
        "duplicate_identity_rows": duplicate_identity_rows,
        "timestamp_conflict_identities_excluded": timestamp_conflicts,
        "late_backfill_documents": late,
        "missing_availability_documents": missing,
        "usable_calendar_days": len(available_days),
    }


def association_counts(
    markets: list[dict[str, Any]], documents: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    token_index: dict[str, set[int]] = defaultdict(set)
    for index, document in enumerate(documents):
        for token in document["tokens"]:
            token_index[token].add(index)
    results: list[dict[str, Any]] = []
    for market in markets:
        active_start = parse_utc(str(market["first_trade_ts"]))
        active_end = parse_utc(str(market["last_trade_ts"]))
        spec = market_spec(market["question"], market["category"])
        seed_terms = set(spec.anchors) | set(spec.event_terms) | set(spec.keywords)
        for phrase in spec.phrases:
            seed_terms.update(normalized_tokens(phrase))
        candidate_indices: set[int] = set()
        for term in seed_terms:
            candidate_indices.update(token_index.get(term, set()))
        matched_ids: list[str] = []
        for index in sorted(candidate_indices):
            if not active_start <= documents[index]["available_at"] <= active_end:
                continue
            reasons, _ = associate(spec, documents[index]["text"])
            if reasons:
                matched_ids.append(documents[index]["doc_id"])
        results.append(
            {
                "association_count": len(matched_ids),
                "category": market["category"],
                "market_id": market["market_id"],
                "venue": market["venue"],
            }
        )
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ingest-semantics-confirmed", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if protocol.get("labels_permitted") is not False or protocol.get("outcomes_permitted") is not False:
        raise SystemExit("protocol does not preserve outcome seal")
    protocol_id = str(protocol["protocol_id"])
    start = parse_utc(protocol["window"]["start_inclusive"])
    end = parse_utc(protocol["window"]["end_exclusive"])
    cohort_rules = protocol["cohort"]
    markets, market_stats, input_paths = build_markets(
        args.raw_root,
        protocol_id,
        protocol["window"],
        int(cohort_rules["min_active_trading_days_per_market"]),
        int(cohort_rules["min_canonical_yes_trades_per_market"]),
    )
    _, news_path = load_manifest(
        args.raw_root, "news", protocol_id, protocol["window"]
    )
    input_paths["news"] = news_path
    documents, news_stats = load_timely_news(
        news_path,
        start,
        end,
        float(protocol["availability"]["primary_max_ingest_lag_hours"]),
    )
    counts = association_counts(markets, documents)
    venue_counts = Counter(row["venue"] for row in markets)
    supported = sum(row["association_count"] >= 5 for row in counts)
    total_associations = sum(row["association_count"] for row in counts)
    max_associations = max((row["association_count"] for row in counts), default=0)
    concentration = max_associations / total_associations if total_associations else math.inf
    support_rules = protocol["news_support_gates"]
    gates = {
        "ingest_ts_semantics_confirmed": args.ingest_semantics_confirmed,
        "min_markets_total": len(markets) >= int(cohort_rules["min_markets_total"]),
        "min_markets_per_venue": all(
            venue_counts.get(venue, 0) >= int(cohort_rules["min_markets_per_venue"])
            for venue in ("kalshi", "polymarket")
        ),
        "min_markets_with_five_timely_associations": supported
        >= int(support_rules["min_markets_with_five_timely_associations"]),
        "min_timely_associations_total": total_associations
        >= int(support_rules["min_timely_associations_total"]),
        "max_single_market_association_share": total_associations > 0
        and concentration <= float(support_rules["max_single_market_association_share"]),
        "min_usable_calendar_days": news_stats["usable_calendar_days"]
        >= int(support_rules["min_usable_calendar_days"]),
    }
    all_data_gates = all(
        value for key, value in gates.items() if key != "ingest_ts_semantics_confirmed"
    )
    all_gates = all(gates.values())
    total_days = (end.date() - start.date()).days
    development_days = int(total_days * float(protocol["future_historical_protocol_if_passed"]["development_fraction_complete_utc_days"]))
    split = start + timedelta(days=development_days)
    args.output.mkdir(parents=True, exist_ok=True)
    eligible_path = args.output / "eligible_markets.jsonl"
    counts_path = args.output / "association_counts.jsonl"
    atomic_jsonl(eligible_path, markets)
    atomic_jsonl(counts_path, counts)
    report = {
        "protocol_id": protocol_id,
        "completed_at": rfc3339(datetime.now(timezone.utc)),
        "status": "passed" if all_gates else (
            "blocked_pending_ingest_ts_confirmation" if all_data_gates else "failed_data_gates"
        ),
        "labels_or_outcomes_read": False,
        "window": protocol["window"],
        "candidate_split_if_passed": {
            "development_start": rfc3339(start),
            "development_end_exclusive": rfc3339(split),
            "holdout_start": rfc3339(split),
            "holdout_end_exclusive": rfc3339(end),
        },
        "market_summary": {
            "eligible_markets": len(markets),
            "by_venue": dict(sorted(venue_counts.items())),
            **market_stats,
        },
        "news_summary": news_stats,
        "association_summary": {
            "markets_with_at_least_five": supported,
            "total": total_associations,
            "maximum_for_one_market": max_associations,
            "maximum_market_share": concentration if math.isfinite(concentration) else None,
        },
        "gates": gates,
        "historical_protocol_authorized": all_gates,
        "input_hashes": {str(path): sha256_file(path) for path in sorted(input_paths.values())},
        "outputs": {
            "eligible_markets": {"path": str(eligible_path), "sha256": sha256_file(eligible_path)},
            "association_counts": {"path": str(counts_path), "sha256": sha256_file(counts_path)},
        },
    }
    atomic_json(args.output / "report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
