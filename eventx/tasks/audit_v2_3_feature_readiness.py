"""Run label-blind EventX v2.3 news/trade feature-readiness diagnostics.

This task applies the frozen news association rule, audits point-in-time rolling-news
features, quantifies warehouse-backfill timing, and measures trade timestamp freshness.
It deliberately does not construct jump labels, read forward returns, train a model,
run the official power analysis, or access the October holdout.
"""

from __future__ import annotations

import argparse
import bisect
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable

from eventx.features.v2_1_association import MarketSpec, associate
from eventx.settings import REPO_ROOT


DEFAULT_COHORT = REPO_ROOT / "data/v2_1/cohort/selected_markets.jsonl"
DEFAULT_SPECS = REPO_ROOT / "data/v2_1/association/v1_audit/market_specs.jsonl"
DEFAULT_WAREHOUSE_ROOT = (
    REPO_ROOT
    / "data/v2_3_1/reconciliation/news_warehouse"
    / "20260808T000000Z_20260828T000000Z"
)
DEFAULT_WAREHOUSE = DEFAULT_WAREHOUSE_ROOT / "news_articles.jsonl"
DEFAULT_AVAILABILITY = DEFAULT_WAREHOUSE_ROOT / "reconciled/availability_index.jsonl"
DEFAULT_RECONCILIATION = (
    DEFAULT_WAREHOUSE_ROOT / "reconciled/reconciliation_manifest.json"
)
DEFAULT_TRADE_ROOT = (
    REPO_ROOT / "data/v2_3_1/reconciliation/frozen_cohort_20260808_20260828"
)
DEFAULT_KALSHI_TRADES = DEFAULT_TRADE_ROOT / "trades_kalshi.jsonl"
DEFAULT_POLYMARKET_TRADES = DEFAULT_TRADE_ROOT / "trades_polymarket.jsonl"
DEFAULT_OUTPUT = REPO_ROOT / "data/v2_3_1/feature_readiness_20260829"
WINDOWS_MIN = (60, 360, 1440)
FRESHNESS_MIN = (30, 60, 240)
GRID_MINUTES = 5
RULE_VERSION = "eventx-v2.1-association-rule-v1-candidate"


def parse_utc(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def content_hash(text: str) -> str:
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()


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


def percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def distribution(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "p50": percentile(values, 0.50),
        "p90": percentile(values, 0.90),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "max": max(values) if values else None,
        "mean": sum(values) / len(values) if values else None,
    }


def grid(start: datetime, end: datetime) -> list[datetime]:
    rows: list[datetime] = []
    current = start
    while current < end:
        rows.append(current)
        current += timedelta(minutes=GRID_MINUTES)
    return rows


def ceil_to_grid(value: datetime) -> datetime:
    seconds = GRID_MINUTES * 60
    timestamp = value.timestamp()
    ceiled = math.ceil(timestamp / seconds) * seconds
    return datetime.fromtimestamp(ceiled, tz=timezone.utc)


def rolling_count(times: list[datetime], at: datetime, minutes: int) -> int:
    right = bisect.bisect_right(times, at)
    left = bisect.bisect_right(times, at - timedelta(minutes=minutes), hi=right)
    return right - left


def load_specs(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in iter_jsonl(path):
        if row.get("rule_version") != RULE_VERSION:
            raise ValueError("market spec uses an unexpected association rule")
        value = row["spec"]
        spec = MarketSpec(
            category=str(value["category"]),
            question=str(value["question"]),
            phrases=tuple(value.get("phrases") or []),
            anchors=tuple(value.get("anchors") or []),
            event_terms=tuple(value.get("event_terms") or []),
            keywords=tuple(value.get("keywords") or []),
            cashtags=tuple(value.get("cashtags") or []),
        )
        result[str(row["market_id"])] = {
            "venue": str(row["venue"]),
            "market_id": str(row["market_id"]),
            "outcome_id": str(row["outcome_id"]),
            "spec": spec,
        }
    return result


def load_availability(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in iter_jsonl(path):
        key = str(row.get("warehouse_id"))
        if key in result:
            raise ValueError(f"duplicate warehouse ID in availability index: {key}")
        result[key] = row
    return result


def lag_audit(
    warehouse_path: Path,
    availability: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    eventx_lags: list[float] = []
    available_lags: list[float] = []
    ingest_lags: list[float] = []
    eventx_by_mode: defaultdict[str, list[float]] = defaultdict(list)
    available_by_source: defaultdict[str, list[float]] = defaultdict(list)
    negative_eventx_lag = 0
    rows = 0
    per_row: list[dict[str, Any]] = []
    for article in iter_jsonl(warehouse_path):
        rows += 1
        indexed = availability.get(str(article.get("id")))
        if indexed is None:
            raise ValueError(f"warehouse ID {article.get('id')} missing availability row")
        published = parse_utc(article.get("published_at"))
        first_seen = parse_utc(indexed.get("eventx_first_seen_at"))
        available = parse_utc(indexed.get("available_at"))
        ingest = parse_utc(article.get("ingest_ts"))
        assert published is not None and first_seen is not None and available is not None
        eventx_lag = (first_seen - published).total_seconds() / 60
        available_lag = (available - published).total_seconds() / 60
        if eventx_lag < 0:
            negative_eventx_lag += 1
        eventx_lags.append(eventx_lag)
        available_lags.append(available_lag)
        mode = (
            "warehouse_export_completion"
            if indexed.get("eventx_first_seen_source") == "warehouse_export_completion"
            else "endpoint_observed"
        )
        eventx_by_mode[mode].append(eventx_lag)
        source = str(article.get("source") or "<missing>")
        available_by_source[source].append(available_lag)
        ingest_lag = None
        if ingest is not None:
            ingest_lag = (ingest - published).total_seconds() / 60
            ingest_lags.append(ingest_lag)
        per_row.append(
            {
                "available_lag_minutes": available_lag,
                "eventx_first_seen_lag_minutes": eventx_lag,
                "first_seen_mode": mode,
                "lumid_ingest_lag_minutes": ingest_lag,
                "warehouse_id": article.get("id"),
            }
        )
    return (
        {
            "rows": rows,
            "negative_eventx_first_seen_lag_rows": negative_eventx_lag,
            "eventx_first_seen_lag_minutes": distribution(eventx_lags),
            "available_lag_minutes": distribution(available_lags),
            "lumid_ingest_lag_minutes": distribution(ingest_lags),
            "eventx_first_seen_lag_by_mode": {
                key: distribution(values) for key, values in sorted(eventx_by_mode.items())
            },
            "available_lag_by_warehouse_source": {
                key: distribution(values)
                for key, values in sorted(available_by_source.items())
            },
        },
        per_row,
    )


def build_associations(
    warehouse_path: Path,
    availability: dict[str, dict[str, Any]],
    specs: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any], list[dict[str, Any]]]:
    selected: dict[str, dict[str, dict[str, Any]]] = {
        market_id: {} for market_id in specs
    }
    reasons: Counter[str] = Counter()
    potential_quarantined: Counter[str] = Counter()
    duplicate_market_content = 0
    articles_scanned = 0
    empty_text = 0
    for article in iter_jsonl(warehouse_path):
        articles_scanned += 1
        indexed = availability[str(article["id"])]
        text = " ".join(
            str(article.get(field) or "").strip()
            for field in ("headline", "summary")
            if str(article.get(field) or "").strip()
        )
        if not text:
            empty_text += 1
            continue
        digest = content_hash(text)
        for market_id, market in specs.items():
            match_reasons, terms = associate(market["spec"], text)
            if not match_reasons:
                continue
            if indexed.get("quarantined_timestamp_conflict") is True:
                potential_quarantined[market_id] += 1
                continue
            event = {
                "association_rule": RULE_VERSION,
                "available_at": indexed["available_at"],
                "content_hash": digest,
                "eventx_first_seen_at": indexed["eventx_first_seen_at"],
                "first_seen_mode": (
                    "warehouse_export_completion"
                    if indexed.get("eventx_first_seen_source")
                    == "warehouse_export_completion"
                    else "endpoint_observed"
                ),
                "market_id": market_id,
                "match_reasons": match_reasons,
                "match_terms": terms,
                "outcome_id": market["outcome_id"],
                "published_at": article["published_at"],
                "venue": market["venue"],
                "warehouse_id": article["id"],
                "warehouse_source": article.get("source"),
            }
            prior = selected[market_id].get(digest)
            if prior is not None:
                duplicate_market_content += 1
                prior_time = parse_utc(prior["available_at"])
                event_time = parse_utc(event["available_at"])
                assert prior_time is not None and event_time is not None
                if event_time >= prior_time:
                    continue
            selected[market_id][digest] = event

    grouped: dict[str, list[dict[str, Any]]] = {}
    all_rows: list[dict[str, Any]] = []
    market_summary: dict[str, Any] = {}
    for market_id, values in selected.items():
        events = sorted(
            values.values(),
            key=lambda row: (row["available_at"], row["content_hash"]),
        )
        grouped[market_id] = events
        all_rows.extend(events)
        mode_counts = Counter(str(row["first_seen_mode"]) for row in events)
        source_counts = Counter(str(row.get("warehouse_source")) for row in events)
        for row in events:
            reasons.update(row["match_reasons"])
        market_summary[market_id] = {
            "associations": len(events),
            "associations_by_first_seen_mode": dict(sorted(mode_counts.items())),
            "associations_by_warehouse_source": dict(sorted(source_counts.items())),
            "quarantined_potential_matches": potential_quarantined[market_id],
        }
    return (
        grouped,
        {
            "articles_scanned": articles_scanned,
            "empty_text_articles": empty_text,
            "associations": len(all_rows),
            "duplicate_market_content_removed": duplicate_market_content,
            "markets_with_associations": sum(
                bool(values) for values in grouped.values()
            ),
            "markets_without_associations": sorted(
                key for key, values in grouped.items() if not values
            ),
            "match_reasons": dict(sorted(reasons.items())),
            "by_market": market_summary,
            "news_symbol_mapped": {
                "constant_value": 0,
                "mapped_markets": 0,
                "note": "Frozen event-market specs contain no canonical financial-symbol mapping.",
            },
        },
        sorted(all_rows, key=lambda row: (row["market_id"], row["available_at"])),
    )


def feature_audit(
    grouped: dict[str, list[dict[str, Any]]],
    *,
    start: datetime,
    end: datetime,
    export_completed: datetime,
) -> dict[str, Any]:
    primary_grid = grid(start, end)
    shock_time = ceil_to_grid(export_completed)
    shock_grid_end = shock_time + timedelta(minutes=max(WINDOWS_MIN) + GRID_MINUTES)
    market_results: dict[str, Any] = {}
    all_primary_counts: dict[int, list[float]] = {value: [] for value in WINDOWS_MIN}
    invariance_failures = 0
    export_associations = 0
    observed_associations = 0

    for market_id, events in grouped.items():
        times = [parse_utc(row["available_at"]) for row in events]
        if any(value is None for value in times):
            raise ValueError(f"market {market_id} contains invalid available_at")
        event_times = [value for value in times if value is not None]
        observed_times = [
            parse_utc(row["available_at"])
            for row in events
            if row["first_seen_mode"] == "endpoint_observed"
        ]
        observed = [value for value in observed_times if value is not None]
        export_associations += sum(
            row["first_seen_mode"] == "warehouse_export_completion" for row in events
        )
        observed_associations += sum(
            row["first_seen_mode"] == "endpoint_observed" for row in events
        )
        primary: dict[str, Any] = {}
        shock: dict[str, Any] = {}
        for minutes in WINDOWS_MIN:
            values = [rolling_count(event_times, at, minutes) for at in primary_grid]
            all_primary_counts[minutes].extend(float(value) for value in values)
            primary[f"{minutes}m"] = {
                **distribution([float(value) for value in values]),
                "nonzero_grid_rows": sum(value > 0 for value in values),
                "nonzero_grid_share": (
                    sum(value > 0 for value in values) / len(values) if values else 0
                ),
            }
            total_at_shock = rolling_count(event_times, shock_time, minutes)
            observed_at_shock = rolling_count(observed, shock_time, minutes)
            shock[f"{minutes}m"] = {
                "all_associations": total_at_shock,
                "endpoint_observed_only": observed_at_shock,
                "warehouse_backfill_component": total_at_shock - observed_at_shock,
                "backfill_share": (
                    (total_at_shock - observed_at_shock) / total_at_shock
                    if total_at_shock
                    else 0
                ),
                "count_after_window_minutes": rolling_count(
                    event_times, shock_time + timedelta(minutes=minutes), minutes
                ),
            }

        checkpoints = primary_grid[::144] + [shock_time]
        for checkpoint in checkpoints:
            visible = [value for value in event_times if value <= checkpoint]
            for minutes in WINDOWS_MIN:
                if rolling_count(event_times, checkpoint, minutes) != rolling_count(
                    visible, checkpoint, minutes
                ):
                    invariance_failures += 1
        future_time = shock_grid_end + timedelta(days=1)
        for minutes in WINDOWS_MIN:
            if rolling_count(event_times, shock_time, minutes) != rolling_count(
                sorted([*event_times, future_time]), shock_time, minutes
            ):
                invariance_failures += 1
        market_results[market_id] = {
            "associations": len(events),
            "primary_window": primary,
            "shock_at_export_completion": shock,
        }

    aggregate_primary = {
        f"{minutes}m": distribution(values)
        for minutes, values in all_primary_counts.items()
    }
    aggregate_shock = {
        f"{minutes}m": {
            "all_associations": sum(
                value["shock_at_export_completion"][f"{minutes}m"]["all_associations"]
                for value in market_results.values()
            ),
            "endpoint_observed_only": sum(
                value["shock_at_export_completion"][f"{minutes}m"][
                    "endpoint_observed_only"
                ]
                for value in market_results.values()
            ),
            "warehouse_backfill_component": sum(
                value["shock_at_export_completion"][f"{minutes}m"][
                    "warehouse_backfill_component"
                ]
                for value in market_results.values()
            ),
        }
        for minutes in WINDOWS_MIN
    }
    return {
        "window_semantics": "(feature_ts - window, feature_ts] using available_at",
        "primary_grid": {
            "start": rfc3339(start),
            "end_exclusive": rfc3339(end),
            "cadence_minutes": GRID_MINUTES,
            "rows_per_market": len(primary_grid),
        },
        "backfill_shock_time": rfc3339(shock_time),
        "diagnostic_shock_grid_end": rfc3339(shock_grid_end),
        "endpoint_observed_associations": observed_associations,
        "warehouse_export_associations": export_associations,
        "backfill_shock_detected": any(
            row["warehouse_backfill_component"] > 0
            for row in aggregate_shock.values()
        ),
        "aggregate_primary_counts": aggregate_primary,
        "aggregate_shock_counts": aggregate_shock,
        "point_in_time_invariance": {
            "failures": invariance_failures,
            "passed": invariance_failures == 0,
            "checks": "prefix recomputation plus appended-future-event invariance",
        },
        "by_market": market_results,
    }


def trade_audit(
    paths: list[Path],
    cohort: dict[str, dict[str, Any]],
    *,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    times_by_market: defaultdict[str, list[datetime]] = defaultdict(list)
    invalid_rows = 0
    outside_window = 0
    for path in paths:
        for envelope in iter_jsonl(path):
            record = envelope.get("record")
            if not isinstance(record, dict):
                invalid_rows += 1
                continue
            market_id = str(record.get("market_id") or record.get("ticker") or "")
            timestamp = parse_utc(record.get("created_time") or record.get("ts"))
            if market_id not in cohort or timestamp is None:
                invalid_rows += 1
                continue
            if not start <= timestamp < end:
                outside_window += 1
                continue
            times_by_market[market_id].append(timestamp)

    grid_times = grid(start, end)
    by_market: dict[str, Any] = {}
    aggregate_ages: list[float] = []
    aggregate_gaps: list[float] = []
    no_prior_total = 0
    for market_id in sorted(cohort):
        times = sorted(times_by_market.get(market_id, []))
        gaps = [
            (right - left).total_seconds() / 60
            for left, right in zip(times, times[1:])
        ]
        ages: list[float] = []
        no_prior = 0
        for at in grid_times:
            index = bisect.bisect_right(times, at) - 1
            if index < 0:
                no_prior += 1
                continue
            ages.append((at - times[index]).total_seconds() / 60)
        aggregate_ages.extend(ages)
        aggregate_gaps.extend(gaps)
        no_prior_total += no_prior
        freshness = {
            f"le_{threshold}m": {
                "rows": sum(value <= threshold for value in ages),
                "share_of_all_grid_rows": (
                    sum(value <= threshold for value in ages) / len(grid_times)
                    if grid_times
                    else 0
                ),
                "share_where_price_exists": (
                    sum(value <= threshold for value in ages) / len(ages) if ages else 0
                ),
            }
            for threshold in FRESHNESS_MIN
        }
        by_market[market_id] = {
            "venue": cohort[market_id]["venue"],
            "trade_rows": len(times),
            "first_trade_at": rfc3339(times[0]) if times else None,
            "last_trade_at": rfc3339(times[-1]) if times else None,
            "grid_rows": len(grid_times),
            "grid_rows_without_prior_trade": no_prior,
            "price_age_minutes": distribution(ages),
            "intertrade_gap_minutes": distribution(gaps),
            "freshness": freshness,
        }
    total_grid_rows = len(grid_times) * len(cohort)
    return {
        "trade_rows": sum(len(values) for values in times_by_market.values()),
        "markets": len(cohort),
        "markets_with_trades": sum(bool(times_by_market.get(key)) for key in cohort),
        "markets_without_trades": sorted(
            key for key in cohort if not times_by_market.get(key)
        ),
        "invalid_rows": invalid_rows,
        "outside_window_rows": outside_window,
        "grid_rows": total_grid_rows,
        "grid_rows_without_prior_trade": no_prior_total,
        "aggregate_price_age_minutes": distribution(aggregate_ages),
        "aggregate_intertrade_gap_minutes": distribution(aggregate_gaps),
        "aggregate_freshness": {
            f"le_{threshold}m": {
                "rows": sum(value <= threshold for value in aggregate_ages),
                "share_of_all_grid_rows": (
                    sum(value <= threshold for value in aggregate_ages) / total_grid_rows
                    if total_grid_rows
                    else 0
                ),
                "share_where_price_exists": (
                    sum(value <= threshold for value in aggregate_ages)
                    / len(aggregate_ages)
                    if aggregate_ages
                    else 0
                ),
            }
            for threshold in FRESHNESS_MIN
        },
        "by_market": by_market,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    parser.add_argument("--market-specs", type=Path, default=DEFAULT_SPECS)
    parser.add_argument("--warehouse", type=Path, default=DEFAULT_WAREHOUSE)
    parser.add_argument("--availability", type=Path, default=DEFAULT_AVAILABILITY)
    parser.add_argument(
        "--availability-manifest",
        type=Path,
        help="optional verified multi-snapshot availability merge manifest",
    )
    parser.add_argument("--reconciliation", type=Path, default=DEFAULT_RECONCILIATION)
    parser.add_argument("--kalshi-trades", type=Path, default=DEFAULT_KALSHI_TRADES)
    parser.add_argument(
        "--polymarket-trades", type=Path, default=DEFAULT_POLYMARKET_TRADES
    )
    parser.add_argument("--start", default="2026-08-08T00:00:00Z")
    parser.add_argument("--end", default="2026-08-28T00:00:00Z")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start = parse_utc(args.start)
    end = parse_utc(args.end)
    assert start is not None and end is not None and start < end
    reconciliation = json.loads(args.reconciliation.read_text(encoding="utf-8"))
    if reconciliation.get("integrity_pass") is not True:
        raise SystemExit("warehouse reconciliation integrity has not passed")
    if args.availability_manifest is not None:
        availability_manifest = json.loads(
            args.availability_manifest.read_text(encoding="utf-8")
        )
        artifact = availability_manifest.get("artifacts", {}).get(
            "availability_index", {}
        )
        artifact_path = REPO_ROOT / str(artifact.get("path", ""))
        if availability_manifest.get("integrity_pass") is not True:
            raise SystemExit("availability merge integrity has not passed")
        if availability_manifest.get("labels_or_outcomes_read") is not False:
            raise SystemExit("availability merge is not label-blind")
        if artifact_path.resolve() != args.availability.resolve():
            raise SystemExit("availability index does not match merge manifest")
        if artifact_path.stat().st_size != artifact.get("bytes"):
            raise SystemExit("availability index byte count does not match manifest")
        if file_sha256(artifact_path) != artifact.get("sha256"):
            raise SystemExit("availability index hash does not match merge manifest")
    export_completed = parse_utc(reconciliation.get("warehouse_export_completed_at"))
    if export_completed is None:
        raise SystemExit("reconciliation has no warehouse export completion time")

    cohort_rows = list(iter_jsonl(args.cohort))
    cohort = {str(row["market_id"]): row for row in cohort_rows}
    specs = load_specs(args.market_specs)
    if set(cohort) != set(specs) or len(cohort) != 14:
        raise SystemExit("cohort and frozen market specs do not contain the same 14 IDs")
    availability = load_availability(args.availability)
    lag_report, lag_rows = lag_audit(args.warehouse, availability)
    grouped, association_report, associations = build_associations(
        args.warehouse, availability, specs
    )
    features = feature_audit(
        grouped,
        start=start,
        end=end,
        export_completed=export_completed,
    )
    trades = trade_audit(
        [args.kalshi_trades, args.polymarket_trades],
        cohort,
        start=start,
        end=end,
    )

    args.output.mkdir(parents=True, exist_ok=True)
    associations_path = args.output / "matched_news_associations.jsonl"
    lag_path = args.output / "news_lag_rows.jsonl"
    market_path = args.output / "market_readiness.jsonl"
    report_path = args.output / "audit_report.json"
    atomic_jsonl(associations_path, associations)
    atomic_jsonl(lag_path, lag_rows)
    atomic_jsonl(
        market_path,
        (
            {
                "association": association_report["by_market"][market_id],
                "feature": features["by_market"][market_id],
                "market_id": market_id,
                "trade": trades["by_market"][market_id],
                "venue": cohort[market_id]["venue"],
            }
            for market_id in sorted(cohort)
        ),
    )
    inputs = [
        args.cohort,
        args.market_specs,
        args.warehouse,
        args.availability,
        args.reconciliation,
        args.kalshi_trades,
        args.polymarket_trades,
    ]
    if args.availability_manifest is not None:
        inputs.append(args.availability_manifest)
    output_artifacts = [associations_path, lag_path, market_path]
    report = {
        "status": "completed_label_blind_diagnostics",
        "protocol_id": "eventx-v2.3-news-availability-clarifications-20260817",
        "association_rule": RULE_VERSION,
        "created_at": rfc3339(datetime.now(timezone.utc)),
        "window": {
            "start_inclusive": rfc3339(start),
            "end_exclusive": rfc3339(end),
        },
        "integrity": {
            "label_blind": True,
            "labels_read": [],
            "outcomes_read": [],
            "prices_read": [],
            "model_training_run": False,
            "official_power_analysis_run": False,
            "holdout_accessed": False,
        },
        "association_density": association_report,
        "news_source_lag": lag_report,
        "news_feature_readiness": features,
        "trade_staleness": trades,
        "findings": {
            "point_in_time_invariance_passed": features[
                "point_in_time_invariance"
            ]["passed"],
            "backfill_shock_detected": features["backfill_shock_detected"],
            "markets_without_news_associations": association_report[
                "markets_without_associations"
            ],
            "news_symbol_mapped_is_constant_zero": True,
            "trade_all_markets_supported": not trades["markets_without_trades"],
        },
        "input_hashes": {
            relative(path): file_sha256(path) for path in inputs
        },
        "output_artifacts": {
            relative(path): {
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
            for path in output_artifacts
        },
        "code": {
            "path": relative(Path(__file__)),
            "sha256": file_sha256(Path(__file__)),
        },
        "interpretation_limit": (
            "These diagnostics measure data and feature readiness only. They do not "
            "estimate predictive lift, label prevalence, model performance, or power."
        ),
    }
    atomic_json(report_path, report)
    print(
        json.dumps(
            {
                "output": relative(report_path),
                "status": report["status"],
                "findings": report["findings"],
                "association_summary": {
                    key: association_report[key]
                    for key in (
                        "articles_scanned",
                        "associations",
                        "markets_with_associations",
                        "markets_without_associations",
                    )
                },
                "backfill_shock": features["aggregate_shock_counts"],
                "trade_summary": {
                    "trade_rows": trades["trade_rows"],
                    "markets_with_trades": trades["markets_with_trades"],
                    "aggregate_freshness": trades["aggregate_freshness"],
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
