"""Run a label-blind Lumid sufficiency rehearsal on the frozen EventX cohort.

This task retrieves only market metadata, trades, news, service health, and the
OpenAPI contract. It never constructs or reads jump labels, prevalence, folds,
predictions, or model metrics.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Iterator

import httpx

from eventx.features.v2_1_association import GENERIC
from eventx.ingest.client import FindataClient
from eventx.settings import ApiSettings, REPO_ROOT


OFFICIAL_BASE_URL = "https://lum.id/findata"
DEFAULT_PROTOCOL = REPO_ROOT / "eventx" / "release" / "v2_2" / "protocol.json"
DEFAULT_COHORT = REPO_ROOT / "data" / "v2_1" / "cohort" / "selected_markets.jsonl"
DEFAULT_COHORT_MANIFEST = (
    REPO_ROOT / "data" / "v2_1" / "cohort" / "cohort_freeze_manifest.json"
)
DEFAULT_MARKET_SPECS = (
    REPO_ROOT / "data" / "v2_1" / "association" / "v1_audit" / "market_specs.jsonl"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "data"
    / "v2_2"
    / "planning"
    / "lumid_subwindow_20260808_20260817"
)
REQUIRED_ENDPOINTS = {
    "/freshness",
    "/health",
    "/news/latest",
    "/news/search",
    "/prediction-markets/markets/kalshi/{ticker}",
    "/prediction-markets/markets/polymarket/{condition_id}",
    "/prediction-markets/trades/kalshi/{ticker}",
    "/prediction-markets/trades/polymarket/{condition_id}",
    "/usage/me",
}
TIMESTAMP_KEY = {"polymarket": "ts", "kalshi": "created_time"}
TRADE_FIELDS = {
    "polymarket": {"trade_id", "ts", "token_id", "price", "size", "side"},
    "kalshi": {"trade_id", "created_time", "yes_price", "count", "taker_side"},
}


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def rfc3339(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def utc_now() -> datetime:
    return datetime.now(UTC)


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            yield value


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def stable_hash(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode()).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def response_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        for key in ("data", "articles", "trades", "results", "items"):
            rows = value.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def parsed_list(value: Any) -> list[str]:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        value = decoded
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def atomic_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text)
    temporary.replace(path)


def queries_from_spec(spec: dict[str, Any]) -> list[str]:
    queries: list[str] = []
    phrases = [str(value) for value in spec.get("phrases", [])]
    if phrases:
        cleaned = " ".join(
            token for token in phrases[0].split() if token.lower() not in GENERIC
        )
        if cleaned:
            queries.append(cleaned)
    anchors = [
        str(anchor)
        for anchor in sorted(spec.get("anchors", []), key=lambda value: (-len(value), value))
        if str(anchor) not in GENERIC
        and str(anchor) not in {"and", "control", "feb", "u.s"}
    ]
    event_terms = [str(value) for value in spec.get("event_terms", [])]
    if anchors:
        queries.append(" ".join([*anchors[:2], *event_terms[:1]]))
    elif event_terms:
        queries.append(" ".join(event_terms[:2]))
    return list(dict.fromkeys(query.strip() for query in queries if len(query.strip()) >= 3))


def trade_key(row: dict[str, Any], venue: str, market_id: str) -> str:
    trade_id = row.get("trade_id")
    if trade_id not in (None, ""):
        return f"{venue}:{trade_id}"
    return stable_hash([venue, market_id, row])


def validate_price(row: dict[str, Any], venue: str) -> bool:
    try:
        price = float(row["price"] if venue == "polymarket" else row["yes_price"])
        if venue == "kalshi" and price > 1:
            price /= 100
        return math.isfinite(price) and 0 <= price <= 1
    except (KeyError, TypeError, ValueError):
        return False


def date_keys(start: datetime, end: datetime) -> list[str]:
    current = start.date()
    stop = end.date()
    values: list[str] = []
    while current < stop:
        values.append(current.isoformat())
        current += timedelta(days=1)
    return values


def max_gap_minutes(timestamps: list[datetime]) -> float | None:
    if len(timestamps) < 2:
        return None
    ordered = sorted(timestamps)
    return max((right - left).total_seconds() / 60 for left, right in zip(ordered, ordered[1:]))


def fetch_market_detail(
    client: FindataClient,
    market: dict[str, Any],
    retrieved_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    venue = str(market["venue"])
    market_id = str(market["market_id"])
    endpoint = f"/prediction-markets/markets/{venue}/{market_id}"
    response = client.get(endpoint)
    if not isinstance(response, dict):
        raise ValueError("market detail response is not an object")
    checks: dict[str, Any] = {
        "canonical_yes_mapping": False,
        "endpoint": endpoint,
        "market_id": market_id,
        "required_fields_missing": [],
        "venue": venue,
    }
    if venue == "polymarket":
        required = {"condition_id", "question", "outcomes", "clob_token_ids"}
        checks["required_fields_missing"] = sorted(required - response.keys())
        outcomes = parsed_list(response.get("outcomes"))
        tokens = parsed_list(response.get("clob_token_ids"))
        yes_tokens = [tokens[i] for i, outcome in enumerate(outcomes) if i < len(tokens) and outcome.lower() == "yes"]
        checks["canonical_yes_mapping"] = (
            str(response.get("condition_id") or response.get("market_id")) == market_id
            and str(market["outcome_id"]) in yes_tokens
        )
        checks["outcomes"] = outcomes
        checks["yes_tokens"] = yes_tokens
    else:
        required = {"ticker", "title", "close_time", "status"}
        checks["required_fields_missing"] = sorted(required - response.keys())
        checks["canonical_yes_mapping"] = (
            str(response.get("ticker") or response.get("market_id")) == market_id
            and str(market["outcome_id"]).upper() == "YES"
        )
    checks["passed"] = not checks["required_fields_missing"] and checks["canonical_yes_mapping"]
    envelope = {
        "_protocol_id": "eventx-v2.2-october-pilot-fixes-20260817",
        "_retrieved_at": retrieved_at,
        "_source_endpoint": endpoint,
        "record": response,
    }
    return envelope, checks


def fetch_trades(
    client: FindataClient,
    market: dict[str, Any],
    start: datetime,
    end: datetime,
    page_limit: int,
    max_pages: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    venue = str(market["venue"])
    market_id = str(market["market_id"])
    endpoint = f"/prediction-markets/trades/{venue}/{market_id}"
    page_to = end
    previous_oldest: datetime | None = None
    seen: set[str] = set()
    retained: list[dict[str, Any]] = []
    day_counts: Counter[str] = Counter()
    timestamps: list[datetime] = []
    report: dict[str, Any] = {
        "canonical_yes_rows": 0,
        "duplicate_rows": 0,
        "endpoint": endpoint,
        "invalid_price_rows": 0,
        "invalid_timestamp_rows": 0,
        "market_id": market_id,
        "missing_field_rows": 0,
        "noncanonical_rows": 0,
        "out_of_window_rows": 0,
        "pages": 0,
        "response_rows": 0,
        "saturated_timestamp_boundary": False,
        "truncated": True,
        "venue": venue,
    }
    for _ in range(max_pages):
        retrieved_at = rfc3339(utc_now())
        response = client.get(
            endpoint,
            **{"from": rfc3339(start), "to": rfc3339(page_to), "limit": page_limit},
        )
        rows = response_rows(response)
        report["pages"] += 1
        report["response_rows"] += len(rows)
        page_timestamps: list[datetime] = []
        for row in rows:
            missing = TRADE_FIELDS[venue] - row.keys()
            if missing:
                report["missing_field_rows"] += 1
            value = row.get(TIMESTAMP_KEY[venue])
            if value in (None, ""):
                report["invalid_timestamp_rows"] += 1
                continue
            try:
                timestamp = parse_utc(str(value))
            except (TypeError, ValueError):
                report["invalid_timestamp_rows"] += 1
                continue
            page_timestamps.append(timestamp)
            if not start <= timestamp < end:
                report["out_of_window_rows"] += 1
                continue
            if venue == "polymarket" and str(row.get("token_id")) != str(market["outcome_id"]):
                report["noncanonical_rows"] += 1
                continue
            if not validate_price(row, venue):
                report["invalid_price_rows"] += 1
                continue
            key = trade_key(row, venue, market_id)
            if key in seen:
                report["duplicate_rows"] += 1
                continue
            seen.add(key)
            timestamps.append(timestamp)
            day_counts[timestamp.date().isoformat()] += 1
            retained.append(
                {
                    "_event_ts": rfc3339(timestamp),
                    "_protocol_id": "eventx-v2.2-october-pilot-fixes-20260817",
                    "_record_key": key,
                    "_retrieved_at": retrieved_at,
                    "_source_endpoint": endpoint,
                    "record": {**row, "market_id": market_id, "venue": venue},
                }
            )
            report["canonical_yes_rows"] += 1
        complete = len(rows) < page_limit
        if not rows:
            complete = True
        elif not page_timestamps:
            report["error"] = "page contained no parseable timestamps"
            break
        else:
            oldest = min(page_timestamps)
            if oldest <= start:
                complete = True
            if len(rows) >= page_limit and sum(ts == oldest for ts in page_timestamps) == len(rows):
                report["saturated_timestamp_boundary"] = True
                report["error"] = "saturated page contains one timestamp; safe pagination unavailable"
                break
            if previous_oldest is not None and oldest >= previous_oldest:
                report["error"] = "backward pagination made no timestamp progress"
                break
            previous_oldest = oldest
            page_to = oldest
        if complete:
            report["truncated"] = False
            break
    report["earliest_event"] = rfc3339(min(timestamps)) if timestamps else None
    report["latest_event"] = rfc3339(max(timestamps)) if timestamps else None
    report["max_intertrade_gap_minutes"] = max_gap_minutes(timestamps)
    report["rows_retained"] = len(retained)
    report["rows_by_day"] = {day: day_counts.get(day, 0) for day in date_keys(start, end)}
    report["zero_trade_days"] = [day for day, count in report["rows_by_day"].items() if count == 0]
    report["passed_endpoint_integrity"] = (
        not report.get("error")
        and not report["truncated"]
        and report["invalid_timestamp_rows"] == 0
        and report["invalid_price_rows"] == 0
        and report["missing_field_rows"] == 0
    )
    retained.sort(key=lambda row: (row["record"]["market_id"], row["_event_ts"], row["_record_key"]))
    return retained, report


def news_key(row: dict[str, Any]) -> str:
    natural = row.get("url") or row.get("id") or row.get("article_id")
    return stable_hash(["news", natural if natural else row])


def fetch_news_request(
    client: FindataClient,
    *,
    endpoint: str,
    start: datetime,
    end: datetime,
    limit: int,
    query: str | None,
    market_ids: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params: dict[str, Any] = {"since": rfc3339(start), "limit": limit}
    if query is not None:
        params["q"] = query
    retrieved_at = rfc3339(utc_now())
    response = client.get(endpoint, **params)
    rows = response_rows(response)
    retained: list[dict[str, Any]] = []
    seen: set[str] = set()
    invalid_timestamp = future_timestamp = out_of_window = duplicates = missing_fields = 0
    day_counts: Counter[str] = Counter()
    for row in rows:
        if not {"published_at", "headline", "publisher"}.issubset(row):
            missing_fields += 1
        value = row.get("published_at")
        if value in (None, ""):
            invalid_timestamp += 1
            continue
        try:
            timestamp = parse_utc(str(value))
        except (TypeError, ValueError):
            invalid_timestamp += 1
            continue
        if timestamp > parse_utc(retrieved_at):
            future_timestamp += 1
        if not start <= timestamp < end:
            out_of_window += 1
            continue
        key = news_key(row)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        day_counts[timestamp.date().isoformat()] += 1
        retained.append(
            {
                "_event_ts": rfc3339(timestamp),
                "_protocol_id": "eventx-v2.2-october-pilot-fixes-20260817",
                "_record_key": key,
                "_retrieved_at": retrieved_at,
                "_search_market_ids": market_ids,
                "_search_query": query,
                "_source_endpoint": endpoint,
                "record": row,
            }
        )
    possible_cap = len(rows) in {200, 500, 1000} and len(rows) < limit
    report = {
        "duplicate_rows": duplicates,
        "endpoint": endpoint,
        "future_timestamp_rows": future_timestamp,
        "invalid_timestamp_rows": invalid_timestamp,
        "limit_requested": limit,
        "market_ids": market_ids,
        "missing_field_rows": missing_fields,
        "out_of_window_rows": out_of_window,
        "possible_undocumented_server_cap": possible_cap,
        "query": query,
        "response_rows": len(rows),
        "rows_by_day": {day: day_counts.get(day, 0) for day in date_keys(start, end)},
        "rows_retained": len(retained),
        "truncation_risk": len(rows) >= limit or possible_cap,
    }
    retained.sort(key=lambda row: (row["_event_ts"], row["_record_key"]))
    return retained, report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# EventX v2.2 label-blind Lumid subwindow drill",
        "",
        f"**Status:** `{report['status']}`  ",
        f"**Window:** `{report['window']['start']}` to `{report['window']['end_exclusive']}`  ",
        f"**Completed:** `{report['completed_at']}`  ",
        "**Labels read:** none",
        "",
        "## Gate summary",
        "",
        f"- OpenAPI required routes present: `{report['openapi']['required_routes_present']}`.",
        f"- Market-detail canonical mappings passed: `{report['summary']['market_details_passed']}/14`.",
        f"- Trade endpoints passing integrity: `{report['summary']['trade_markets_integrity_passed']}/14`.",
        f"- Canonical-YES trades retained: `{report['summary']['trade_rows_retained']}`.",
        f"- Frozen news queries: `{report['summary']['news_queries']}`.",
        f"- News requests with truncation risk: `{report['summary']['news_requests_with_truncation_risk']}`.",
        f"- Future-dated news rows quarantined: `{report['summary']['future_news_rows']}`.",
        "",
        "A passing rehearsal validates the mechanics only. The final development and",
        "holdout exact-window sufficiency gates remain mandatory.",
        "",
        "## Blocking reasons",
        "",
    ]
    reasons = report.get("blocking_reasons", [])
    if reasons:
        lines.extend(f"- {reason}" for reason in reasons)
    else:
        lines.append("- None for this elapsed-window rehearsal.")
    lines.extend(["", "## Per-market trade coverage", ""])
    lines.append("| Venue | Market | Rows | Pages | Earliest | Latest | Zero-trade days | Integrity |")
    lines.append("|---|---|---:|---:|---|---|---:|---|")
    for item in report["trades"]:
        lines.append(
            "| {venue} | `{market_id}` | {rows_retained} | {pages} | {earliest} | "
            "{latest} | {zero_days} | {passed} |".format(
                venue=item["venue"],
                market_id=item["market_id"],
                rows_retained=item["rows_retained"],
                pages=item["pages"],
                earliest=item["earliest_event"] or "—",
                latest=item["latest_event"] or "—",
                zero_days=len(item["zero_trade_days"]),
                passed="pass" if item["passed_endpoint_integrity"] else "fail",
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This audit does not construct jump labels, calculate prevalence, create folds,",
            "fit a model, or inspect the October holdout. Empty market-days are reported",
            "rather than treated as API failures; final eligibility and label support are",
            "assessed only after the frozen development window closes.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    parser.add_argument("--cohort-manifest", type=Path, default=DEFAULT_COHORT_MANIFEST)
    parser.add_argument("--market-specs", type=Path, default=DEFAULT_MARKET_SPECS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--start", default="2026-08-08T00:00:00Z")
    parser.add_argument("--end", default="2026-08-17T00:00:00Z")
    parser.add_argument("--trade-limit", type=int, default=1000)
    parser.add_argument("--news-limit", type=int, default=5000)
    parser.add_argument("--max-trade-pages", type=int, default=100)
    parser.add_argument("--rpm", type=int, default=45)
    args = parser.parse_args()

    protocol = load_json(args.protocol)
    cohort_manifest = load_json(args.cohort_manifest)
    start = parse_utc(args.start)
    end = parse_utc(args.end)
    now = utc_now()
    if protocol.get("protocol_id") != "eventx-v2.2-october-pilot-fixes-20260817":
        raise SystemExit("wrong protocol")
    if protocol.get("status") != "preregistered_labels_uninspected":
        raise SystemExit("protocol label seal is not active")
    development = protocol["windows"]["development"]
    if start < parse_utc(development["start"]) or end > parse_utc(development["end_exclusive"]):
        raise SystemExit("audit window is outside v2.2 development")
    if end > now:
        raise SystemExit("audit end must be fully elapsed")
    if sha256_file(args.cohort) != protocol["cohort"]["selected_markets_sha256"]:
        raise SystemExit("selected-market hash does not match v2.2 protocol")
    if sha256_file(args.cohort) != cohort_manifest.get("output", {}).get("sha256"):
        raise SystemExit("selected-market hash does not match cohort manifest")

    markets = sorted(read_jsonl(args.cohort), key=lambda row: (row["venue"], row["market_id"]))
    if len(markets) != 14:
        raise SystemExit("expected exactly 14 frozen markets")
    market_ids = {str(row["market_id"]) for row in markets}
    query_markets: dict[str, set[str]] = {}
    for row in read_jsonl(args.market_specs):
        market_id = str(row.get("market_id") or "")
        if market_id not in market_ids:
            continue
        spec = row.get("spec")
        if not isinstance(spec, dict):
            raise SystemExit(f"missing market spec for {market_id}")
        for query in queries_from_spec(spec):
            query_markets.setdefault(query, set()).add(market_id)

    openapi_response = httpx.get(f"{OFFICIAL_BASE_URL}/openapi.json", timeout=30)
    openapi_response.raise_for_status()
    openapi_bytes = openapi_response.content
    openapi = openapi_response.json()
    openapi_paths = set(openapi.get("paths", {}))
    missing_routes = sorted(REQUIRED_ENDPOINTS - openapi_paths)
    args.output.mkdir(parents=True, exist_ok=True)
    openapi_path = args.output / "lumid_openapi.json"
    openapi_path.write_bytes(openapi_bytes)

    settings = ApiSettings.from_env()
    lumid_settings = ApiSettings(token=settings.token, base_url=OFFICIAL_BASE_URL)
    market_envelopes: list[dict[str, Any]] = []
    detail_reports: list[dict[str, Any]] = []
    trade_outputs: dict[str, list[dict[str, Any]]] = {"kalshi": [], "polymarket": []}
    trade_reports: list[dict[str, Any]] = []
    news_rows: list[dict[str, Any]] = []
    news_reports: list[dict[str, Any]] = []
    endpoint_errors: list[dict[str, str]] = []
    controls: dict[str, Any] = {}
    with FindataClient(settings=lumid_settings, rpm=args.rpm, timeout=60.0) as client:
        for endpoint in ("/health", "/freshness", "/usage/me"):
            try:
                controls[endpoint] = client.get(endpoint)
            except Exception as exc:
                endpoint_errors.append({"endpoint": endpoint, "error": f"{type(exc).__name__}: {exc}"[:500]})
        for market in markets:
            try:
                envelope, detail_report = fetch_market_detail(client, market, rfc3339(utc_now()))
                market_envelopes.append(envelope)
                detail_reports.append(detail_report)
            except Exception as exc:
                detail_reports.append(
                    {
                        "canonical_yes_mapping": False,
                        "error": f"{type(exc).__name__}: {exc}"[:500],
                        "market_id": str(market["market_id"]),
                        "passed": False,
                        "venue": str(market["venue"]),
                    }
                )
                endpoint_errors.append(
                    {
                        "endpoint": f"/prediction-markets/markets/{market['venue']}/{market['market_id']}",
                        "error": f"{type(exc).__name__}: {exc}"[:500],
                    }
                )
            try:
                rows, trade_report = fetch_trades(
                    client,
                    market,
                    start,
                    end,
                    args.trade_limit,
                    args.max_trade_pages,
                )
                trade_outputs[str(market["venue"])].extend(rows)
                trade_reports.append(trade_report)
            except Exception as exc:
                trade_reports.append(
                    {
                        "error": f"{type(exc).__name__}: {exc}"[:500],
                        "market_id": str(market["market_id"]),
                        "pages": 0,
                        "passed_endpoint_integrity": False,
                        "rows_retained": 0,
                        "venue": str(market["venue"]),
                        "zero_trade_days": date_keys(start, end),
                        "earliest_event": None,
                        "latest_event": None,
                    }
                )
                endpoint_errors.append(
                    {
                        "endpoint": f"/prediction-markets/trades/{market['venue']}/{market['market_id']}",
                        "error": f"{type(exc).__name__}: {exc}"[:500],
                    }
                )
        try:
            rows, news_report = fetch_news_request(
                client,
                endpoint="/news/latest",
                start=start,
                end=end,
                limit=args.news_limit,
                query=None,
                market_ids=sorted(market_ids),
            )
            news_rows.extend(rows)
            news_reports.append(news_report)
        except Exception as exc:
            endpoint_errors.append({"endpoint": "/news/latest", "error": f"{type(exc).__name__}: {exc}"[:500]})
        for query in sorted(query_markets):
            try:
                rows, news_report = fetch_news_request(
                    client,
                    endpoint="/news/search",
                    start=start,
                    end=end,
                    limit=args.news_limit,
                    query=query,
                    market_ids=sorted(query_markets[query]),
                )
                news_rows.extend(rows)
                news_reports.append(news_report)
            except Exception as exc:
                endpoint_errors.append(
                    {"endpoint": "/news/search", "query": query, "error": f"{type(exc).__name__}: {exc}"[:500]}
                )

    market_envelopes.sort(key=lambda row: row["_source_endpoint"])
    trade_reports.sort(key=lambda row: (row["venue"], row["market_id"]))
    detail_reports.sort(key=lambda row: (row["venue"], row["market_id"]))
    news_reports.sort(key=lambda row: (row["endpoint"], row.get("query") or ""))
    deduped_news: dict[str, dict[str, Any]] = {}
    for row in news_rows:
        deduped_news.setdefault(row["_record_key"], row)
    news_rows = sorted(deduped_news.values(), key=lambda row: (row["_event_ts"], row["_record_key"]))
    for venue in trade_outputs:
        deduped = {row["_record_key"]: row for row in trade_outputs[venue]}
        trade_outputs[venue] = sorted(
            deduped.values(),
            key=lambda row: (row["record"]["market_id"], row["_event_ts"], row["_record_key"]),
        )

    output_paths = {
        "market_details": args.output / "market_details.jsonl",
        "news": args.output / "news.jsonl",
        "trades_kalshi": args.output / "trades_kalshi.jsonl",
        "trades_polymarket": args.output / "trades_polymarket.jsonl",
    }
    atomic_jsonl(output_paths["market_details"], market_envelopes)
    atomic_jsonl(output_paths["news"], news_rows)
    atomic_jsonl(output_paths["trades_kalshi"], trade_outputs["kalshi"])
    atomic_jsonl(output_paths["trades_polymarket"], trade_outputs["polymarket"])

    blocking_reasons: list[str] = []
    if missing_routes:
        blocking_reasons.append(f"OpenAPI missing required routes: {missing_routes}")
    if endpoint_errors:
        blocking_reasons.append(f"{len(endpoint_errors)} endpoint requests failed")
    failed_details = [row for row in detail_reports if not row.get("passed")]
    if failed_details:
        blocking_reasons.append(f"{len(failed_details)} market-detail canonical mappings failed")
    failed_trades = [row for row in trade_reports if not row.get("passed_endpoint_integrity")]
    if failed_trades:
        blocking_reasons.append(f"{len(failed_trades)} market trade endpoints failed integrity")
    news_truncation = [row for row in news_reports if row.get("truncation_risk")]
    if news_truncation:
        blocking_reasons.append(f"{len(news_truncation)} news requests have unresolved truncation risk")

    future_news = sum(int(row.get("future_timestamp_rows", 0)) for row in news_reports)
    report: dict[str, Any] = {
        "blocking_reasons": blocking_reasons,
        "completed_at": rfc3339(utc_now()),
        "controls": controls,
        "endpoint_errors": endpoint_errors,
        "input_hashes": {
            relative(args.cohort): sha256_file(args.cohort),
            relative(args.cohort_manifest): sha256_file(args.cohort_manifest),
            relative(args.market_specs): sha256_file(args.market_specs),
            relative(args.protocol): sha256_file(args.protocol),
        },
        "label_blind": True,
        "labels_created": [],
        "labels_read": [],
        "market_details": detail_reports,
        "news": news_reports,
        "openapi": {
            "bytes": len(openapi_bytes),
            "missing_required_routes": missing_routes,
            "path": relative(openapi_path),
            "paths": len(openapi_paths),
            "required_routes_present": not missing_routes,
            "sha256": sha256_bytes(openapi_bytes),
        },
        "output_artifacts": {
            name: {"bytes": path.stat().st_size, "path": relative(path), "sha256": sha256_file(path)}
            for name, path in output_paths.items()
        },
        "protocol_id": protocol["protocol_id"],
        "status": "pass" if not blocking_reasons else "incomplete",
        "summary": {
            "future_news_rows": future_news,
            "market_details_passed": sum(bool(row.get("passed")) for row in detail_reports),
            "news_queries": len(query_markets),
            "news_requests": len(news_reports),
            "news_requests_with_truncation_risk": len(news_truncation),
            "news_rows_retained_unique": len(news_rows),
            "trade_markets_integrity_passed": sum(
                bool(row.get("passed_endpoint_integrity")) for row in trade_reports
            ),
            "trade_rows_retained": sum(len(rows) for rows in trade_outputs.values()),
            "zero_record_markets": [
                f"{row['venue']}:{row['market_id']}" for row in trade_reports if row.get("rows_retained") == 0
            ],
        },
        "trades": trade_reports,
        "window": {"end_exclusive": rfc3339(end), "start": rfc3339(start)},
    }
    report_path = args.output / "audit_report.json"
    atomic_json(report_path, report)
    markdown_path = args.output / "AUDIT_REPORT.md"
    atomic_text(markdown_path, render_markdown(report))
    print(
        json.dumps(
            {
                "blocking_reasons": blocking_reasons,
                "labels_read": [],
                "report": relative(report_path),
                "status": report["status"],
                "summary": report["summary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    if blocking_reasons:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
