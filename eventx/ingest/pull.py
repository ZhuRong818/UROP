"""Resumable, rate-limited pullers for the findata prediction-market data.

Design notes grounded in live probing of https://kv.run:5000:
  * The market universe comes from /api/v1/lqt/* (the liquidity-monitored universe).
    /prediction-markets/markets/search is unreliable (times out / 500s on broad q), so
    it is NOT used for enumeration (guardrail A1: verified, not assumed).
  * Trades/candles are keyed by real market_id (Polymarket condition_id, Kalshi ticker)
    and paged by TIME RANGE (from/to/limit), newest-first — not offset. We page backward
    via the `to` cursor until a page returns fewer than `limit` rows.

Run:
    python -m eventx.ingest.pull universe --venue polymarket
    python -m eventx.ingest.pull universe --venue kalshi
    python -m eventx.ingest.pull trades   --venue polymarket --market <condition_id>
    python -m eventx.ingest.pull candles  --venue polymarket --market <id> --interval 60
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

import yaml

from eventx.ingest.client import FindataClient
from eventx.ingest.sink import JsonlSink
from eventx.settings import REPO_ROOT

log = logging.getLogger("eventx.pull")

CONFIG_PATH = REPO_ROOT / "eventx" / "config" / "eventx.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def pull_universe(client: FindataClient, sink: JsonlSink, venue: str) -> int:
    """Pull the liquidity-monitored market universe + cross-venue matches for a venue."""
    if sink.is_done("universe", venue):
        log.info("universe/%s already done; skipping", venue)
        return 0
    resp = client.get("/api/v1/lqt/markets", venue=venue)
    markets = resp.get("markets", [])
    for m in markets:
        m["venue"] = venue
        m["as_of_ns"] = resp.get("as_of_ns")
    n = sink.write(f"universe_{venue}", markets)

    # Flatten cross-venue matched pairs (feature-only, research_plan §3).
    pairs = [
        {
            "venue_a": venue,
            "venue_a_id": m["market_id"],
            "venue_b": match.get("venue"),
            "venue_b_id": match.get("market_id"),
            "match_kind": match.get("match_kind"),
            "similarity": match.get("similarity"),
        }
        for m in markets
        for match in (m.get("matches") or [])
    ]
    sink.write("matched_pairs", pairs)
    sink.set_checkpoint("universe", venue, status="done", n_markets=n, n_pairs=len(pairs))
    log.info("universe/%s: %d markets, %d matched pairs", venue, n, len(pairs))
    return n


def pull_trades(
    client: FindataClient,
    sink: JsonlSink,
    venue: str,
    market_id: str,
    *,
    page_limit: int = 1000,
    max_pages: int = 10_000,
) -> int:
    """Page a market's trades backward in time until exhausted. Resumable per market."""
    job = f"trades_{venue}"
    if sink.is_done(job, market_id):
        log.info("%s/%s already done; skipping", job, market_id)
        return 0
    cp = sink.get_checkpoint(job, market_id) or {}
    to_cursor: str | None = cp.get("oldest_ts")  # resume from where we stopped
    total = int(cp.get("n_rows", 0))
    ts_key = "ts" if venue == "polymarket" else "created_time"

    for _ in range(max_pages):
        params: dict[str, Any] = {"limit": page_limit}
        if to_cursor:
            params["to"] = to_cursor
        rows = client.get(f"/prediction-markets/trades/{venue}/{market_id}", **params)
        if not rows:
            break
        total += sink.write(job, [{**r, "venue": venue, "market_id": market_id} for r in rows])
        oldest = min(r[ts_key] for r in rows)
        if oldest == to_cursor:  # no progress -> avoid infinite loop
            break
        to_cursor = oldest
        sink.set_checkpoint(job, market_id, oldest_ts=oldest, n_rows=total, status="running")
        if len(rows) < page_limit:
            break

    sink.set_checkpoint(job, market_id, status="done", n_rows=total)
    log.info("%s/%s: %d trades", job, market_id, total)
    return total


def pull_candles(
    client: FindataClient, sink: JsonlSink, venue: str, market_id: str, interval: str
) -> int:
    """Pull candles (recent window) — used only to validate bar reconstruction."""
    rows = client.get(
        f"/prediction-markets/candles/{venue}/{market_id}", interval=interval, limit="100000"
    )
    n = sink.write(
        f"candles_{venue}",
        [{**r, "venue": venue, "market_id": market_id, "interval_min": int(interval)} for r in rows],
    )
    log.info("candles/%s/%s (int=%s): %d bars", venue, market_id, interval, n)
    return n


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    version = cfg["extract"]["version"]

    ap = argparse.ArgumentParser(description="EventX findata pullers")
    ap.add_argument("job", choices=["universe", "trades", "candles"])
    ap.add_argument("--venue", choices=["polymarket", "kalshi"], required=True)
    ap.add_argument("--market", help="market_id (condition_id / ticker) for trades/candles")
    ap.add_argument("--interval", default="60", help="candle interval in minutes")
    args = ap.parse_args()

    sink = JsonlSink(version)
    with FindataClient() as client:
        if args.job == "universe":
            pull_universe(client, sink, args.venue)
        elif args.job == "trades":
            if not args.market:
                ap.error("trades requires --market")
            pull_trades(client, sink, args.venue, args.market)
        elif args.job == "candles":
            if not args.market:
                ap.error("candles requires --market")
            pull_candles(client, sink, args.venue, args.market, args.interval)


if __name__ == "__main__":
    main()
