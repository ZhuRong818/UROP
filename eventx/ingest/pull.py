"""Resumable, rate-limited pullers for the findata prediction-market data.

Design notes grounded in live probing of https://lum.id/findata (formerly https://kv.run:5000):
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
import json
import logging
from pathlib import Path
from typing import Any

import yaml

from eventx.ingest.client import FindataClient
from eventx.ingest.sink import JsonlSink
from eventx.settings import REPO_ROOT

log = logging.getLogger("eventx.pull")

CONFIG_PATH = REPO_ROOT / "eventx" / "config" / "eventx.yaml"

TOY_NEWS_QUERIES = {
    "Will United Russia (ER) gain the most seats in the next Russian parliamentary election?": [
        "United Russia election",
        "Russian parliamentary election",
    ],
    "Will China invade Taiwan by end of 2026?": [
        "China Taiwan invasion",
        "Taiwan military blockade",
    ],
    "Strait of Hormuz traffic returns to normal by December 31?": [
        "Strait of Hormuz",
        "Hormuz shipping traffic",
    ],
    "Will Benjamin Netanyahu be the next Prime Minister of Israel?": [
        "Benjamin Netanyahu election",
        "Netanyahu prime minister",
    ],
    "Will Luiz Inácio Lula da Silva win the 2026 Brazilian presidential election?": [
        "Lula 2026 election",
        "Brazil presidential election",
    ],
    "Will Gavin Newsom win the 2028 Democratic presidential nomination?": [
        "Gavin Newsom 2028",
        "Newsom presidential nomination",
    ],
    "Will Naftali Bennett be the next Prime Minister of Israel?": [
        "Naftali Bennett prime minister",
        "Bennett Israel election",
    ],
    "Will Mojtaba Khamenei be head of state in Iran end of 2026?": [
        "Mojtaba Khamenei Iran",
    ],
    "Will Russia capture all of Stepnohirsk by September 30, 2026?": [
        "Stepnohirsk Russia",
    ],
    "Cuban regime falls in 2026?": [
        "Cuba regime",
        "Cuban government collapse",
    ],
    "Will JD Vance win the 2028 US Presidential Election?": [
        "JD Vance 2028",
        "Vance presidential election",
    ],
    "Will Andy Burnham be the next Prime Minister of the United Kingdom in 2026?": [
        "Andy Burnham prime minister",
    ],
    "Will Karen Bass win the 2026 Los Angeles mayoral election?": [
        "Karen Bass mayoral election",
        "Los Angeles mayor election",
    ],
    "Will Marco Rubio win the 2028 Republican presidential nomination?": [
        "Marco Rubio 2028",
        "Rubio presidential nomination",
    ],
    "Will Xavier Becerra win the California Governor Election in 2026?": [
        "Xavier Becerra governor",
        "California governor election",
    ],
    "Hantavirus pandemic in 2026?": [
        "Hantavirus outbreak",
        "Hantavirus cases",
    ],
    "Mojtaba Khamenei seen in public by July 31?": [
        "Mojtaba Khamenei public appearance",
        "Mojtaba Khamenei seen",
    ],
    "New Rihanna Album before GTA VI?": [
        "Rihanna album",
        "Rihanna GTA VI",
    ],
    "Israel withdraws from Lebanon by July 31, 2026?": [
        "Israel Lebanon withdrawal",
        "Israeli troops Lebanon",
    ],
    "Will J.D. Vance win the 2028 Republican presidential nomination?": [
        "JD Vance 2028",
        "Vance Republican nomination",
    ],
}


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def pull_universe(client: FindataClient, sink: JsonlSink, venue: str) -> int:
    """Pull the complete reachable market roster + instruments + cross-venue matches.

    Three views, none a superset of the others (markets/search is broken; events carry
    no market_id):
      * `/api/v1/lqt/markets` -> ~2961 ACTIVE markets, one row per market_id, carries
        `matches` (cross-venue matched pairs, research §3).
      * `/api/v1/lqt/universe?include_inactive=1` -> the FULL roster incl. resolved
        markets (~175k distinct, ~350k instrument rows: ~2/market Yes/No), carries
        `instrument_id` (needed for L2/orderbook, guardrail C9). This is the enumeration
        master for the historical spine — active-only lists miss ~172k resolved markets.
    universe_{venue}     <- active monitored roster + matches
    instruments_{venue}  <- full instrument-level roster (active + resolved)
    """
    if sink.is_done("universe", venue):
        log.info("universe/%s already done; skipping", venue)
        return 0
    mkt = client.get("/api/v1/lqt/markets", venue=venue)
    markets = mkt.get("markets", [])
    for m in markets:
        m["venue"] = venue
        m["as_of_ns"] = mkt.get("as_of_ns")
    n = sink.write(f"universe_{venue}", markets)

    inst_resp = client.get("/api/v1/lqt/universe", venue=venue, include_inactive=1)
    instruments = inst_resp.get("markets", [])
    for r in instruments:
        r["as_of_ns"] = inst_resp.get("as_of_ns")
    n_inst = sink.write(f"instruments_{venue}", instruments)

    # Cross-venue matched pairs (feature-only, research_plan §3).
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
    sink.set_checkpoint(
        "universe", venue, status="done", n_markets=n, n_instruments=n_inst, n_pairs=len(pairs)
    )
    log.info(
        "universe/%s: %d markets, %d instruments, %d matched pairs", venue, n, n_inst, len(pairs)
    )
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
    client: FindataClient,
    sink: JsonlSink,
    venue: str,
    market_id: str,
    interval: str,
    *,
    floor_ts: str,
    page_limit: int = 5000,
    max_pages: int = 5_000,
) -> int:
    """Page a market's candles backward to `floor_ts`, resumable per (market, interval).

    The endpoint caps a single response at ~5000 bars, so we walk the `to` cursor backward
    with `from` pinned at the venue floor until a short page (reached the start) or no
    progress. `from`/`to` require RFC3339 (bare dates / epoch 400). Boundary bar may repeat
    across pages — raw is frozen and deduped in curation (guardrail A3).
    """
    job = f"candles_{venue}_{interval}"
    if sink.is_done(job, market_id):
        log.info("%s/%s already done; skipping", job, market_id)
        return 0
    cp = sink.get_checkpoint(job, market_id) or {}
    to_cursor: str | None = cp.get("oldest_bucket")
    total = int(cp.get("n_bars", 0))

    for _ in range(max_pages):
        params: dict[str, Any] = {"interval": interval, "from": floor_ts, "limit": page_limit}
        if to_cursor:
            params["to"] = to_cursor
        rows = client.get(f"/prediction-markets/candles/{venue}/{market_id}", **params)
        if not rows:
            break
        total += sink.write(
            job,
            [{**r, "venue": venue, "market_id": market_id, "interval_min": int(interval)} for r in rows],
        )
        oldest = min(r["bucket_ts"] for r in rows)
        if oldest == to_cursor:  # no progress -> avoid infinite loop
            break
        to_cursor = oldest
        sink.set_checkpoint(job, market_id, oldest_bucket=oldest, n_bars=total, status="running")
        if len(rows) < page_limit:  # reached the market's earliest bar for this interval
            break

    sink.set_checkpoint(job, market_id, status="done", n_bars=total)
    log.info("%s/%s: %d bars (oldest=%s)", job, market_id, total, to_cursor)
    return total


def roster_market_ids(sink: JsonlSink, venue: str) -> list[str]:
    """Distinct market_ids for candle enumeration, newest roster file first.

    Prefers the on-disk instrument roster (`instruments_{venue}.jsonl`), which was captured
    while `/api/v1/lqt/universe?include_inactive=1` still returned resolved markets — it is
    the ONLY surviving enumeration of the ~172k resolved markets now that the flag regressed
    to active-only (findata bug #5). Falls back to `universe_{venue}.jsonl`, then to [] so the
    caller can hit the live endpoint. Order is preserved (dict.fromkeys) for stable resume.
    """
    for name in (f"instruments_{venue}", f"universe_{venue}"):
        path = sink.raw_dir / f"{name}.jsonl"
        if not path.exists():
            continue
        with path.open() as f:
            ids = list(
                dict.fromkeys(
                    json.loads(line)["market_id"] for line in f if line.strip()
                )
            )
        if ids:
            log.info("candles-all/%s: %d distinct market_ids from %s", venue, len(ids), name)
            return ids
    return []


def normalize_market_outcomes(venue: str, detail: dict[str, Any]) -> list[dict[str, Any]]:
    """Turn a market-detail response into explicit, outcome-level rows.

    The raw response is retained separately.  These compact rows make the v1 binary
    market filter and canonical-YES selection auditable without reparsing provider
    payloads downstream.
    """
    if venue == "polymarket":
        market_id = detail.get("condition_id") or detail.get("market_id")
        outcomes = detail.get("outcomes") or []
        token_ids = detail.get("clob_token_ids") or []
        prices = detail.get("outcome_prices") or []
        is_binary = len(outcomes) == 2
        return [
            {
                "venue": venue,
                "market_id": market_id,
                "outcome_id": token_ids[i] if i < len(token_ids) else None,
                "outcome_name": str(outcome),
                "outcome_price": prices[i] if i < len(prices) else None,
                "canonical_side": is_binary and str(outcome).strip().lower() == "yes",
                "is_binary": is_binary,
                "question": detail.get("question"),
                "scheduled_close_ts": detail.get("end_date"),
                "resolution_ts": detail.get("closed_time"),
                "status": "closed" if detail.get("closed") else "active" if detail.get("active") else None,
            }
            for i, outcome in enumerate(outcomes)
        ]

    # Kalshi's detail endpoint exposes a binary YES/NO market but no token identifier.
    return [
        {
            "venue": venue,
            "market_id": detail.get("ticker"),
            "outcome_id": None,
            "outcome_name": "YES",
            "outcome_price": detail.get("last_price"),
            "canonical_side": True,
            "is_binary": True,
            "question": detail.get("title"),
            "scheduled_close_ts": detail.get("close_time"),
            "resolution_ts": None,
            "status": detail.get("status"),
        }
    ]


def pull_market_detail(
    client: FindataClient, sink: JsonlSink, venue: str, market_id: str
) -> int:
    """Fetch one market's raw metadata and normalized outcome rows, resumably."""
    job = f"market_details_{venue}"
    if sink.is_done(job, market_id):
        return 0
    detail = client.get(f"/prediction-markets/markets/{venue}/{market_id}")
    if not isinstance(detail, dict):
        raise TypeError(f"Unexpected market detail response for {venue}/{market_id}: {type(detail).__name__}")
    detail = {**detail, "venue": venue, "market_id": market_id}
    outcomes = normalize_market_outcomes(venue, detail)
    sink.write(f"market_details_{venue}", [detail])
    sink.write(f"market_outcomes_{venue}", outcomes)
    sink.set_checkpoint(job, market_id, status="done", n_outcomes=len(outcomes))
    log.info("%s/%s: %d outcomes", job, market_id, len(outcomes))
    return len(outcomes)


def pull_all_market_details(client: FindataClient, sink: JsonlSink, venue: str) -> int:
    """Fetch detail/outcome records for the complete on-disk market roster."""
    market_ids = roster_market_ids(sink, venue)
    if not market_ids:
        raise RuntimeError(f"No market roster found for {venue}; run universe first")
    log.info("market-details-all/%s: %d markets", venue, len(market_ids))
    total = 0
    errors = 0
    for i, market_id in enumerate(market_ids, 1):
        try:
            total += pull_market_detail(client, sink, venue, market_id)
        except Exception as exc:
            errors += 1
            log.warning("market-details-all/%s: skip %s after %s: %s", venue, market_id, type(exc).__name__, exc)
        if i % 50 == 0:
            log.info("market-details-all/%s: %d/%d markets, %d outcomes, %d errors", venue, i, len(market_ids), total, errors)
    sink.flush()
    log.info("market-details-all/%s: done pass, %d outcomes, %d errors", venue, total, errors)
    return total


def pull_all_trades(client: FindataClient, sink: JsonlSink, venue: str) -> int:
    """Backfill all retained trades for every market in the frozen roster.

    The endpoint returns token/outcome IDs with each trade, so a single request stream
    per market preserves outcome-level records without double-counting binary sides.
    """
    market_ids = roster_market_ids(sink, venue)
    if not market_ids:
        raise RuntimeError(f"No market roster found for {venue}; run universe first")
    log.info("trades-all/%s: %d markets", venue, len(market_ids))
    total = 0
    errors = 0
    for i, market_id in enumerate(market_ids, 1):
        try:
            total += pull_trades(client, sink, venue, market_id)
        except Exception as exc:
            errors += 1
            log.warning("trades-all/%s: skip %s after %s: %s", venue, market_id, type(exc).__name__, exc)
        if i % 50 == 0:
            log.info("trades-all/%s: %d/%d markets, %d trades, %d errors", venue, i, len(market_ids), total, errors)
    sink.flush()
    log.info("trades-all/%s: done pass, %d trades, %d errors", venue, total, errors)
    return total


def pull_all_candles(
    client: FindataClient, sink: JsonlSink, cfg: dict[str, Any], venue: str
) -> int:
    """Driver: pull candles for every distinct market at each configured interval.

    Enumerates from the on-disk roster (see `roster_market_ids` — includes resolved markets
    that the live `include_inactive` flag no longer returns), falling back to the live
    `/api/v1/lqt/markets` active set only if no roster is on disk. Pulls each interval per
    market resumably; a killed run resumes from per-market checkpoints.
    """
    cc = cfg["candles"]
    intervals = [str(i) for i in cc["intervals_min"]]
    floor = cc["floor"][venue]
    page_limit = int(cc.get("page_limit", 5000))

    market_ids = roster_market_ids(sink, venue)
    if not market_ids:
        resp = client.get("/api/v1/lqt/markets", venue=venue)
        market_ids = list(dict.fromkeys(m["market_id"] for m in resp.get("markets", [])))
        log.info("candles-all/%s: %d markets from live lqt/markets (no disk roster)", venue, len(market_ids))
    log.info("candles-all/%s: %d markets x %d intervals", venue, len(market_ids), len(intervals))

    total = 0
    errors = 0
    for i, mid in enumerate(market_ids, 1):
        for interval in intervals:
            try:
                total += pull_candles(
                    client, sink, venue, mid, interval, floor_ts=floor, page_limit=page_limit
                )
            except Exception as exc:
                # One market's failure must not abort a 175k-market batch. Observed 500s here
                # are mostly transient, so we DON'T persist an "error" marker: the market stays
                # unsettled and a later resume retries it. Re-run the job until a pass reports 0
                # errors. Already-written raw rows stay frozen and are deduped in curation (A3).
                errors += 1
                log.warning("candles-all/%s: skip %s iv=%s after %s: %s",
                            venue, mid, interval, type(exc).__name__, exc)
        if i % 50 == 0:
            log.info("candles-all/%s: %d/%d markets, %d bars, %d errors",
                     venue, i, len(market_ids), total, errors)
    sink.flush()
    log.info("candles-all/%s: done pass, %d bars, %d errors (re-run to retry unsettled)",
             venue, total, errors)
    return total


def pull_kol_roster(client: FindataClient, sink: JsonlSink) -> int:
    """Pull the KOL roster (handle list). Single call — the endpoint returns the full
    roster (~3,700 handles) in one response; no pagination support. Idempotent."""
    if sink.is_done("kol_roster", "all"):
        log.info("kol_roster already done; skipping")
        path = sink.raw_dir / "kol_roster.jsonl"
        return sum(1 for _ in path.open("rb")) if path.exists() else 0

    # Clear any partial file from a previous killed run.
    roster_path = sink.raw_dir / "kol_roster.jsonl"
    if roster_path.exists():
        roster_path.unlink()

    rows = client.get("/kols")
    batch: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, str):
            batch.append({"handle": r})
        else:
            batch.append(r)
    n = sink.write("kol_roster", batch)
    sink.set_checkpoint("kol_roster", "all", status="done", n_handles=n)
    log.info("kol_roster: %d handles", n)
    return n


def pull_kol_tweets(
    client: FindataClient,
    sink: JsonlSink,
    handle: str,
    *,
    since: str,
    page_limit: int = 1000,
    max_pages: int = 1_000,
) -> int:
    """Pull a single KOL's tweet history since `since`, resumable per handle."""
    job = "kol_tweets"
    if sink.is_done(job, handle):
        return 0
    cp = sink.get_checkpoint(job, handle) or {}
    offset = int(cp.get("offset", 0))
    total = int(cp.get("n_tweets", 0))

    for _ in range(max_pages):
        rows = client.get(
            f"/kols/{handle}/tweets/history",
            since=since,
            limit=page_limit,
            offset=offset,
        )
        if not rows:
            break
        n = sink.write(job, [{**r, "_kol_handle": handle} for r in rows])
        total += n
        offset += n
        sink.set_checkpoint(job, handle, offset=offset, n_tweets=total, status="running")
        if n < page_limit:
            break

    sink.set_checkpoint(job, handle, status="done", n_tweets=total)
    log.info("kol_tweets/%s: %d tweets", handle, total)
    return total


def pull_all_kol_tweets(
    client: FindataClient, sink: JsonlSink, cfg: dict[str, Any]
) -> int:
    """Driver: pull tweet history for every handle in the roster since the window start."""
    since = cfg["window"]["start"]
    # Read roster from disk — must already be pulled.
    roster_path = sink.raw_dir / "kol_roster.jsonl"
    if not roster_path.exists():
        log.error("kol_roster.jsonl not found — run 'kol-roster' job first")
        return 0

    handles: list[str] = []
    with roster_path.open() as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            handles.append(r["handle"] if isinstance(r, dict) else r)

    handles = list(dict.fromkeys(handles))  # dedup, preserve order
    log.info("kol-tweets-all: %d handles", len(handles))

    total = 0
    errors = 0
    for i, handle in enumerate(handles, 1):
        try:
            total += pull_kol_tweets(client, sink, handle, since=since)
        except Exception as exc:
            errors += 1
            log.warning("kol-tweets-all: skip %s after %s: %s", handle, type(exc).__name__, exc)
        if i % 100 == 0:
            log.info("kol-tweets-all: %d/%d handles, %d tweets, %d errors",
                     i, len(handles), total, errors)
    sink.flush()
    log.info("kol-tweets-all: done pass, %d tweets, %d errors (re-run to retry unsettled)",
             total, errors)
    return total


def response_rows(response: Any) -> list[dict[str, Any]]:
    """Normalize list/envelope response variants used by read-only data routes."""
    if isinstance(response, list):
        return [row for row in response if isinstance(row, dict)]
    if isinstance(response, dict):
        for key in ("articles", "data", "results", "news"):
            rows = response.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def pull_toy_news(
    client: FindataClient,
    sink: JsonlSink,
    cfg: dict[str, Any],
    *,
    limit: int = 1000,
) -> int:
    """Fetch a fixed, auditable search candidate pool for the selected toy markets."""
    markets_path = REPO_ROOT / "data" / cfg["extract"]["version"] / "toy" / "selected_markets.jsonl"
    if not markets_path.exists():
        raise RuntimeError(f"Selected toy markets not found: {markets_path}")
    markets = [json.loads(line) for line in markets_path.open() if line.strip()]
    missing = [
        str(market["question"])
        for market in markets
        if str(market["question"]) not in TOY_NEWS_QUERIES
    ]
    if missing:
        raise RuntimeError("Missing fixed news queries for: " + "; ".join(missing))

    total = 0
    cap_hits = 0
    query_count = 0
    for market in markets:
        question = str(market["question"])
        for query in TOY_NEWS_QUERIES[question]:
            checkpoint_key = f"{market['market_id']}:{query}"
            if sink.is_done("news_toy_search", checkpoint_key):
                continue
            response = client.get(
                "/news/search",
                q=query,
                since=cfg["window"]["start"],
                limit=limit,
            )
            rows = response_rows(response)
            enriched = [
                {
                    **row,
                    "_search_query": query,
                    "_search_market_id": market["market_id"],
                    "_search_outcome_id": market["outcome_id"],
                    "_search_question": question,
                }
                for row in rows
            ]
            written = sink.write("news_toy_search", enriched)
            cap_hit = len(rows) >= limit
            cap_hits += int(cap_hit)
            query_count += 1
            total += written
            sink.set_checkpoint(
                "news_toy_search",
                checkpoint_key,
                status="done",
                query=query,
                market_id=market["market_id"],
                n_rows=written,
                requested_limit=limit,
                cap_hit=cap_hit,
            )
            log.info(
                "news-toy %d/%d %r: %d rows%s",
                query_count,
                sum(len(TOY_NEWS_QUERIES[str(row["question"])]) for row in markets),
                query,
                written,
                " [CAP HIT]" if cap_hit else "",
            )
    sink.set_checkpoint(
        "news_toy_search_summary",
        "all",
        status="done",
        calls=query_count,
        rows=total,
        cap_hits=cap_hits,
        limit=limit,
    )
    log.info("news-toy: %d rows across %d calls; %d cap hits", total, query_count, cap_hits)
    return total


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    version = cfg["extract"]["version"]

    ap = argparse.ArgumentParser(description="EventX findata pullers")
    ap.add_argument("job", choices=[
        "universe", "market-details", "market-details-all", "trades", "trades-all", "candles", "candles-all",
        "kol-roster", "kol-tweets", "kol-tweets-all", "news-toy",
    ])
    ap.add_argument("--venue", choices=["polymarket", "kalshi"])
    ap.add_argument("--market", help="market_id (condition_id / ticker) for trades/candles")
    ap.add_argument("--interval", default="60", help="candle interval in minutes")
    ap.add_argument("--handle", help="KOL handle for single-handle tweet pull")
    args = ap.parse_args()

    sink = JsonlSink(version)
    try:
        with FindataClient() as client:
            if args.job == "universe":
                if not args.venue:
                    ap.error("universe requires --venue")
                pull_universe(client, sink, args.venue)
            elif args.job == "market-details":
                if not args.venue or not args.market:
                    ap.error("market-details requires --venue and --market")
                pull_market_detail(client, sink, args.venue, args.market)
            elif args.job == "market-details-all":
                if not args.venue:
                    ap.error("market-details-all requires --venue")
                pull_all_market_details(client, sink, args.venue)
            elif args.job == "trades":
                if not args.venue or not args.market:
                    ap.error("trades requires --venue and --market")
                pull_trades(client, sink, args.venue, args.market)
            elif args.job == "trades-all":
                if not args.venue:
                    ap.error("trades-all requires --venue")
                pull_all_trades(client, sink, args.venue)
            elif args.job == "candles":
                if not args.venue or not args.market:
                    ap.error("candles requires --venue and --market")
                floor = cfg["candles"]["floor"][args.venue]
                pull_candles(client, sink, args.venue, args.market, args.interval, floor_ts=floor)
            elif args.job == "candles-all":
                if not args.venue:
                    ap.error("candles-all requires --venue")
                pull_all_candles(client, sink, cfg, args.venue)
            elif args.job == "kol-roster":
                pull_kol_roster(client, sink)
            elif args.job == "kol-tweets":
                if not args.handle:
                    ap.error("kol-tweets requires --handle")
                pull_kol_tweets(client, sink, args.handle, since=cfg["window"]["start"])
            elif args.job == "kol-tweets-all":
                pull_all_kol_tweets(client, sink, cfg)
            elif args.job == "news-toy":
                pull_toy_news(client, sink, cfg)
    finally:
        sink.flush()


if __name__ == "__main__":
    main()
