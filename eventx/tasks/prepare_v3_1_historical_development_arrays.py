"""Prepare compact, label-blind arrays for the EventX v3.1 development run."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterator

import numpy as np

from eventx.features.v2_1_association import (
    associate,
    market_spec,
    normalized_tokens,
)
from eventx.settings import REPO_ROOT
from eventx.tasks.export_v3_historical_feasibility import parse_utc, rfc3339
from eventx.tasks.prepare_v3_historical_primary_inputs import load_development_news


PROTOCOL = REPO_ROOT / "eventx/release/v3_1_historical_primary/protocol.json"
DATA_GATE = REPO_ROOT / "data/v3_1_historical/primary/development/data_gate/manifest.json"
COHORT = REPO_ROOT / "data/v3_1_historical/primary/label_blind_inputs/cohort.jsonl"
RAW_TRADES = REPO_ROOT / "data/v3_historical/primary/development/trades"
NEWS_ROOT = REPO_ROOT / "data/v3_historical/primary/label_blind_inputs"
OUTPUT = REPO_ROOT / "data/v3_1_historical/primary/development/prepared"
LABELS = REPO_ROOT / "data/v3_1_historical/primary/development/labels.jsonl"
HOLDOUT = REPO_ROOT / "data/v3_1_historical/primary/holdout"
KALSHI_METADATA = (
    REPO_ROOT
    / "data/v3_historical/feasibility/raw/kalshi_markets/kalshi_markets.jsonl"
)
POLY_METADATA = (
    REPO_ROOT
    / "data/v3_historical/feasibility/raw/polymarket_markets/polymarket_markets.jsonl"
)
TRADE_DTYPE = np.dtype(
    [
        ("market", "<u4"),
        ("timestamp_us", "<i8"),
        ("price", "<f8"),
        ("notional", "<f8"),
        ("ordinal", "<u8"),
    ],
    align=False,
)
NEWS_DTYPE = np.dtype([("market", "<u4"), ("timestamp_us", "<i8")], align=False)


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
        for line in handle:
            if line.strip():
                yield json.loads(line)


def verify_manifest(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for artifact in manifest.get("artifacts", []):
        artifact_path = REPO_ROOT / str(artifact["path"])
        if not artifact_path.is_file() or sha256_file(artifact_path) != str(
            artifact["sha256"]
        ):
            raise RuntimeError(f"hash-lock failure: {artifact_path}")


def timestamp_us(value: str | datetime) -> int:
    parsed = value if isinstance(value, datetime) else parse_utc(value)
    return int(round(parsed.timestamp() * 1_000_000))


def load_market_index() -> tuple[list[dict[str, Any]], dict[tuple[str, str], int]]:
    rows = sorted(read_jsonl(COHORT), key=lambda row: (row["venue"], row["market_id"]))
    lookup = {
        (str(row["venue"]), str(row["market_id"])): index
        for index, row in enumerate(rows)
    }
    if len(lookup) != len(rows):
        raise RuntimeError("duplicate corrected cohort key")
    return rows, lookup


def terminal_metadata(
    markets: list[dict[str, Any]], lookup: dict[tuple[str, str], int]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    kalshi = {str(row["ticker"]): row for row in read_jsonl(KALSHI_METADATA)}
    poly = {str(row["condition_id"]): row for row in read_jsonl(POLY_METADATA)}
    output: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for index, market in enumerate(markets):
        venue = str(market["venue"])
        market_id = str(market["market_id"])
        if lookup[(venue, market_id)] != index:
            raise RuntimeError("market index is not deterministic")
        metadata = kalshi.get(market_id) if venue == "kalshi" else poly.get(market_id)
        if metadata is None:
            raise RuntimeError(f"missing frozen metadata: {venue}:{market_id}")
        candidates: list[datetime] = []
        fields = ("close_time", "expiration_time") if venue == "kalshi" else ("end_date",)
        for field in fields:
            if metadata.get(field):
                candidates.append(parse_utc(str(metadata[field])))
        terminal = min(candidates) if candidates else None
        first_trade = parse_utc(str(market["first_trade_ts"]))
        last_trade = parse_utc(str(market["last_trade_ts"]))
        counts["markets"] += 1
        counts["known_terminal"] += int(terminal is not None)
        counts["terminal_before_first_trade"] += int(
            terminal is not None and terminal < first_trade
        )
        counts["terminal_before_last_trade"] += int(
            terminal is not None and terminal < last_trade
        )
        output.append(
            {
                **market,
                "market_index": index,
                "market_group": int(
                    hashlib.sha256(f"{venue}:{market_id}".encode()).hexdigest(), 16
                )
                % 5,
                "terminal_time": rfc3339(terminal) if terminal else None,
                "metadata_ingest_ts": metadata.get("ingest_ts"),
            }
        )
    return output, dict(counts)


def normalize_trades(
    lookup: dict[tuple[str, str], int], maximum_rows: int
) -> tuple[Path, dict[str, int]]:
    path = OUTPUT / "trades.bin"
    array = np.memmap(path, mode="w+", dtype=TRADE_DTYPE, shape=(maximum_rows,))
    written = 0
    ordinal = 0
    counters: Counter[str] = Counter()
    for venue in ("kalshi", "polymarket"):
        manifest = json.loads((RAW_TRADES / venue / "manifest.json").read_text())
        for page_number, artifact in enumerate(manifest["artifacts"], start=1):
            page_path = REPO_ROOT / str(artifact["data_path"])
            previous_key: tuple[str, str] | None = None
            previous_signature: tuple[Any, ...] | None = None
            for row in read_jsonl(page_path):
                counters["raw_rows"] += 1
                ordinal += 1
                trade_id = str(row["trade_id"])
                if venue == "kalshi":
                    key = (venue, str(row["ticker"]))
                    timestamp_text = str(row["created_time"])
                    price = float(row["yes_price"]) / 100.0
                    notional = float(row["count"])
                    signature = (key, row["count"], row["yes_price"])
                else:
                    key = (venue, str(row["condition_id"]))
                    timestamp_text = str(row["ts"])
                    price = float(row["price"])
                    notional = float(row["size"])
                    signature = (key, str(row["asset_id"]), row["size"], row["price"])
                execution_key = (trade_id, rfc3339(parse_utc(timestamp_text)))
                if execution_key == previous_key:
                    if signature != previous_signature:
                        raise RuntimeError(f"conflicting adjacent duplicate in {page_path}")
                    counters["exact_duplicates_collapsed"] += 1
                    continue
                previous_key = execution_key
                previous_signature = signature
                market_index = lookup.get(key)
                if market_index is None:
                    counters["rows_outside_corrected_cohort"] += 1
                    continue
                if notional == 0.0:
                    counters["zero_notional_excluded"] += 1
                    continue
                if notional < 0.0 or not np.isfinite(notional):
                    raise RuntimeError(f"invalid notional in {page_path}")
                if not 0.0 <= price <= 1.0 or not np.isfinite(price):
                    raise RuntimeError(f"invalid price in {page_path}")
                if written >= maximum_rows:
                    raise RuntimeError("normalized trade allocation was too small")
                array[written] = (
                    market_index,
                    timestamp_us(timestamp_text),
                    price,
                    notional,
                    ordinal,
                )
                written += 1
            if page_number % 10 == 0:
                print(
                    f"normalized {venue} page {page_number}/{len(manifest['artifacts'])}; "
                    f"kept={written}",
                    flush=True,
                )
    array.flush()
    del array
    os.truncate(path, written * TRADE_DTYPE.itemsize)
    array = np.memmap(path, mode="r+", dtype=TRADE_DTYPE, shape=(written,))
    print(f"sorting {written} normalized executions", flush=True)
    array.sort(order=("market", "timestamp_us", "ordinal"), kind="quicksort")
    array.flush()
    del array
    counters["normalized_rows"] = written
    return path, dict(counters)


def build_news_associations(
    markets: list[dict[str, Any]], lookup: dict[tuple[str, str], int]
) -> tuple[Path, dict[str, int]]:
    documents, document_stats = load_development_news(NEWS_ROOT)
    token_index: dict[str, set[int]] = {}
    for document_index, document in enumerate(documents):
        for token in document["tokens"]:
            token_index.setdefault(token, set()).add(document_index)
    events: list[tuple[int, int]] = []
    markets_with_matches = 0
    maximum_matches = 0
    for position, market in enumerate(markets, start=1):
        spec = market_spec(str(market["question"]), str(market["category"]))
        seeds = set(spec.anchors) | set(spec.event_terms) | set(spec.keywords)
        for phrase in spec.phrases:
            seeds.update(normalized_tokens(phrase))
        candidate_indices: set[int] = set()
        for token in seeds:
            candidate_indices.update(token_index.get(token, set()))
        market_events = []
        for document_index in sorted(candidate_indices):
            document = documents[document_index]
            reasons, _terms = associate(spec, str(document["text"]))
            if reasons:
                market_events.append(
                    (
                        lookup[(str(market["venue"]), str(market["market_id"]))],
                        timestamp_us(document["available_at"]),
                    )
                )
        if market_events:
            markets_with_matches += 1
            maximum_matches = max(maximum_matches, len(market_events))
            events.extend(market_events)
        if position % 500 == 0:
            print(f"associated news for {position}/{len(markets)} markets", flush=True)
    values = np.array(events, dtype=NEWS_DTYPE)
    values.sort(order=("market", "timestamp_us"), kind="quicksort")
    path = OUTPUT / "news_associations.bin"
    values.tofile(path)
    return path, {
        **document_stats,
        "association_events": len(values),
        "markets_with_matches": markets_with_matches,
        "maximum_matches_for_one_market": maximum_matches,
        "news_symbol_mapped_constant_zero": 1,
    }


def main() -> None:
    if LABELS.exists() or HOLDOUT.exists():
        raise SystemExit("label-blind preparation refused after labels or holdout exist")
    verify_manifest(DATA_GATE)
    protocol = json.loads(PROTOCOL.read_text())
    if protocol.get("protocol_id") != "eventx-v3.1-historical-primary-20260902":
        raise SystemExit("wrong historical protocol")
    markets, lookup = load_market_index()
    indexed_markets, terminal_stats = terminal_metadata(markets, lookup)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    market_index_path = OUTPUT / "market_index.jsonl"
    atomic_jsonl(market_index_path, indexed_markets)
    full_gate = json.loads(
        (
            REPO_ROOT
            / "data/v3_historical/primary/development/data_gate/report.json"
        ).read_text()
    )
    maximum_rows = sum(
        int(full_gate["venue_reports"][venue]["unique_executions"])
        for venue in ("kalshi", "polymarket")
    )
    trades_path, trade_stats = normalize_trades(lookup, maximum_rows)
    news_path, news_stats = build_news_associations(markets, lookup)
    report_path = OUTPUT / "report.json"
    checks = {
        "corrected_cohort_rows": len(markets) == 4651,
        "normalized_trades_nonempty": trade_stats["normalized_rows"] > 0,
        "all_source_rows_accounted": trade_stats["raw_rows"]
        == sum(
            json.loads((RAW_TRADES / venue / "manifest.json").read_text())["rows"]
            for venue in ("kalshi", "polymarket")
        ),
        "zero_notional_policy_applied": trade_stats["zero_notional_excluded"] > 0,
        "news_associations_nonempty": news_stats["association_events"] > 0,
        "news_availability_days_at_least_56": news_stats["usable_calendar_days"] >= 56,
        "labels_or_outcomes_read": False,
        "holdout_prices_read": False,
    }
    passed = all(
        value is True
        for name, value in checks.items()
        if name not in {"labels_or_outcomes_read", "holdout_prices_read"}
    ) and checks["labels_or_outcomes_read"] is False and checks[
        "holdout_prices_read"
    ] is False
    report = {
        "protocol_id": protocol["protocol_id"],
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "prepared_label_blind_arrays" if passed else "failed",
        "integrity_pass": passed,
        "label_blind": True,
        "labels_or_outcomes_read": False,
        "holdout_prices_read": False,
        "dtypes": {
            "trades": TRADE_DTYPE.descr,
            "news_associations": NEWS_DTYPE.descr,
        },
        "terminal_metadata": terminal_stats,
        "trades": {
            **trade_stats,
            "path": relative(trades_path),
            "bytes": trades_path.stat().st_size,
            "sha256": sha256_file(trades_path),
        },
        "news": {
            **news_stats,
            "path": relative(news_path),
            "bytes": news_path.stat().st_size,
            "sha256": sha256_file(news_path),
        },
        "market_index": {
            "path": relative(market_index_path),
            "rows": len(indexed_markets),
            "sha256": sha256_file(market_index_path),
        },
        "checks": checks,
    }
    atomic_json(report_path, report)
    manifest_path = OUTPUT / "manifest.json"
    artifacts = (
        PROTOCOL,
        DATA_GATE,
        COHORT,
        KALSHI_METADATA,
        POLY_METADATA,
        Path(__file__).resolve(),
        market_index_path,
        trades_path,
        news_path,
        report_path,
    )
    atomic_json(
        manifest_path,
        {
            "protocol_id": protocol["protocol_id"],
            "status": "frozen_label_blind_prepared_arrays",
            "labels_or_outcomes_read": False,
            "holdout_prices_read": False,
            "artifacts": [
                {"path": relative(path), "sha256": sha256_file(path)}
                for path in artifacts
            ],
        },
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
