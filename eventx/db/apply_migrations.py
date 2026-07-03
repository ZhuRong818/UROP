"""Apply eventx/db/migrations/*.sql in order against the configured Postgres.

Connection comes from env (PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD via .env).
Idempotent: every migration uses CREATE ... IF NOT EXISTS, so re-running is safe.

Usage:
    python -m eventx.db.apply_migrations           # apply all
    python -m eventx.db.apply_migrations --dry-run # list files only
"""

from __future__ import annotations

import argparse
from pathlib import Path

import psycopg

from eventx.settings import PgSettings

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = migration_files()
    if args.dry_run:
        for f in files:
            print("would apply:", f.name)
        return

    pg = PgSettings.from_env()
    conninfo = (
        f"host={pg.host} port={pg.port} dbname={pg.dbname} "
        f"user={pg.user} password={pg.password}"
    )
    with psycopg.connect(conninfo) as conn:
        for f in files:
            sql = f.read_text()
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            print("applied:", f.name)


if __name__ == "__main__":
    main()
