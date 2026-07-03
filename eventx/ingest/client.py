"""Rate-limited, resumable, idempotent client for the findata API (https://kv.run:5000).

Guardrail A2: 100 req/min + auth on every route means every pull is a multi-hour,
resumable batch job. This client enforces the throttle and the retry/backoff policy;
resumability (checkpointing) is the caller's job via meta.job_checkpoints.

Guardrail A1: do NOT hardcode guessed endpoint paths. Use `get`/`paginate` with paths
confirmed against GET /openapi.json or the catalog tools.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from eventx.settings import ApiSettings

log = logging.getLogger(__name__)

# Retry on transient transport errors and on the status codes we re-raise below.
_RETRYABLE = (httpx.HTTPStatusError, httpx.TransportError)


class FindataClient:
    """Thin wrapper over httpx with a global throttle and retry/backoff.

    Stays under the 100 req/min cap with headroom (default 90 rpm). A single client
    instance owns the throttle clock, so share one instance across a pull job.
    """

    def __init__(
        self,
        settings: ApiSettings | None = None,
        *,
        rpm: int = 90,
        timeout: float = 60.0,
    ) -> None:
        self._settings = settings or ApiSettings.from_env()
        self._min_interval = 60.0 / rpm
        self._last = 0.0
        self._client = httpx.Client(
            base_url=self._settings.base_url,
            headers={"Authorization": f"Bearer {self._settings.token}"},
            timeout=timeout,
        )

    def __enter__(self) -> "FindataClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _throttle(self) -> None:
        dt = time.monotonic() - self._last
        if dt < self._min_interval:
            time.sleep(self._min_interval - dt)
        self._last = time.monotonic()

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        wait=wait_exponential(min=2, max=120),
        stop=stop_after_attempt(6),
        reraise=True,
    )
    def get(self, path: str, **params: Any) -> Any:
        """GET a JSON path. Retries transient errors with exponential backoff.

        429: honor Retry-After, then re-raise to trigger a retry.
        503: Lumid unreachable / fail-closed — re-raise to retry with backoff.
        """
        self._throttle()
        r = self._client.get(path, params=params)
        if r.status_code == 429:
            retry_after = int(r.headers.get("Retry-After", "30"))
            log.warning("429 rate-limited on %s; sleeping %ss", path, retry_after)
            time.sleep(retry_after)
            r.raise_for_status()  # -> HTTPStatusError -> tenacity retry
        if r.status_code == 503:
            log.warning("503 on %s (Lumid unreachable); backing off", path)
            r.raise_for_status()
        r.raise_for_status()
        return r.json()

    def paginate(
        self,
        path: str,
        *,
        limit: int = 1000,
        data_key: str = "data",
        **params: Any,
    ) -> Iterator[dict[str, Any]]:
        """Yield rows across limit/offset pages (limit capped server-side at 1000).

        Handles both bare-list and {"data": [...]} response envelopes. Endpoints with a
        server-side row cap instead of offset paging (e.g. /ohlc) must be paged by time
        range by the caller, not with this helper.
        """
        offset = 0
        while True:
            page = self.get(path, limit=limit, offset=offset, **params)
            rows = page if isinstance(page, list) else page.get(data_key, [])
            if not rows:
                break
            yield from rows
            if len(rows) < limit:
                break
            offset += limit
