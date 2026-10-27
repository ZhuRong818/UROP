"""Read-only black-box audit of Lumid Studio's FinData warehouse surface.

The task inventories catalog/discovery features and exercises safe SELECT-only
materialisation queries.  It never issues DDL/DML, reads EventX labels or outcomes,
or accesses the October holdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from eventx.settings import ApiSettings


DEFAULT_OUTPUT = Path("data/v2_3_1/lumid_studio_audit_20260829/report.json")
SENSITIVE_KEY = re.compile(
    r"(authorization|cookie|password|passwd|secret|token|api.?key|dsn|credential)",
    re.IGNORECASE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "<redacted>" if SENSITIVE_KEY.search(str(key)) else sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str) and ("Bearer " in value or "password=" in value.lower()):
        return "<redacted>"
    return value


def safe_uri(value: str) -> str:
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def body_summary(response: httpx.Response) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
        "bytes": len(response.content),
    }
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError):
        text = response.text.strip()
        result["text_preview"] = text[:500]
    else:
        result["json"] = sanitize(payload)
    return result


def request_json(client: httpx.Client, path: str) -> tuple[dict[str, Any], Any | None]:
    started = time.perf_counter()
    try:
        response = client.get(path)
    except httpx.HTTPError as exc:
        return {
            "request": path,
            "exception": type(exc).__name__,
            "message": str(exc)[:500],
            "elapsed_seconds": time.perf_counter() - started,
        }, None
    summary = body_summary(response)
    summary["request"] = path
    summary["elapsed_seconds"] = time.perf_counter() - started
    try:
        payload = response.json() if response.is_success else None
    except (ValueError, json.JSONDecodeError):
        payload = None
    return summary, payload


def named_items(payload: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    values = payload
    if isinstance(payload, dict):
        for key in keys:
            if isinstance(payload.get(key), list):
                values = payload[key]
                break
    if not isinstance(values, list):
        return []
    result = []
    for value in values:
        if isinstance(value, str):
            result.append({"name": value})
        elif isinstance(value, dict):
            result.append(value)
    return result


def item_name(value: dict[str, Any], candidates: tuple[str, ...]) -> str | None:
    for key in candidates:
        item = value.get(key)
        if isinstance(item, str) and item:
            return item
    return None


def materialize(
    client: httpx.Client,
    *,
    name: str,
    sql: str,
    output_format: str = "jsonl",
    download_limit_bytes: int = 8_000_000,
    capture_jsonl_rows: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    result: dict[str, Any] = {
        "name": name,
        "output_format": output_format,
        "sql_sha256": hashlib.sha256(sql.encode()).hexdigest(),
        "select_only": sql.lstrip().upper().startswith(("SELECT", "WITH")),
    }
    try:
        response = client.post(
            "/retrieve",
            json={"sql": sql, "output_format": output_format},
        )
    except httpx.HTTPError as exc:
        result.update(
            {
                "exception": type(exc).__name__,
                "message": str(exc)[:500],
                "elapsed_seconds": time.perf_counter() - started,
            }
        )
        return result
    result["submit"] = body_summary(response)
    result["elapsed_seconds"] = time.perf_counter() - started
    if not response.is_success:
        return result
    try:
        receipt = response.json()
    except (ValueError, json.JSONDecodeError):
        return result
    if not isinstance(receipt, dict):
        return result
    result["receipt"] = {
        key: safe_uri(str(value)) if key == "materialized_uri" else sanitize(value)
        for key, value in receipt.items()
        if key != "materialized_uri" or value
    }
    uri = receipt.get("materialized_uri")
    if not isinstance(uri, str) or not uri:
        return result
    download_started = time.perf_counter()
    try:
        with client.stream("GET", uri) as download:
            result["download_status_code"] = download.status_code
            result["download_content_type"] = download.headers.get("content-type")
            chunks: list[bytes] = []
            size = 0
            truncated = False
            for chunk in download.iter_bytes():
                if size + len(chunk) > download_limit_bytes:
                    remaining = max(0, download_limit_bytes - size)
                    chunks.append(chunk[:remaining])
                    size += remaining
                    truncated = True
                    break
                chunks.append(chunk)
                size += len(chunk)
            data = b"".join(chunks)
    except httpx.HTTPError as exc:
        result["download_exception"] = type(exc).__name__
        result["download_message"] = str(exc)[:500]
        return result
    result["download_seconds"] = time.perf_counter() - download_started
    result["downloaded_bytes"] = len(data)
    result["download_truncated"] = truncated
    result["download_sha256"] = hashlib.sha256(data).hexdigest()
    if output_format == "jsonl":
        lines = [line for line in data.splitlines() if line.strip()]
        result["downloaded_rows"] = len(lines)
        result["jsonl_parse_failures"] = sum(
            1 for line in lines if not _valid_json(line)
        )
        if capture_jsonl_rows and result["jsonl_parse_failures"] == 0:
            result["jsonl_rows"] = sanitize(
                [json.loads(line) for line in lines[:500]]
            )
    elif output_format == "csv":
        lines = [line for line in data.splitlines() if line.strip()]
        result["csv_data_rows"] = max(0, len(lines) - 1)
        result["csv_has_header"] = bool(lines)
    elif output_format == "parquet":
        result["parquet_magic_valid"] = data[:4] == b"PAR1" and data[-4:] == b"PAR1"
    return result


def _valid_json(line: bytes) -> bool:
    try:
        json.loads(line)
    except (ValueError, json.JSONDecodeError):
        return False
    return True


def _duplicate_operation_ids(paths: Any) -> dict[str, list[str]]:
    if not isinstance(paths, dict):
        return {}
    observed: dict[str, list[str]] = {}
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "options",
                "head",
            } or not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if isinstance(operation_id, str) and operation_id:
                observed.setdefault(operation_id, []).append(
                    f"{method.upper()} {path}"
                )
    return {
        operation_id: locations
        for operation_id, locations in sorted(observed.items())
        if len(locations) > 1
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=float, default=180.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = ApiSettings.from_env()
    parsed_base = urlsplit(settings.base_url)
    origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
    headers = {"Authorization": f"Bearer {settings.token}"}
    report: dict[str, Any] = {
        "audit_id": f"eventx-lumid-studio-read-only-audit-{datetime.now(timezone.utc):%Y%m%d}",
        "created_at": utc_now(),
        "scope": "public Studio shell plus authenticated FinData read/discovery surface",
        "integrity": {
            "read_only": True,
            "ddl_or_dml_issued": False,
            "labels_read": [],
            "outcomes_read": [],
            "trade_prices_read": [],
            "holdout_accessed": False,
        },
    }

    with httpx.Client(timeout=httpx.Timeout(args.timeout), follow_redirects=True) as public:
        studio_started = time.perf_counter()
        studio = public.get(f"{origin}/studio")
        studio_text = studio.text
        report["studio_shell"] = {
            "status_code": studio.status_code,
            "final_path": urlsplit(str(studio.url)).path,
            "content_type": studio.headers.get("content-type"),
            "title": _html_title(studio_text),
            "authentication_shell": "/auth/assets/" in studio_text,
            "script_paths": sorted(set(re.findall(r'<script[^>]+src="([^"]+)"', studio_text))),
            "elapsed_seconds": time.perf_counter() - studio_started,
        }
        unauth = httpx.Client(
            base_url=settings.base_url,
            timeout=httpx.Timeout(args.timeout),
            follow_redirects=True,
        )
        try:
            report["unauthenticated_catalog"] = body_summary(unauth.get("/catalog/schemas"))
        finally:
            unauth.close()

    with httpx.Client(
        base_url=settings.base_url,
        headers=headers,
        timeout=httpx.Timeout(args.timeout),
        follow_redirects=True,
    ) as client:
        openapi_summary, openapi = request_json(client, "/openapi.json")
        report["openapi_request"] = openapi_summary
        paths = openapi.get("paths", {}) if isinstance(openapi, dict) else {}
        report["openapi"] = {
            "title": (openapi.get("info") or {}).get("title")
            if isinstance(openapi, dict)
            else None,
            "version": (openapi.get("info") or {}).get("version")
            if isinstance(openapi, dict)
            else None,
            "path_count": len(paths) if isinstance(paths, dict) else 0,
            "retrieve_documented": "/retrieve" in paths,
            "catalog_paths": sorted(path for path in paths if path.startswith("/catalog/")),
            "stream_paths": sorted(path for path in paths if path.endswith("/stream")),
            "mcp_documented": "/mcp" in paths,
            "duplicate_operation_ids": _duplicate_operation_ids(paths),
        }

        catalog_requests: dict[str, Any] = {}
        schemas_summary, schemas_payload = request_json(client, "/catalog/schemas")
        catalog_requests["schemas"] = schemas_summary
        schema_items = named_items(schemas_payload, ("schemas", "items", "data"))
        table_targets: list[tuple[str, str, dict[str, Any]]] = []
        for schema_item in schema_items:
            schema = item_name(schema_item, ("name", "schema", "schema_name"))
            if not schema:
                continue
            tables_summary, tables_payload = request_json(
                client, f"/catalog/schemas/{schema}/tables"
            )
            catalog_requests[f"tables:{schema}"] = tables_summary
            table_items = named_items(tables_payload, ("tables", "items", "data"))
            print(f"catalog_schema={schema} tables={len(table_items)}", flush=True)
            for table_item in table_items:
                table = item_name(table_item, ("name", "table", "table_name"))
                if not table:
                    continue
                table_targets.append((schema, table, table_item))

        def inspect_table(
            target: tuple[str, str, dict[str, Any]],
        ) -> dict[str, Any]:
            schema, table, table_item = target
            with httpx.Client(
                base_url=settings.base_url,
                headers=headers,
                timeout=httpx.Timeout(args.timeout),
                follow_redirects=True,
            ) as table_client:
                profile_summary, profile_payload = request_json(
                    table_client, f"/catalog/tables/{schema}/{table}"
                )
                shape_summary, shape_payload = request_json(
                    table_client, f"/catalog/tables/{schema}/{table}/schema.json"
                )
            properties = (
                shape_payload.get("properties", {})
                if isinstance(shape_payload, dict)
                else {}
            )
            return {
                "schema": schema,
                "table": table,
                "table_listing": sanitize(table_item),
                "profile_request": profile_summary,
                "profile": sanitize(profile_payload),
                "schema_request": shape_summary,
                "column_count": len(properties) if isinstance(properties, dict) else None,
                "columns": sorted(properties) if isinstance(properties, dict) else [],
            }

        with ThreadPoolExecutor(max_workers=8) as pool:
            inventory = sorted(
                pool.map(inspect_table, table_targets),
                key=lambda value: (value["schema"], value["table"]),
            )
        report["catalog_requests"] = catalog_requests
        report["catalog_inventory"] = inventory
        report["catalog_summary"] = {
            "schemas": sorted(
                name
                for item in schema_items
                if (name := item_name(item, ("name", "schema", "schema_name")))
            ),
            "schema_count": len(schema_items),
            "table_count": len(inventory),
        }

        discovery: dict[str, Any] = {}
        for name, path in (
            ("sources", "/catalog/sources"),
            ("submitters", "/catalog/submitters"),
            ("lineage_runs", "/catalog/lineage/runs?limit=1000"),
            (
                "lineage_row_news_articles_missing_key",
                "/catalog/lineage/row?schema=news&table=articles",
            ),
            (
                "lineage_row_news_articles_valid_key",
                "/catalog/lineage/row?schema=news&table=articles&id=240598138",
            ),
            ("usage", "/usage.md"),
            ("skill", "/skill.md"),
            ("reference", "/reference"),
        ):
            summary, payload = request_json(client, path)
            if name in {"sources", "submitters", "lineage_runs"}:
                summary["payload"] = sanitize(payload)
            discovery[name] = summary
        report["discovery"] = discovery

        mcp_started = time.perf_counter()
        mcp_response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )
        report["mcp_tools_list"] = body_summary(mcp_response)
        report["mcp_tools_list"]["elapsed_seconds"] = time.perf_counter() - mcp_started

        report["retrieve_tests"] = [
            materialize(
                client,
                name="basic_select_jsonl",
                sql="SELECT 1::integer AS ok, CURRENT_TIMESTAMP AS server_time",
            ),
            materialize(
                client,
                name="cte_window_jsonl",
                sql=(
                    "WITH x(n) AS (VALUES (1), (2), (3)) "
                    "SELECT n, SUM(n) OVER (ORDER BY n) AS running_sum FROM x ORDER BY n"
                ),
            ),
            materialize(
                client,
                name="empty_result_jsonl",
                sql="SELECT 1::integer AS ok WHERE FALSE",
            ),
            materialize(
                client,
                name="fifteen_hundred_rows_jsonl",
                sql="SELECT id FROM news.articles ORDER BY id LIMIT 1500",
            ),
            materialize(
                client,
                name="news_articles_information_schema_jsonl",
                sql=(
                    "SELECT column_name, data_type, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'news' AND table_name = 'articles' "
                    "ORDER BY ordinal_position"
                ),
                capture_jsonl_rows=True,
            ),
            materialize(
                client,
                name="news_full_text_search_jsonl",
                sql=(
                    "SELECT COUNT(*)::bigint AS rows "
                    "FROM news.articles "
                    "WHERE search_tsv @@ plainto_tsquery('english', 'clarity act')"
                ),
            ),
            materialize(
                client,
                name="news_bounded_full_text_search_jsonl",
                sql=(
                    "SELECT COUNT(*)::bigint AS rows "
                    "FROM news.articles "
                    "WHERE published_at >= TIMESTAMPTZ '2026-08-08T00:00:00Z' "
                    "AND published_at < TIMESTAMPTZ '2026-08-09T00:00:00Z' "
                    "AND search_tsv @@ plainto_tsquery('english', 'clarity act')"
                ),
            ),
            materialize(
                client,
                name="basic_select_csv",
                sql="SELECT 1::integer AS n UNION ALL SELECT 2::integer ORDER BY n",
                output_format="csv",
            ),
            materialize(
                client,
                name="basic_select_parquet",
                sql="SELECT 1::integer AS n UNION ALL SELECT 2::integer ORDER BY n",
                output_format="parquet",
            ),
            materialize(
                client,
                name="invalid_table_error",
                sql="SELECT * FROM eventx_nonexistent_schema.eventx_nonexistent_table",
            ),
            materialize(
                client,
                name="invalid_output_format",
                sql="SELECT 1::integer AS n",
                output_format="not-a-format",
            ),
        ]

    report["findings"] = summarize_findings(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["findings"], indent=2, sort_keys=True))
    print(f"report={args.output}")


def _html_title(value: str) -> str | None:
    match = re.search(r"<title>(.*?)</title>", value, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def summarize_findings(report: dict[str, Any]) -> dict[str, Any]:
    inventory = report.get("catalog_inventory", [])
    tests = report.get("retrieve_tests", [])
    profile_timeouts = [
        f"{item['schema']}.{item['table']}"
        for item in inventory
        if item.get("profile_request", {}).get("exception") == "ReadTimeout"
    ]
    schema_404s = [
        f"{item['schema']}.{item['table']}"
        for item in inventory
        if item.get("schema_request", {}).get("status_code") == 404
    ]
    passed_formats = []
    for test in tests:
        if test.get("name") == "basic_select_jsonl" and test.get("downloaded_rows") == 1:
            passed_formats.append("jsonl")
        if test.get("name") == "basic_select_csv" and test.get("csv_data_rows") == 2:
            passed_formats.append("csv")
        if test.get("name") == "basic_select_parquet" and test.get("parquet_magic_valid"):
            passed_formats.append("parquet")
    bulk = next(
        (test for test in tests if test.get("name") == "fifteen_hundred_rows_jsonl"),
        {},
    )
    lineage_runs = report.get("discovery", {}).get("lineage_runs", {}).get("json", {})
    mcp_tools = report.get("mcp_tools_list", {}).get("json", {}).get("result", {}).get("tools", [])
    news_catalog = next(
        (
            item
            for item in inventory
            if item.get("schema") == "news" and item.get("table") == "articles"
        ),
        {},
    )
    information_schema_test = next(
        (
            test
            for test in tests
            if test.get("name") == "news_articles_information_schema_jsonl"
        ),
        {},
    )
    actual_news_columns = sorted(
        str(row["column_name"])
        for row in information_schema_test.get("jsonl_rows", [])
        if isinstance(row, dict) and row.get("column_name")
    )
    catalog_news_columns = sorted(str(value) for value in news_catalog.get("columns", []))
    return {
        "studio_requires_authentication": report.get("studio_shell", {}).get(
            "authentication_shell"
        ),
        "catalog_schema_count": report.get("catalog_summary", {}).get("schema_count"),
        "catalog_table_count": report.get("catalog_summary", {}).get("table_count"),
        "catalog_profiles_completed": sum(
            1
            for item in inventory
            if item.get("profile_request", {}).get("status_code") == 200
            and item.get("schema_request", {}).get("status_code") == 200
        ),
        "catalog_profile_timeouts": profile_timeouts,
        "catalog_schema_404s": schema_404s,
        "catalog_metadata_anonymous_status": report.get("unauthenticated_catalog", {}).get(
            "status_code"
        ),
        "retrieve_documented_in_openapi": report.get("openapi", {}).get(
            "retrieve_documented"
        ),
        "openapi_duplicate_operation_ids": report.get("openapi", {}).get(
            "duplicate_operation_ids"
        ),
        "news_articles_catalog_columns": catalog_news_columns,
        "news_articles_actual_columns": actual_news_columns,
        "news_articles_catalog_missing_columns": sorted(
            set(actual_news_columns) - set(catalog_news_columns)
        ),
        "news_articles_catalog_extra_columns": sorted(
            set(catalog_news_columns) - set(actual_news_columns)
        ),
        "working_materialization_formats": passed_formats,
        "retrieve_slow_or_failed_tests": [
            test["name"]
            for test in tests
            if test.get("exception") or test.get("elapsed_seconds", 0) > 30
        ],
        "retrieve_submit_statuses": {
            str(test.get("name")): (test.get("submit") or {}).get("status_code")
            for test in tests
        },
        "lineage_runs_count": len(lineage_runs.get("runs", []))
        if isinstance(lineage_runs, dict)
        else None,
        "lineage_valid_key_status": report.get("discovery", {})
        .get("lineage_row_news_articles_valid_key", {})
        .get("status_code"),
        "lineage_missing_key_status": report.get("discovery", {})
        .get("lineage_row_news_articles_missing_key", {})
        .get("status_code"),
        "mcp_tool_count": len(mcp_tools) if isinstance(mcp_tools, list) else None,
        "bulk_rows_recovered": bulk.get("downloaded_rows"),
        "bulk_receipt_rowcount": (bulk.get("receipt") or {}).get("rowcount"),
        "select_only_tests": all(test.get("select_only") for test in tests),
        "protected_data_touched": False,
    }


if __name__ == "__main__":
    main()
