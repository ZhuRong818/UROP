"""Build and sample the label-blind EventX v2.1 market taxonomy."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterator

from eventx.settings import REPO_ROOT


DEFAULT_PROTOCOL = REPO_ROOT / "eventx" / "release" / "v2_1" / "protocol.json"
DEFAULT_GUIDE = REPO_ROOT / "eventx" / "release" / "v2" / "TAXONOMY_GUIDE.md"
DEFAULT_CANDIDATE_DB = (
    REPO_ROOT / "data" / "v2_1" / "prospective" / "state" / "collector.sqlite3"
)
DEFAULT_MARKETS = REPO_ROOT / "data" / "v1" / "curated" / "markets.jsonl"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "v2_1" / "taxonomy"
TAXONOMY_VERSION = "eventx-v2.1-taxonomy-v7"
SAMPLE_SEED = 20260807

POLITICS_PATTERNS = (
    r"\belections?\b",
    r"\belectoral\b",
    r"\bnominee\b",
    r"\bnomination\b",
    r"\b(?:presidential|senate|house|gubernatorial|party|congressional) primar(?:y|ies)\b",
    r"\bprimar(?:y|ies) (?:election|race|ballot)\b",
    r"\bpresident(?:ial|cy)?\b",
    r"\bprime minister\b",
    r"\bminister\b",
    r"\bhead of state\b",
    r"\bgovernor\b",
    r"\bgubernatorial\b",
    r"\bmayor(?:al)?\b",
    r"\bparliament(?:ary)?\b",
    r"\bcongress(?:ional)?\b",
    r"\bsenat(?:e|or|orial)\b",
    r"\bhouse (?:seat|race|control|majority|minority|speaker)\b",
    r"\bspeaker of the house\b",
    r"\b(?:republican|democratic|democrat|labour|conservative|liberal) party\b",
    r"\brepublicans?\b",
    r"\bdemocrats?\b",
    r"\bconservatives?\b",
    r"\bliberals?\b",
    r"\bcabinet\b",
    r"\bchancellor\b",
    r"\bsecretary-general\b",
    r"\bsecretary of (?:state|defense|defence|commerce|treasury|homeland security)\b",
    r"\bconfirmed as (?:fed chair|director of national intelligence)\b",
    r"\bleader of (?:[\w'-]+(?:\s+[\w'-]+){0,5})\b",
    r"\b(?:de facto|next) leader\b",
    r"\bout as [^?]{0,50}\bleader\b",
    r"\b(?:leave|rejoin) the [^?]{0,30}\badministration\b",
    r"\bsupreme court (?:justice|vacancy)\b",
    r"\bfederal coalition\b",
    r"\breferendum\b",
    r"\bballot\b",
    r"\bimpeach(?:ment|ed)?\b",
    r"\blegislat(?:ion|ive|ure)\b",
    r"\b(?:bill|veto) (?:pass|passes|passed|override|overridden|signed)\b",
    r"\bsigned into law\b",
    r"\bgovernment shutdown\b",
    r"\bfederal government\b",
    r"\b(?:tax|tariff)s? (?:suspended|repealed|passed|raised|cut|increase|decrease|eliminated)\b",
    r"\b(?:eliminates?|repeals?) [^?]{0,40}\b(?:tax|tariff)s?\b",
    r"\bapproval rating\b",
    r"\bparty (?:control|majority|leader|leadership)\b",
    r"\brun for public office\b",
    r"\bbecome law\b",
    r"\benacts? .{0,40}\bbill\b",
    r"\bregister .{0,30}\bparty\b",
    r"\bvote for independence\b",
    r"\bout as [^?]{0,50}\bpm\b",
    r"\bcouncil of ministers\b",
    r"\bleadership change\b",
    r"\b25th amendment\b",
    r"\bproposition\b",
    r"\bpass(?:es|ed)? (?:a |the )?(?:national |federal |state )?budget\b",
    r"\bdepartment of [a-z ]+\b",
    r"\b(?:tax|tariff)s? [^?]{0,20}(?:suspended|repealed|raised|cut)\b",
    r"\b(?:deductions|act|section|cap) (?:is |be )?repealed\b",
    r"\bblue tsunami\b",
    r"\bblue wave\b",
    r"\bmidterms?\b",
    r"\bconstitution\b",
    r"\bnext fda commissioner\b",
    r"\bhead of the [^?]{0,30}\brepublic\b",
    r"\bpm [^?]{0,40}\bout\b",
    r"\b(?:modi|xi jinping|netanyahu|erdoğan|masoud pezeshkian) out\b",
    r"\blead iran\b",
    r"\b[a-z]{2}-(?:sen|gov|\d{1,2})\b",
    r"\bpass [^?]{0,40}\btax\b",
    r"\bout as (?:president|prime minister|governor|mayor)\b",
    r"\bresign(?:s|ed|ation)? (?:as|before|by|from)\b",
)

CRYPTO_PATTERNS = (
    r"\bcrypto(?:currency|currencies)?\b",
    r"\bbitcoin\b",
    r"\bbtc\b",
    r"\bethereum\b",
    r"\beth\b",
    r"\bsolana\b",
    r"\bsol\b",
    r"\bdogecoin\b",
    r"\bdoge\b",
    r"\bxrp\b",
    r"\bcardano\b",
    r"\bhyperliquid\b",
    r"\bbinance\b",
    r"\bcoinbase\b",
    r"\busdc\b",
    r"\bsatoshi\b",
    r"\b(?:usdt|usd1|usde|tether)\b",
    r"\b(?:kraken|consensys)\b",
    r"\b(?:ethena|zcash|chainlink|monero)\b",
    r"\b(?:uni|bnb) (?:reach|dip|hit|flip)\b",
    r"\bflip pump\b",
    r"\bcex\b",
    r"\bblockchain\b",
    r"\bstablecoin\b",
    r"\bmemecoin\b",
    r"\bdefi\b",
    r"\bmainnet\b",
    r"\bairdrop\b",
    r"\btoken (?:launch|price|sale|unlock|supply)\b",
    r"\blaunch a token\b",
    r"\bfdv\b",
    r"\bmarket cap.*(?:coin|token|crypto)\b",
    r"\bcoin launched\b",
)

SPORTS_PATTERNS = (
    r"\b(?:nfl|nba|wnba|nhl|mlb|mls|ufc|fifa|uefa|afl|atp|wta|ncaa)\b",
    r"\b(?:football|soccer|basketball|baseball|hockey|tennis|golf|cricket|rugby)\b",
    r"\bformula ?1\b",
    r"\bf1\b",
    r"\bnascar\b",
    r"\bgrand prix\b",
    r"\bolympic(?:s)?\b",
    r"\bworld cup\b",
    r"\bworld series\b",
    r"\bsuper bowl\b",
    r"\bstanley cup\b",
    r"\bnba finals\b",
    r"\b(?:al|nl) (?:central|east|west) title\b",
    r"\b(?:afc|nfc) (?:north|south|east|west)\b",
    r"\bchampion(?:ship)?\b",
    r"\bplayoffs?\b",
    r"\b(?:semi[- ]?final|quarter[- ]?final|final match)\b",
    r"\bmatch(?:up)?\b",
    r"\btournament\b",
    r"\b(?:league|cup) (?:title|winner|champion)\b",
    r"\b(?:mvp|rookie of the year|golden boot|ballon d'or|hank aaron award)\b",
    r"\bcy young award\b",
    r"\bplatinum glove award\b",
    r"\bedgar martinez outstanding designated hitter award\b",
    r"\blebron(?: james)?(?:'s|’s)?\b",
    r"\bgrok ai beat t1\b",
    r"\bplay for the\b",
    r"\bnext team\b",
    r"\bhead coach\b",
    r"\b(?:fight|face) [\w' -]{2,40} next\b",
    r"\b(?:lpl|lck|lec|lcs|cblol)\b",
    r"\b(?:lol|league of legends) worlds\b",
    r"\besports?\b",
    r"\bscore (?:at least|more than|under|over)\b",
    r"\bgoals?\b",
    r"\binnings?\b",
    r"\b(?:coach|manager) of (?:the )?[A-Z]",
)

MACRO_PATTERNS = (
    r"\bconsumer price index\b",
    r"\bcpi\b",
    r"\bgross domestic product\b",
    r"\bgdp\b",
    r"\bunemployment (?:rate|claims?)\b",
    r"\bnonfarm payrolls?\b",
    r"\binflation (?:rate|print|above|below|reach|fall|rise)\b",
    r"\bannual inflation\b",
    r"\bfederal reserve\b",
    r"\b(?:the )?fed(?:'s|’s)?\b",
    r"\bfed (?:rate|chair|meeting|cut|hike)\b",
    r"\bcentral bank\b",
    r"\bbank of england\b",
    r"\bbank of canada (?:rate|meeting|cut|hike)\b",
    r"\beuropean central bank\b",
    r"\becb (?:rate|meeting|cut|hike)\b",
    r"\bpolicy rate\b",
    r"\binterest rates?\b",
    r"\bfederal funds rate\b",
    r"\btreasury yields?\b",
    r"\byield curve\b",
    r"\bgovernment debt\b",
    r"\bnational debt\b",
    r"\bdebt[- ]to[- ]gdp\b",
    r"\brecession\b",
    r"\bsoft landing\b",
    r"\bbrent crude\b",
    r"\bwti crude\b",
    r"\bcrude oil\b",
    r"\bgold price\b",
    r"\bgold \(gc\)",
    r"\bgold (?:\(gc\)|have|hit|reach|rise|fall|performance)\b",
)

CATEGORY_PATTERNS = {
    "politics": tuple(re.compile(pattern, re.IGNORECASE) for pattern in POLITICS_PATTERNS),
    "crypto": tuple(re.compile(pattern, re.IGNORECASE) for pattern in CRYPTO_PATTERNS),
    "sports": tuple(re.compile(pattern, re.IGNORECASE) for pattern in SPORTS_PATTERNS),
    "macro": tuple(re.compile(pattern, re.IGNORECASE) for pattern in MACRO_PATTERNS),
}


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            yield value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def classify(question: str) -> tuple[str, list[str]]:
    # Descriptions from some providers contain repeated attribution boilerplate
    # (for example, "primary source") that is unrelated to market semantics.
    # The canonical question/title is therefore the sole deterministic input.
    text = re.sub(r"\s+", " ", question).strip()
    for category in ("politics", "crypto", "sports", "macro"):
        matches = sorted(
            {match.group(0).lower() for pattern in CATEGORY_PATTERNS[category] for match in pattern.finditer(text)}
        )
        if matches:
            return category, matches
    return "other", []


def atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def load_candidates(path: Path) -> set[tuple[str, str]]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT venue, market_id FROM candidate_markets ORDER BY venue, market_id"
        ).fetchall()
    finally:
        connection.close()
    return {(str(venue), str(market_id)) for venue, market_id in rows}


def deterministic_sample(
    rows: list[dict[str, Any]],
    *,
    per_category: int,
    seed: int,
) -> list[dict[str, Any]]:
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_category[row["category"]].append(row)
    selected: list[dict[str, Any]] = []
    for category in ("politics", "crypto", "sports", "macro", "other"):
        candidates = by_category[category]
        kalshi = [row for row in candidates if row["venue"] == "kalshi"]
        polymarket = [row for row in candidates if row["venue"] == "polymarket"]
        key = lambda row: stable_hash(f"{seed}:{category}:{row['venue']}:{row['market_id']}")
        kalshi.sort(key=key)
        polymarket.sort(key=key)
        retained = kalshi[:per_category]
        retained.extend(polymarket[: max(0, per_category - len(retained))])
        if len(retained) < per_category:
            raise ValueError(
                f"category {category} has only {len(retained)} rows; need {per_category}"
            )
        selected.extend(retained)
    selected.sort(key=lambda row: stable_hash(f"{seed}:order:{row['venue']}:{row['market_id']}"))
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--guide", type=Path, default=DEFAULT_GUIDE)
    parser.add_argument("--candidate-db", type=Path, default=DEFAULT_CANDIDATE_DB)
    parser.add_argument("--markets", type=Path, default=DEFAULT_MARKETS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sample-per-category", type=int, default=50)
    parser.add_argument("--seed", type=int, default=SAMPLE_SEED)
    args = parser.parse_args()
    args.output_dir = args.output_dir.resolve()

    protocol = json.loads(args.protocol.read_text())
    if protocol.get("status") != "preregistered_labels_uninspected":
        raise SystemExit("protocol is not label-uninspected")
    candidates = load_candidates(args.candidate_db)
    markets: dict[tuple[str, str], dict[str, Any]] = {}
    for row in read_jsonl(args.markets):
        key = (str(row.get("venue") or ""), str(row.get("market_id") or ""))
        if key not in candidates:
            continue
        if row.get("is_binary") is not True or row.get("canonical_side") is not True:
            continue
        if key in markets:
            raise ValueError(f"duplicate canonical market {key}")
        markets[key] = row
    missing = sorted(candidates - set(markets))
    if missing:
        raise ValueError(f"{len(missing)} candidate markets lack canonical metadata")

    mapping: list[dict[str, Any]] = []
    for key in sorted(candidates):
        source = markets[key]
        category, matches = classify(str(source.get("question") or ""))
        mapping.append(
            {
                "canonical_side": True,
                "category": category,
                "description": source.get("description"),
                "is_binary": True,
                "market_id": key[1],
                "outcome_id": str(source.get("outcome_id") or "YES"),
                "provenance": {
                    "candidate_source": "v2_1_collector_candidate_snapshot",
                    "metadata_path": "data/v1/curated/markets.jsonl",
                    "permitted_inputs": ["question"],
                    "prices_or_trades_used": False,
                },
                "question": source.get("question"),
                "resolution_ts": source.get("resolution_ts"),
                "review_status": "deterministic_first_pass_unreviewed",
                "rule_matches": matches,
                "scheduled_close_ts": source.get("scheduled_close_ts"),
                "status": source.get("status"),
                "taxonomy_version": TAXONOMY_VERSION,
                "venue": key[0],
            }
        )

    sampled = deterministic_sample(
        mapping,
        per_category=args.sample_per_category,
        seed=args.seed,
    )
    blind_rows: list[dict[str, Any]] = []
    key_rows: list[dict[str, Any]] = []
    for row in sampled:
        audit_id = stable_hash(f"{row['venue']}:{row['market_id']}")[:16]
        blind_rows.append(
            {
                "audit_id": audit_id,
                "description": row.get("description"),
                "market_id": row["market_id"],
                "question": row.get("question"),
                "venue": row["venue"],
            }
        )
        key_rows.append(
            {
                "audit_id": audit_id,
                "market_id": row["market_id"],
                "proposed_category": row["category"],
                "rule_matches": row["rule_matches"],
                "taxonomy_version": TAXONOMY_VERSION,
                "venue": row["venue"],
            }
        )

    mapping_path = args.output_dir / "market_categories.jsonl"
    sample_path = args.output_dir / "blind_review_sample.jsonl"
    key_path = args.output_dir / "blind_review_key.jsonl"
    atomic_jsonl(mapping_path, mapping)
    atomic_jsonl(sample_path, blind_rows)
    atomic_jsonl(key_path, key_rows)
    candidate_material = "\n".join(f"{venue}:{market_id}" for venue, market_id in sorted(candidates))
    report = {
        "candidate_count": len(candidates),
        "candidate_set_sha256": hashlib.sha256(candidate_material.encode()).hexdigest(),
        "category_counts": dict(sorted(Counter(row["category"] for row in mapping).items())),
        "input_hashes": {
            "eventx/release/v2/TAXONOMY_GUIDE.md": sha256_file(args.guide),
            "eventx/release/v2_1/protocol.json": sha256_file(args.protocol),
            "data/v1/curated/markets.jsonl": sha256_file(args.markets),
        },
        "label_blind": True,
        "labels_read": [],
        "mapping": {
            "bytes": mapping_path.stat().st_size,
            "path": str(mapping_path.relative_to(REPO_ROOT)),
            "sha256": sha256_file(mapping_path),
        },
        "protocol_id": protocol["protocol_id"],
        "review_key": {
            "bytes": key_path.stat().st_size,
            "path": str(key_path.relative_to(REPO_ROOT)),
            "sha256": sha256_file(key_path),
        },
        "review_sample": {
            "bytes": sample_path.stat().st_size,
            "path": str(sample_path.relative_to(REPO_ROOT)),
            "rows": len(blind_rows),
            "sha256": sha256_file(sample_path),
            "strata": {
                f"{venue}:{category}": count
                for (venue, category), count in sorted(
                    Counter((row["venue"], row["category"]) for row in sampled).items()
                )
            },
        },
        "sample_seed": args.seed,
        "status": "first_pass_and_blind_sample_frozen",
        "taxonomy_version": TAXONOMY_VERSION,
    }
    atomic_json(args.output_dir / "taxonomy_build_report.json", report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
