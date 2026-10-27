#!/usr/bin/env python3
"""Read-only smoke test for MarketLens historical Polymarket L2 data.

Usage:
    export MARKETLENS_API_KEY='mk_...'
    python3 l2_orderbook_smoke_test/marketlens_l2_smoke_test.py

The default market and timestamp are a documented historical MarketLens example.
Pass a different market UUID and timestamp to test another book:

    python3 l2_orderbook_smoke_test/marketlens_l2_smoke_test.py \
        --market-id <uuid> --at 2026-04-15T01:50:00Z --depth 10

This script only performs one GET request. It never writes the API key or the
returned book to disk.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://api.marketlens.trade/v1"
DEFAULT_MARKET_ID = "4ee145e2-3fee-5b15-bb95-56a33a292945"
DEFAULT_TIMESTAMP = "2026-04-15T01:50:00Z"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market-id", default=DEFAULT_MARKET_ID)
    parser.add_argument("--at", default=DEFAULT_TIMESTAMP, help="ISO-8601 or Unix-ms timestamp")
    parser.add_argument("--depth", type=int, default=5, choices=range(1, 101))
    return parser.parse_args()


def fetch_book(api_key: str, market_id: str, at: str, depth: int) -> dict:
    query = urlencode({"at": at, "depth": depth})
    url = f"{BASE_URL}/markets/{market_id}/orderbook?{query}"
    # MarketLens's Cloudflare layer rejects Python's default "Python-urllib" user
    # agent, while accepting a normal command-line HTTP client identifier.
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "curl/8.7.1",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def format_level(level: dict) -> str:
    return f"{float(level['price']):.4f} x {float(level['size']):,.2f} shares"


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("MARKETLENS_API_KEY")
    if not api_key:
        print("FAIL: Set MARKETLENS_API_KEY before running this script.", file=sys.stderr)
        return 2

    try:
        book = fetch_book(api_key, args.market_id, args.at, args.depth)
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")[:500]
        print(f"FAIL: MarketLens returned HTTP {error.code}: {body}", file=sys.stderr)
        return 1
    except URLError as error:
        print(f"FAIL: Could not reach MarketLens: {error.reason}", file=sys.stderr)
        return 1

    required = {"market_id", "as_of", "bids", "asks", "bid_levels", "ask_levels"}
    missing = required.difference(book)
    if missing:
        print(f"FAIL: Response lacks required L2 fields: {sorted(missing)}", file=sys.stderr)
        return 1

    bids = book["bids"]
    asks = book["asks"]
    if not bids and not asks:
        print("FAIL: Response contains no bid or ask levels.", file=sys.stderr)
        return 1

    print("PASS: MarketLens returned a historical L2 book")
    print(f"market_id: {book['market_id']}")
    print(f"requested_at: {args.at}")
    print(f"as_of_ms: {book['as_of']}")
    print(f"total_levels: {book['bid_levels']} bids / {book['ask_levels']} asks")
    print(f"returned_levels: {len(bids)} bids / {len(asks)} asks")
    if bids:
        print(f"best_bid: {format_level(bids[0])}")
    if asks:
        print(f"best_ask: {format_level(asks[0])}")

    if bids and asks and float(bids[0]["price"]) > float(asks[0]["price"]):
        print("WARNING: The returned book is crossed (best bid > best ask).")
        print("Treat this as an availability test only; investigate book quality before backtesting.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
