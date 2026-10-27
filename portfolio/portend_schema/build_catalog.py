"""Build a PORTEND DuckDB catalog from the schema and pinned release manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import duckdb


DATASET_VIEWS = {
    "core.markets": "contract.markets",
    "core.outcomes": "contract.outcomes",
    "core.fees": "contract.fees",
    "core.trading_rules": "contract.trading_rules",
    "core.settlements": "contract.settlements",
    "market_data.prices": "contract.prices",
    "market_data.trades": "contract.trades",
    "market_data.orderbook_updates": "contract.orderbook_updates",
    "market_data.orderbook_snapshots": "contract.orderbook_snapshots",
    "semantics.event_families": "contract.event_families",
    "semantics.event_family_members": "contract.event_family_members",
    "semantics.relations": "contract.relations",
    "semantics.relation_participants": "contract.relation_participants",
    "semantics.relation_audits": "contract.relation_audits",
    "semantics.constraints": "contract.constraints",
    "semantics.constraint_terms": "contract.constraint_terms",
    "benchmark.decision_times": "contract.decision_times",
    "benchmark.beliefs": "contract.beliefs",
    "benchmark.joint_distributions": "contract.joint_distributions",
    "benchmark.joint_distribution_members": "contract.joint_distribution_members",
    "benchmark.joint_samples": "contract.joint_samples",
    "benchmark.episodes": "contract.episodes",
    "benchmark.episode_families": "contract.episode_families",
    "benchmark.splits": "contract.splits",
    "benchmark.split_memberships": "contract.split_memberships",
    "benchmark.scenarios": "contract.scenarios",
    "benchmark.stress_events": "contract.stress_events",
    "benchmark.oracle_variants": "contract.oracle_variants",
    "simulation.experiment_runs": "contract.experiment_runs",
    "simulation.fills": "contract.fills",
    "simulation.portfolio_states": "contract.portfolio_states",
    "simulation.portfolio_positions": "contract.portfolio_positions",
    "simulation.results": "contract.results",
    "simulation.simulator_validation": "contract.simulator_validation",
    "qa.replay_events": "contract.replay_events",
    "qa.book_validity": "contract.book_validity",
    "qa.completeness": "contract.completeness",
    "qa.schema_checks": "contract.schema_checks",
    "qa.relation_checks": "contract.relation_checks",
    "qa.dataset_statistics": "contract.dataset_statistics",
}

REQUIRED_MANIFEST_FIELDS = {
    "dataset_name",
    "dataset_version",
    "schema_version",
    "status",
    "row_count",
    "min_timestamp",
    "max_timestamp",
    "code_commit",
    "config_hash",
    "created_at",
    "published_at",
    "qa_status",
    "source_run_ids",
    "files",
    "upstream_manifests",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def resolve_data_file(data_root: Path, relative_path: str) -> Path:
    root = data_root.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"dataset file escapes data root: {relative_path}") from exc
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def load_manifest(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    manifest = json.loads(raw)
    missing = REQUIRED_MANIFEST_FIELDS - manifest.keys()
    if missing:
        raise ValueError(f"{path}: missing manifest fields {sorted(missing)}")
    if manifest["dataset_name"] not in DATASET_VIEWS:
        raise ValueError(f"{path}: unknown dataset_name {manifest['dataset_name']!r}")
    if manifest["status"] != "published":
        raise ValueError(f"{path}: only published releases may enter a catalog")
    if manifest["qa_status"] != "pass":
        raise ValueError(f"{path}: qa_status must be 'pass'")
    if not manifest["files"]:
        raise ValueError(f"{path}: files must not be empty")
    return manifest, hashlib.sha256(raw).hexdigest()


def contract_columns(connection: duckdb.DuckDBPyConnection, table: str) -> list[tuple[str, str]]:
    rows = connection.execute(f"DESCRIBE {table}").fetchall()
    return [(row[0], row[1]) for row in rows]


def register_release(
    connection: duckdb.DuckDBPyConnection,
    manifest_path: Path,
    data_root: Path,
    verify_hashes: bool,
) -> str:
    manifest, manifest_hash = load_manifest(manifest_path)
    dataset_name = manifest["dataset_name"]
    contract_table = DATASET_VIEWS[dataset_name]
    try:
        manifest_relative_path = str(manifest_path.resolve().relative_to(data_root.resolve()))
    except ValueError as exc:
        raise ValueError(f"manifest escapes data root: {manifest_path}") from exc
    existing = connection.execute(
        """
        SELECT manifest_sha256
        FROM meta.dataset_releases
        WHERE dataset_name = ? AND dataset_version = ?
        """,
        [dataset_name, manifest["dataset_version"]],
    ).fetchone()
    if existing is not None and existing[0] != manifest_hash:
        raise ValueError(
            f"immutable release changed: {dataset_name}@{manifest['dataset_version']}"
        )

    paths: list[Path] = []
    file_rows = 0
    for item in manifest["files"]:
        for field in ("relative_path", "file_sha256", "byte_count", "row_count"):
            if field not in item:
                raise ValueError(f"{manifest_path}: file entry missing {field}")
        path = resolve_data_file(data_root, item["relative_path"])
        if verify_hashes and sha256_file(path) != item["file_sha256"]:
            raise ValueError(f"checksum mismatch: {path}")
        if path.stat().st_size != item["byte_count"]:
            raise ValueError(f"byte-count mismatch: {path}")
        file_rows += int(item["row_count"])
        paths.append(path)

    if file_rows != int(manifest["row_count"]):
        raise ValueError(
            f"{manifest_path}: file row total {file_rows} != manifest row_count "
            f"{manifest['row_count']}"
        )

    path_list = "[" + ", ".join(sql_string(str(path)) for path in paths) + "]"
    parquet_sql = f"read_parquet({path_list}, hive_partitioning = true, union_by_name = false)"
    available = {
        row[0]: row[1]
        for row in connection.execute(f"DESCRIBE SELECT * FROM {parquet_sql}").fetchall()
    }
    expected = contract_columns(connection, contract_table)
    missing_columns = [name for name, _ in expected if name not in available]
    if missing_columns:
        raise ValueError(f"{manifest_path}: missing canonical columns {missing_columns}")

    select_list = ",\n    ".join(
        f'CAST("{name}" AS {column_type}) AS "{name}"' for name, column_type in expected
    )
    connection.execute(
        f"CREATE OR REPLACE VIEW {dataset_name} AS\n"
        f"SELECT\n    {select_list}\nFROM {parquet_sql}"
    )

    connection.execute(
        """
        INSERT INTO meta.dataset_releases VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        ON CONFLICT (dataset_name, dataset_version) DO UPDATE SET
            schema_version = excluded.schema_version,
            status = excluded.status,
            manifest_relative_path = excluded.manifest_relative_path,
            manifest_sha256 = excluded.manifest_sha256,
            row_count = excluded.row_count,
            min_timestamp = excluded.min_timestamp,
            max_timestamp = excluded.max_timestamp,
            code_commit = excluded.code_commit,
            config_hash = excluded.config_hash,
            qa_status = excluded.qa_status,
            created_at = excluded.created_at,
            published_at = excluded.published_at
        """,
        [
            dataset_name,
            manifest["dataset_version"],
            manifest["schema_version"],
            manifest["status"],
            manifest_relative_path,
            manifest_hash,
            manifest["row_count"],
            manifest.get("min_timestamp"),
            manifest.get("max_timestamp"),
            manifest["code_commit"],
            manifest["config_hash"],
            manifest["qa_status"],
            manifest["created_at"],
            manifest.get("published_at"),
        ],
    )
    for item in manifest["files"]:
        connection.execute(
            """
            INSERT OR REPLACE INTO meta.dataset_files VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            [
                dataset_name,
                manifest["dataset_version"],
                item["relative_path"],
                item["file_sha256"],
                item["byte_count"],
                item["row_count"],
                item.get("row_group_count"),
                item.get("min_timestamp"),
                item.get("max_timestamp"),
                json.dumps(item.get("partition_values")),
            ],
        )
    for dependency in manifest.get("upstream_manifests", []):
        connection.execute(
            "INSERT OR REPLACE INTO meta.dataset_dependencies VALUES (?, ?, ?, ?, ?)",
            [
                dataset_name,
                manifest["dataset_version"],
                dependency["dataset_name"],
                dependency["dataset_version"],
                dependency["manifest_sha256"],
            ],
        )
    connection.execute(
        "DELETE FROM meta.dataset_source_runs WHERE dataset_name = ? AND dataset_version = ?",
        [dataset_name, manifest["dataset_version"]],
    )
    for source_run_id in manifest["source_run_ids"]:
        connection.execute(
            "INSERT INTO meta.dataset_source_runs VALUES (?, ?, ?)",
            [dataset_name, manifest["dataset_version"], source_run_id],
        )
    connection.execute(
        "INSERT OR REPLACE INTO meta.active_releases VALUES (?, ?, ?, current_timestamp)",
        [dataset_name, manifest["dataset_version"], manifest_hash],
    )
    return manifest_hash


def build_catalog(
    database: Path,
    data_root: Path,
    manifests: list[Path],
    verify_hashes: bool = True,
) -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database))
    try:
        connection.execute(schema_path.read_text())
        selected_names = [load_manifest(path)[0]["dataset_name"] for path in manifests]
        if len(selected_names) != len(set(selected_names)):
            raise ValueError("provide at most one manifest per dataset_name")

        connection.execute("BEGIN TRANSACTION")
        try:
            for dataset_name, contract_table in DATASET_VIEWS.items():
                if dataset_name not in selected_names:
                    connection.execute(
                        f"CREATE OR REPLACE VIEW {dataset_name} AS "
                        f"SELECT * FROM {contract_table} WHERE false"
                    )
                    connection.execute(
                        "DELETE FROM meta.active_releases WHERE dataset_name = ?",
                        [dataset_name],
                    )

            manifest_hashes = [
                register_release(connection, path, data_root, verify_hashes)
                for path in manifests
            ]
            manifest_set_hash = hashlib.sha256(
                "\n".join(sorted(manifest_hashes)).encode()
            ).hexdigest()
            build_id = hashlib.sha256(
                f"{database.resolve()}:{manifest_set_hash}".encode()
            ).hexdigest()[:24]
            connection.execute(
                """
                INSERT OR REPLACE INTO meta.catalog_builds
                (catalog_build_id, database_path, manifest_set_sha256, code_commit,
                 started_at, completed_at, status, error_summary)
                VALUES (?, ?, ?, NULL, current_timestamp, current_timestamp, 'complete', NULL)
                """,
                [build_id, str(database.resolve()), manifest_set_hash],
            )
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, action="append", default=[])
    parser.add_argument(
        "--skip-file-hashes",
        action="store_true",
        help="Development-only: skip SHA-256 verification of Parquet files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_catalog(
        database=args.database,
        data_root=args.data_root,
        manifests=args.manifest,
        verify_hashes=not args.skip_file_hashes,
    )


if __name__ == "__main__":
    main()
