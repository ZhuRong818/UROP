"""Executable smoke test for the PORTEND DuckDB schema and manifest registrar."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import duckdb

from build_catalog import DATASET_VIEWS, build_catalog


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_sample_prices(root: Path) -> tuple[Path, dict[str, object]]:
    relative = Path(
        "warehouse/market_data/prices/venue=polymarket/date=2026-09-06/part-000.parquet"
    )
    parquet_path = root / relative
    parquet_path.parent.mkdir(parents=True)
    connection = duckdb.connect()
    try:
        connection.execute(
            f"""
            COPY (
                SELECT
                    'price-1'::VARCHAR AS price_id,
                    'token-1'::VARCHAR AS token_id,
                    'market-1'::VARCHAR AS market_id,
                    TIMESTAMPTZ '2026-09-06 00:00:00+00' AS exchange_ts,
                    TIMESTAMPTZ '2026-09-06 00:00:00.100+00' AS received_ts,
                    TIMESTAMPTZ '2026-09-06 00:00:00.200+00' AS ingest_ts,
                    TIMESTAMPTZ '2026-09-06 00:00:00.200+00' AS availability_ts,
                    'last_trade'::VARCHAR AS price_type,
                    0.61::DECIMAL(38, 18) AS price,
                    'run-1'::VARCHAR AS source_run_id,
                    repeat('a', 64)::VARCHAR AS raw_payload_hash,
                    'prices-test-v1'::VARCHAR AS dataset_version,
                    '1.0.0'::VARCHAR AS schema_version
            ) TO '{str(parquet_path).replace("'", "''")}'
            (FORMAT parquet, COMPRESSION zstd)
            """
        )
    finally:
        connection.close()

    item = {
        "relative_path": str(relative),
        "file_sha256": file_sha256(parquet_path),
        "byte_count": parquet_path.stat().st_size,
        "row_count": 1,
        "row_group_count": 1,
        "min_timestamp": "2026-09-06T00:00:00Z",
        "max_timestamp": "2026-09-06T00:00:00Z",
        "partition_values": {"venue": "polymarket", "date": "2026-09-06"},
    }
    return parquet_path, item


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="portend-schema-") as temporary:
        root = Path(temporary)
        _, file_item = write_sample_prices(root)
        manifest = {
            "dataset_name": "market_data.prices",
            "dataset_version": "prices-test-v1",
            "schema_version": "1.0.0",
            "status": "published",
            "row_count": 1,
            "min_timestamp": "2026-09-06T00:00:00Z",
            "max_timestamp": "2026-09-06T00:00:00Z",
            "code_commit": "0000000-test",
            "config_hash": "0" * 64,
            "created_at": "2026-09-06T00:05:00Z",
            "published_at": "2026-09-06T00:06:00Z",
            "qa_status": "pass",
            "source_run_ids": ["run-1"],
            "files": [file_item],
            "upstream_manifests": [],
        }
        manifest_path = root / "manifests/dataset=market_data.prices/version=prices-test-v1/manifest.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

        database = root / "portend.duckdb"
        build_catalog(database, root, [manifest_path])

        changed_manifest = dict(manifest)
        changed_manifest["config_hash"] = "1" * 64
        manifest_path.write_text(json.dumps(changed_manifest, indent=2) + "\n")
        try:
            build_catalog(database, root, [manifest_path])
        except ValueError as exc:
            assert "immutable release changed" in str(exc)
        else:
            raise AssertionError("a published dataset version accepted a changed manifest")
        finally:
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

        # Applying the schema a second time must be safe and preserve registered views.
        connection = duckdb.connect(str(database))
        try:
            schema_sql = Path(__file__).with_name("schema.sql").read_text()
            connection.execute(schema_sql)
            schemas = {
                row[0]
                for row in connection.execute(
                    "SELECT schema_name FROM information_schema.schemata"
                ).fetchall()
            }
            required_schemas = {
                "meta",
                "contract",
                "core",
                "market_data",
                "semantics",
                "benchmark",
                "simulation",
                "qa",
            }
            assert required_schemas <= schemas
            view_count = connection.execute(
                """
                SELECT count(*)
                FROM information_schema.views
                WHERE table_schema IN ('core', 'market_data', 'semantics', 'benchmark',
                                       'simulation', 'qa')
                """
            ).fetchone()[0]
            assert view_count == len(DATASET_VIEWS), (view_count, len(DATASET_VIEWS))
            row = connection.execute(
                """
                SELECT venue, date, token_id, price, dataset_version
                FROM market_data.prices
                """
            ).fetchone()
            assert row is not None, "schema reapplication must not reset a registered view"
        finally:
            connection.close()

        # Rebuilding from the pinned manifest must restore the external Parquet view.
        build_catalog(database, root, [manifest_path])
        connection = duckdb.connect(str(database), read_only=True)
        try:
            row = connection.execute(
                "SELECT venue, date, token_id, price, dataset_version FROM market_data.prices"
            ).fetchone()
            assert row[0] == "polymarket"
            assert str(row[1]) == "2026-09-06"
            assert row[2] == "token-1"
            assert str(row[3]) == "0.610000000000000000"
            assert row[4] == "prices-test-v1"
            active = connection.execute(
                "SELECT dataset_version FROM meta.active_releases WHERE dataset_name = ?",
                ["market_data.prices"],
            ).fetchone()
            assert active == ("prices-test-v1",)
        finally:
            connection.close()

    print(f"PORTEND schema smoke test passed ({len(DATASET_VIEWS)} Parquet contracts).")


if __name__ == "__main__":
    main()
