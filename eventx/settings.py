"""Environment + config loading. Secrets come from the gitignored .env only."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

# Load .env once at import; real values live only in the gitignored file.
load_dotenv(REPO_ROOT / ".env")


def require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(
            f"Missing required environment variable {name!r}. "
            f"Copy .env.example to .env and fill it in."
        )
    return val


@dataclass(frozen=True)
class ApiSettings:
    token: str
    base_url: str

    @classmethod
    def from_env(cls) -> "ApiSettings":
        return cls(
            token=require_env("FINDATA_TOKEN"),
            base_url=os.environ.get("FINDATA_BASE_URL", "https://kv.run:5000"),
        )


@dataclass(frozen=True)
class PgSettings:
    host: str
    port: int
    dbname: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "PgSettings":
        return cls(
            host=os.environ.get("PGHOST", "localhost"),
            port=int(os.environ.get("PGPORT", "5432")),
            dbname=os.environ.get("PGDATABASE", "eventx"),
            user=os.environ.get("PGUSER", "eventx"),
            password=os.environ.get("PGPASSWORD", ""),
        )
