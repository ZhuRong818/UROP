"""Materialize a label-blind Lumid ``news.articles`` reconciliation snapshot.

This task uses Lumid FinData's read-only ``POST /retrieve`` surface.  It never reads
prediction-market outcomes or constructs EventX labels.  The resulting JSONL preserves
the article fields needed by the frozen news matcher and the Lumid provenance fields
needed to audit an endpoint-equivalent warehouse recovery.

Example:

    python -m eventx.tasks.export_v2_3_news_warehouse \
        --start 2026-08-08T00:00:00Z \
        --end 2026-08-28T00:00:00Z
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from eventx.settings import ApiSettings


DEFAULT_OUTPUT_ROOT = Path("data/v2_3_1/reconciliation/news_warehouse")
SELECTED_COLUMNS = (
    "id",
    "published_at",
    "ingest_ts",
    "symbol",
    "related_symbols",
    "publisher",
    "author",
    "category",
    "headline",
    "summary",
    "body",
    "lsa_summary",
    "luhn_summary",
    "textrank_summary",
    "lexrank_summary",
    "url",
    "image",
    "source",
    "source_endpoint",
    "source_run_id",
    "raw",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp must include a timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def sql_timestamp(value: datetime) -> str:
    # Values are parsed as datetimes before interpolation, so this does not accept
    # arbitrary SQL input.
    return rfc3339(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def fetch_json(client: httpx.Client, path: str) -> Any:
    response = client.get(path)
    response.raise_for_status()
    return response.json()


def retrieve(client: httpx.Client, sql: str) -> dict[str, Any]:
    response = client.post(
        "/retrieve",
        json={"sql": sql, "output_format": "jsonl"},
    )
    response.raise_for_status()
    value = response.json()
    if not isinstance(value, dict) or not value.get("materialized_uri"):
        raise RuntimeError("Lumid /retrieve did not return a materialized_uri")
    return value


def download_materialized(
    client: httpx.Client,
    uri: str,
    destination: Path,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    with client.stream("GET", uri) as response:
        response.raise_for_status()
        with temporary.open("wb") as handle:
            for chunk in response.iter_bytes(1024 * 1024):
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
    os.replace(temporary, destination)


def summarize_jsonl(path: Path, start: datetime, end: datetime) -> dict[str, Any]:
    ids: set[int | str] = set()
    urls: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    endpoints: Counter[str] = Counter()
    source_runs: Counter[str] = Counter()
    published_days: Counter[str] = Counter()
    invalid_json = 0
    missing_required = 0
    out_of_window = 0
    rows = 0
    min_published: datetime | None = None
    max_published: datetime | None = None
    min_ingest: datetime | None = None
    max_ingest: datetime | None = None

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                invalid_json += 1
                raise RuntimeError(f"invalid JSON on line {line_number}: {exc}") from exc
            rows += 1
            identifier = record.get("id")
            published_text = record.get("published_at")
            url = record.get("url")
            if identifier is None or not published_text or not url:
                missing_required += 1
                continue
            ids.add(identifier)
            urls[str(url)] += 1
            sources[str(record.get("source") or "<missing>")] += 1
            endpoints[str(record.get("source_endpoint") or "<missing>")] += 1
            source_runs[str(record.get("source_run_id") or "<missing>")] += 1

            published = parse_utc(str(published_text))
            if not start <= published < end:
                out_of_window += 1
            published_days[published.date().isoformat()] += 1
            min_published = published if min_published is None else min(min_published, published)
            max_published = published if max_published is None else max(max_published, published)

            ingest_text = record.get("ingest_ts")
            if ingest_text:
                ingest = parse_utc(str(ingest_text))
                min_ingest = ingest if min_ingest is None else min(min_ingest, ingest)
                max_ingest = ingest if max_ingest is None else max(max_ingest, ingest)

    duplicate_ids = rows - len(ids)
    duplicate_url_rows = sum(count - 1 for count in urls.values() if count > 1)
    return {
        "rows": rows,
        "unique_ids": len(ids),
        "duplicate_id_rows": duplicate_ids,
        "unique_urls": len(urls),
        "duplicate_url_rows": duplicate_url_rows,
        "invalid_json_rows": invalid_json,
        "missing_required_rows": missing_required,
        "out_of_window_rows": out_of_window,
        "published_at_min": rfc3339(min_published) if min_published else None,
        "published_at_max": rfc3339(max_published) if max_published else None,
        "ingest_ts_min": rfc3339(min_ingest) if min_ingest else None,
        "ingest_ts_max": rfc3339(max_ingest) if max_ingest else None,
        "rows_by_published_day": dict(sorted(published_days.items())),
        "rows_by_source": dict(sorted(sources.items())),
        "rows_by_source_endpoint": dict(sorted(endpoints.items())),
        "distinct_source_run_ids": len(source_runs),
    }


def build_sql(start: datetime, end: datetime) -> str:
    columns = ",\n       ".join(SELECTED_COLUMNS)
    return (
        f"SELECT {columns}\n"
        "FROM news.articles\n"
        f"WHERE published_at >= TIMESTAMPTZ '{sql_timestamp(start)}'\n"
        f"  AND published_at < TIMESTAMPTZ '{sql_timestamp(end)}'\n"
        "ORDER BY id"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, help="inclusive RFC3339 UTC start")
    parser.add_argument("--end", required=True, help="exclusive RFC3339 UTC end")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--timeout", type=float, default=600.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    start = parse_utc(args.start)
    end = parse_utc(args.end)
    if start >= end:
        raise SystemExit("--start must be before --end")
    if end > utc_now():
        raise SystemExit("--end cannot be in the future")

    stamp = f"{start:%Y%m%dT%H%M%SZ}_{end:%Y%m%dT%H%M%SZ}"
    root = args.output_root / stamp
    data_path = root / "news_articles.jsonl"
    receipt_path = root / "retrieve_receipt.json"
    manifest_path = root / "manifest.json"
    query_path = root / "query.sql"
    catalog_root = root / "catalog"
    root.mkdir(parents=True, exist_ok=True)

    sql = build_sql(start, end)
    query_path.write_text(sql + "\n", encoding="utf-8")
    settings = ApiSettings.from_env()
    headers = {"Authorization": f"Bearer {settings.token}"}
    started_at = utc_now()
    with httpx.Client(
        base_url=settings.base_url,
        headers=headers,
        timeout=httpx.Timeout(args.timeout),
        follow_redirects=True,
    ) as client:
        receipt = retrieve(client, sql)
        receipt["requested_at"] = rfc3339(started_at)
        receipt["base_url"] = settings.base_url
        write_json(receipt_path, receipt)
        download_materialized(client, str(receipt["materialized_uri"]), data_path)

        catalog_artifacts = {
            "schemas.json": fetch_json(client, "/catalog/schemas"),
            "news_tables.json": fetch_json(client, "/catalog/schemas/news/tables"),
            "news_articles_table.json": fetch_json(client, "/catalog/tables/news/articles"),
            "news_articles_schema.json": fetch_json(
                client, "/catalog/tables/news/articles/schema.json"
            ),
            "sources.json": fetch_json(client, "/catalog/sources"),
            "lineage_runs.json": fetch_json(client, "/catalog/lineage/runs?limit=1000"),
        }
        for name, value in catalog_artifacts.items():
            write_json(catalog_root / name, value)

    completed_at = utc_now()
    summary = summarize_jsonl(data_path, start, end)
    receipt_rowcount = int(receipt.get("rowcount", -1))
    integrity_pass = (
        summary["rows"] == receipt_rowcount
        and summary["duplicate_id_rows"] == 0
        and summary["invalid_json_rows"] == 0
        and summary["missing_required_rows"] == 0
        and summary["out_of_window_rows"] == 0
    )
    manifest = {
        "protocol_id": "eventx-v2.3-news-availability-clarifications-20260817",
        "implementation_id": "eventx-v2.3-news-implementation-v2-20260827",
        "purpose": "label-blind Lumid news warehouse reconciliation snapshot",
        "source": {
            "base_url": settings.base_url,
            "method": "POST",
            "endpoint": "/retrieve",
            "table": "news.articles",
            "materialized_uri": receipt.get("materialized_uri"),
            "retrieve_run_id": receipt.get("run_id"),
        },
        "window": {
            "start_inclusive": rfc3339(start),
            "end_exclusive": rfc3339(end),
            "field": "published_at",
        },
        "requested_at": rfc3339(started_at),
        "completed_at": rfc3339(completed_at),
        "selected_columns": list(SELECTED_COLUMNS),
        "summary": summary,
        "retrieve_rowcount": receipt_rowcount,
        "integrity_pass": integrity_pass,
        "artifacts": {
            "data": {
                "path": str(data_path),
                "bytes": data_path.stat().st_size,
                "sha256": sha256_file(data_path),
            },
            "query": {
                "path": str(query_path),
                "bytes": query_path.stat().st_size,
                "sha256": sha256_file(query_path),
            },
            "retrieve_receipt": {
                "path": str(receipt_path),
                "bytes": receipt_path.stat().st_size,
                "sha256": sha256_file(receipt_path),
            },
            "catalog": {
                name: {
                    "path": str(catalog_root / name),
                    "bytes": (catalog_root / name).stat().st_size,
                    "sha256": sha256_file(catalog_root / name),
                }
                for name in sorted(catalog_artifacts)
            },
        },
        "point_in_time_note": (
            "Warehouse ingest_ts is retained as Lumid provenance. Primary EventX "
            "first_seen_at remains the earliest successful EventX retrieval across "
            "valid Lumid paths; this export does not backdate primary B1 features."
        ),
        "labels_or_outcomes_read": False,
    }
    write_json(manifest_path, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if not integrity_pass:
        raise SystemExit("warehouse snapshot integrity checks failed")


if __name__ == "__main__":
    main()
