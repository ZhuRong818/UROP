"""Deterministic, auditable KOL-tweet to market association for the toy cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import yaml

from eventx.settings import REPO_ROOT

CONFIG_PATH = REPO_ROOT / "eventx" / "config" / "eventx.yaml"
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9._-]*")
CASHTAG_RE = re.compile(r"\$([A-Za-z][A-Za-z0-9]{0,9})")
URL_RE = re.compile(r"https?://\S+")
PROPER_PHRASE_RE = re.compile(r"\b(?:[A-Z][\w'.-]+(?:\s+|$)){1,5}")
PROPER_TOKEN_RE = re.compile(r"\b[A-Z][A-Za-z0-9'.-]{2,}\b")
STOPWORDS = {
    "about", "after", "again", "against", "before", "between", "could", "during", "from",
    "have", "highest", "into", "market", "more", "most", "next", "over", "second", "than",
    "that", "their", "there", "these", "they", "this", "through", "under", "what", "when",
    "where", "which", "while", "will", "with", "would", "year", "finish", "happen", "reach",
    "price", "estimated", "recorded", "least", "first", "third", "fourth", "fifth", "2026",
    "january", "february", "march", "april", "june", "july", "august", "september",
    "october", "november", "december",
}
GENERIC_PHRASES = {
    "prime minister",
    "us presidential",
    "united kingdom",
    "los angeles",
    "california governor election",
}
ELECTORAL_CONTEXT = {
    "2028", "ballot", "campaign", "candidate", "conceded", "defeat", "election",
    "electoral", "eleitorais", "endorsed", "endorsing", "favorite", "favourite",
    "general", "governor", "leader", "leadership", "mayor", "mayoral", "minister",
    "nomination", "nominee", "odds", "poll", "polling", "positioned", "premier",
    "presidency", "presidential", "primary", "pesquisa", "race",
    "races", "runoff", "successor", "succession", "turno", "vote", "voter",
    "voters", "votes",
}
NOMINATION_CONTEXT = ELECTORAL_CONTEXT - {
    "candidate", "minister", "premier", "presidential",
}
ELECTION_CONTEXT = NOMINATION_CONTEXT | {"election", "electoral"}
APPEARANCE_CONTEXT = {
    "absent", "absence", "appeared", "appearance", "ceremony", "funeral", "photo",
    "photographed", "seen", "sighting", "showed", "video", "visible",
}
LEADERSHIP_CONTEXT = {
    "approval", "appointed", "authority", "head", "leader", "leadership", "reappointed",
    "rule", "ruler", "state", "successor", "succession", "supreme",
}
CONFLICT_CONTEXT = {
    "agreement", "attack", "attacks", "ceasefire", "conflict", "forces", "hezbollah",
    "idf", "fighting", "killing", "military", "offensive", "operations", "peace",
    "security", "strike", "strikes", "troops", "war", "withdraw", "withdrawal",
    "withdraws",
}
INVASION_CONTEXT = {
    "arms", "attack", "blockade", "capabilities", "conflict", "conquer", "conquering",
    "crisis", "defense", "defence", "deter", "deterrence", "drill", "drills",
    "escalates", "escalation", "exercise", "exercises", "invade", "invading",
    "invasion", "maritime", "military", "pla", "security", "war",
}
HEALTH_CONTEXT = {
    "case", "cases", "death", "deaths", "outbreak", "outbreaks", "pandemic", "spread",
    "transmission",
}
HORMUZ_STATUS_CONTEXT = {
    "ais", "attack", "attacks", "blocked", "blockade", "bomb", "bombing", "capacity",
    "capacités", "cargo", "close", "closed", "closes", "closing", "closure", "contingent",
    "control", "contrôle", "crisis", "disruption", "disruptions", "drone", "extortion",
    "fee", "fees", "flow", "flowed", "flows", "full", "irrelevant", "jamming",
    "loadings", "management", "managing", "normal", "normale", "oil", "open", "opened",
    "opening", "passage", "reopen", "reopened", "reopening", "route", "routes", "secure",
    "seize", "seized", "seizing", "ship", "shipping", "ships", "shock", "spoofing",
    "strategic", "strike", "strikes", "supply", "tanker", "tankers", "targeting",
    "threat", "threats", "toll", "trafic", "traffic", "transit", "transiting",
    "vessel", "vessels",
}
WITHDRAWAL_CONTEXT = {
    "agreement", "attack", "attacks", "bomb", "bombing", "bombs", "campaign",
    "ceasefire", "deployed", "deployment", "fighting", "forces", "halt", "leave",
    "leaves", "leaving", "occupation", "occupied", "occupies", "occupying", "offensive",
    "operations", "peace", "presence", "remain", "remains", "troops", "withdraw",
    "withdrawal", "withdraws",
}
CHINA_TAIWAN_PATTERNS = (
    "arms sales",
    "assertive stance",
    "blockade",
    "coast guard",
    "combat readiness",
    "conquer",
    "control of taiwan",
    "cross-strait peace",
    "cross strait peace",
    "defence budget",
    "defense budget",
    "deterrent",
    "drill",
    "invad",
    "invasion",
    "military action",
    "military options",
    "military pressure",
    "patrol",
    "provocation",
    "standoff",
    "security guarantee",
    "simulating different scenarios",
    "take taiwan",
    "taking taiwan",
    "taiwan by force",
)
CUBA_CHANGE_PATTERNS = (
    "cair",
    "collapse",
    "collapsing",
    "fall of the regime",
    "government falls",
    "negotiated outcome",
    "overthrow",
    "pode cair",
    "political change",
    "reform",
    "regime change",
    "sanction",
    "transition",
    "tighten the screws",
    "uprising",
)
ELECTORAL_SIGNAL_PATTERNS = (
    "2028",
    "ahead of",
    "considering a run for president",
    "democratic nomination",
    "democratic nominee",
    "favorite to",
    "favourite to",
    "front-runner",
    "frontrunner",
    "gop nominee",
    "lost ground to",
    "next presidential election",
    "nomination",
    "nominee in 2028",
    "nominee for president",
    "odds to",
    "odds to win",
    "positioned than",
    "positioning himself",
    "post-trump",
    "presidential campaign",
    "presidential election",
    "presidential nomination",
    "presidential run",
    "republican nomination",
    "republican nominee",
    "primary poll",
    "run for president",
    "running for president",
    "test the waters",
    "win the presidency",
)
PRIME_MINISTER_PATTERNS = (
    "burnham government",
    "coalition",
    "coronation",
    "leadership bid",
    "leadership contest",
    "leadership race",
    "likely next prime minister",
    "next prime minister",
    "no 10",
    "number 10",
    "on course",
    "poll",
    "prime minister-to-be",
    "qualities to become prime minister",
    "save labour",
    "set to become",
    "suited to serve as prime minister",
    "succession",
    "successor",
    "victory",
)
KAREN_EVENT_CONTEXT = {
    "ballot", "ballots", "campaign", "candidate", "count", "election", "endorse",
    "endorsed", "endorses", "endorsement", "fraud", "leading", "mayor", "mayoral",
    "poll", "primary", "race", "raman", "rigged", "rigging", "runoff", "spencer",
    "vote", "voter", "voters", "votes",
}
UNITED_RUSSIA_ELECTION_CONTEXT = {
    "candidate", "candidates", "duma", "election", "elections", "federal", "list",
    "poll", "polling", "popularity", "primaries", "primary", "seat", "seats", "vote",
    "votes",
}


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return
    with path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def surface_tokens(text: str) -> set[str]:
    return {
        token.strip("._-")
        for token in TOKEN_RE.findall(text.lower())
        if token.strip("._-")
    }


def tokens(text: str) -> set[str]:
    normalized = surface_tokens(text)
    return {
        token
        for token in normalized
        if len(token) >= 4 and token not in STOPWORDS
    }


def content_hash(text: str) -> str:
    normalized = " ".join(TOKEN_RE.findall(URL_RE.sub(" ", text).lower()))
    return hashlib.sha256(normalized.encode()).hexdigest()


def entities_for(question: str) -> dict[str, list[str]]:
    cashtags = sorted({match.upper() for match in CASHTAG_RE.findall(question)})
    phrases: set[str] = set()
    for match in PROPER_PHRASE_RE.finditer(question):
        phrase = " ".join(match.group(0).split()).strip(" ?.,")
        words = phrase.split()
        while words and words[0].lower() in {"will", "what", "when", "where", "the", "a", "an"}:
            words.pop(0)
        phrase = " ".join(words)
        if len(words) >= 2 and len(phrase) >= 4 and phrase.lower() not in STOPWORDS:
            phrases.add(phrase)
    phrase_tokens = {token for phrase in phrases for token in tokens(phrase)}
    anchors = sorted(
        {
            value.lower()
            for value in PROPER_TOKEN_RE.findall(question)
            if value.lower() not in STOPWORDS and value.lower() not in phrase_tokens
        }
    )
    keywords = sorted(tokens(question) - phrase_tokens)[:16]
    subjects = sorted(
        phrase for phrase in phrases if phrase.lower() not in GENERIC_PHRASES
    )
    return {
        "cashtag": cashtags,
        "entity_phrase": sorted(phrases),
        "subject_phrase": subjects,
        "anchor": anchors,
        "keyword": keywords,
    }


def nearby_context(
    text_lower: str,
    phrases: list[str],
    context: set[str],
    window: int = 220,
) -> tuple[list[str], list[str]]:
    exact_phrases = [phrase for phrase in phrases if phrase.lower() in text_lower]
    found_context: set[str] = set()
    for phrase in exact_phrases:
        needle = phrase.lower()
        start = text_lower.find(needle)
        while start >= 0:
            snippet = text_lower[max(0, start - window): start + len(needle) + window]
            snippet_tokens = surface_tokens(snippet)
            found_context.update(snippet_tokens.intersection(context))
            start = text_lower.find(needle, start + len(needle))
    return exact_phrases, sorted(found_context)


def matched_patterns(text_lower: str, patterns: tuple[str, ...]) -> list[str]:
    return sorted(pattern for pattern in patterns if pattern in text_lower)


def subject_aliases(subjects: list[str]) -> list[str]:
    aliases = {subject.lower() for subject in subjects}
    for subject in subjects:
        words = subject.lower().split()
        if len(words) >= 2 and len(words[-1]) >= 4:
            aliases.add(words[-1])
    return sorted(aliases, key=lambda value: (-len(value), value))


def aliases_in_text(text_lower: str, subjects: list[str]) -> list[str]:
    return [alias for alias in subject_aliases(subjects) if alias in text_lower]


def context_near_aliases(
    text_lower: str,
    subjects: list[str],
    context: set[str],
    window: int = 240,
) -> tuple[list[str], list[str]]:
    aliases = aliases_in_text(text_lower, subjects)
    found: set[str] = set()
    for alias in aliases:
        start = text_lower.find(alias)
        while start >= 0:
            snippet = text_lower[max(0, start - window): start + len(alias) + window]
            found.update(surface_tokens(snippet).intersection(context))
            start = text_lower.find(alias, start + len(alias))
    return aliases, sorted(found)


def match_market_v2(
    question: str,
    extracted: dict[str, list[str]],
    text: str,
    tweet_cashtags: set[str],
) -> tuple[list[str], list[str]]:
    """Return v2 match reasons and terms using event-specific semantic guards."""
    text_lower = text.lower()
    tweet_tokens = surface_tokens(text)
    question_lower = question.lower()
    exact_cashtags = sorted(tweet_cashtags.intersection(extracted["cashtag"]))
    reasons: list[str] = []
    terms: list[str] = []
    if exact_cashtags:
        reasons.append("exact_cashtag")
        terms.extend(exact_cashtags)

    subjects = extracted["subject_phrase"]
    if "seen in public" in question_lower:
        exact, context = nearby_context(text_lower, subjects, APPEARANCE_CONTEXT)
        if exact and context:
            reasons.append("subject_plus_appearance_context")
            terms.extend(exact + context)
    elif "head of state" in question_lower:
        exact, context = nearby_context(text_lower, subjects, LEADERSHIP_CONTEXT)
        if exact and context:
            reasons.append("subject_plus_leadership_context")
            terms.extend(exact + context)
    elif "strait of hormuz" in question_lower:
        hormuz_context = tweet_tokens.intersection(
            {
                "blockade", "cargo", "flow", "flows", "hormuz", "maritime", "oil",
                "shipping", "strait", "tanker", "tankers", "traffic", "transit",
            }
        )
        if "hormuz" in tweet_tokens and len(hormuz_context) >= 2:
            reasons.append("exact_market_topic")
            terms.extend(sorted(hormuz_context))
    elif question_lower.startswith("israel withdraws from lebanon"):
        context = sorted(tweet_tokens.intersection(CONFLICT_CONTEXT))
        if {"israel", "lebanon"} <= tweet_tokens and context:
            reasons.append("geography_plus_conflict_context")
            terms.extend(["israel", "lebanon", *context])
    elif "china invade taiwan" in question_lower:
        context = sorted(tweet_tokens.intersection(INVASION_CONTEXT))
        if {"china", "taiwan"} <= tweet_tokens and context:
            reasons.append("geography_plus_invasion_context")
            terms.extend(["china", "taiwan", *context])
    elif "stepnohirsk" in question_lower:
        if "stepnohirsk" in tweet_tokens:
            reasons.append("exact_market_topic")
            terms.append("stepnohirsk")
    elif "hantavirus" in question_lower:
        exact, context = nearby_context(text_lower, ["hantavirus"], HEALTH_CONTEXT)
        if exact and context:
            reasons.append("topic_plus_health_context")
            terms.extend(exact + context)
    elif "cuban regime" in question_lower:
        cuba_terms = {"cuba", "cuban"}.intersection(tweet_tokens)
        regime_terms = {
            "collapse", "dictatorship", "fall", "falls", "freedom", "regime",
            "repression", "sanction", "sanctions",
        }.intersection(tweet_tokens)
        if cuba_terms and regime_terms:
            reasons.append("geography_plus_regime_context")
            terms.extend(sorted(cuba_terms | regime_terms))
    elif "united russia" in question_lower:
        exact, context = nearby_context(
            text_lower,
            ["United Russia"],
            ELECTORAL_CONTEXT | {"congress", "duma", "party", "primaries", "seats"},
        )
        if exact and context:
            reasons.append("subject_plus_electoral_context")
            terms.extend(exact + context)
    elif "rihanna" in question_lower:
        if "rihanna" in tweet_tokens and tweet_tokens.intersection(
            {"album", "gta", "music", "release", "released"}
        ):
            reasons.append("subject_plus_release_context")
            terms.extend(sorted({"rihanna"}.union(
                tweet_tokens.intersection({"album", "gta", "music", "release", "released"})
            )))
    elif "karen bass" in question_lower:
        exact, context = nearby_context(text_lower, subjects, ELECTION_CONTEXT)
        if exact and context:
            reasons.append("subject_plus_electoral_context")
            terms.extend(exact + context)
        elif "los angeles" in text_lower:
            geographic_context = sorted(tweet_tokens.intersection(ELECTION_CONTEXT))
            if geographic_context:
                reasons.append("market_geography_plus_electoral_context")
                terms.extend(["Los Angeles", *geographic_context])
    elif "nomination" in question_lower:
        exact, context = nearby_context(text_lower, subjects, NOMINATION_CONTEXT)
        if exact and context:
            reasons.append("subject_plus_nomination_context")
            terms.extend(exact + context)
    elif "prime minister" in question_lower:
        leadership_context = (
            NOMINATION_CONTEXT
            | {"labour", "leader", "leadership", "poll", "successor", "succession"}
        )
        exact, context = nearby_context(
            text_lower,
            subjects,
            leadership_context,
        )
        succession_language = any(
            marker in text_lower
            for marker in (
                "likely next prime minister",
                "next prime minister",
                "set to become",
                "suited to serve as prime minister",
            )
        )
        if exact and (context or succession_language):
            reasons.append("subject_plus_leadership_context")
            terms.extend(
                exact + context + (["prime minister"] if succession_language else [])
            )
    elif "election" in question_lower or "governor" in question_lower:
        exact, context = nearby_context(text_lower, subjects, ELECTION_CONTEXT)
        if exact and context:
            reasons.append("subject_plus_electoral_context")
            terms.extend(exact + context)

    return sorted(set(reasons)), sorted(set(terms))


def match_market_v3(
    question: str,
    extracted: dict[str, list[str]],
    text: str,
    tweet_cashtags: set[str],
) -> tuple[list[str], list[str]]:
    """Return rule-v3 matches using outcome-specific guards learned pre-test."""
    text_lower = text.lower()
    tweet_tokens = surface_tokens(text)
    question_lower = question.lower()
    exact_cashtags = sorted(tweet_cashtags.intersection(extracted["cashtag"]))
    reasons: list[str] = []
    terms: list[str] = []
    if exact_cashtags:
        reasons.append("exact_cashtag")
        terms.extend(exact_cashtags)

    subjects = extracted["subject_phrase"]
    if "seen in public" in question_lower:
        exact, context = nearby_context(text_lower, subjects, APPEARANCE_CONTEXT)
        if exact and context:
            reasons.append("subject_plus_appearance_context")
            terms.extend(exact + context)
    elif "head of state" in question_lower:
        exact, context = nearby_context(text_lower, subjects, LEADERSHIP_CONTEXT)
        if exact and context:
            reasons.append("subject_plus_leadership_context")
            terms.extend(exact + context)
    elif "strait of hormuz" in question_lower:
        topic_names, status = nearby_context(
            text_lower,
            ["hormuz", "strait"],
            HORMUZ_STATUS_CONTEXT,
            window=360,
        )
        status.extend(
            matched_patterns(
                text_lower,
                (
                    "hormuz tensions",
                    "capacités",
                    "contrôle",
                    "retour à la normale",
                    "state of the strait",
                    "strait of hormuz tensions",
                    "threatening to bomb the strait",
                ),
            )
        )
        status = sorted(set(status))
        regional = tweet_tokens.intersection(
            {"gulf", "iran", "iranian", "middle-east", "oman", "omani"}
        )
        named_hormuz = "hormuz" in tweet_tokens
        named_strait = "strait" in tweet_tokens
        if status and (
            named_hormuz
            or (named_strait and regional)
            or (named_strait and len(status) >= 2)
        ):
            reasons.append("topic_plus_traffic_status")
            terms.extend(
                sorted(
                    set(status)
                    | set(topic_names)
                )
            )
    elif question_lower.startswith("israel withdraws from lebanon"):
        context = sorted(tweet_tokens.intersection(WITHDRAWAL_CONTEXT))
        if "end the war" in text_lower:
            context.append("end the war")
        if "as we speak" in text_lower and "killing" in tweet_tokens:
            context.append("current killing")
        if {"israel", "lebanon"} <= tweet_tokens and context:
            reasons.append("geography_plus_withdrawal_status")
            terms.extend(["israel", "lebanon", *context])
    elif "china invade taiwan" in question_lower:
        patterns = matched_patterns(text_lower, CHINA_TAIWAN_PATTERNS)
        if {"china", "taiwan"} <= tweet_tokens and patterns:
            reasons.append("geography_plus_invasion_signal")
            terms.extend(["china", "taiwan", *patterns])
    elif "stepnohirsk" in question_lower:
        stepnohirsk_context = tweet_tokens.intersection(
            {
                "advance", "advances", "capture", "captured", "control", "fighting",
                "forces", "occupy", "occupied", "russia", "russian", "seize", "seized",
                "troops", "ukraine", "ukrainian",
            }
        )
        if "stepnohirsk" in tweet_tokens and stepnohirsk_context:
            reasons.append("topic_plus_capture_context")
            terms.extend(["stepnohirsk", *sorted(stepnohirsk_context)])
    elif "hantavirus" in question_lower:
        exact, context = nearby_context(text_lower, ["hantavirus"], HEALTH_CONTEXT)
        if exact and context:
            reasons.append("topic_plus_health_context")
            terms.extend(exact + context)
    elif "cuban regime" in question_lower:
        cuba_terms = sorted({"cuba", "cuban"}.intersection(tweet_tokens))
        patterns = matched_patterns(text_lower, CUBA_CHANGE_PATTERNS)
        if cuba_terms and patterns:
            reasons.append("geography_plus_regime_change_signal")
            terms.extend(cuba_terms + patterns)
    elif "united russia" in question_lower:
        exact, context = nearby_context(
            text_lower,
            ["United Russia"],
            UNITED_RUSSIA_ELECTION_CONTEXT,
            window=320,
        )
        if exact and context:
            reasons.append("subject_plus_parliamentary_context")
            terms.extend(exact + context)
    elif "rihanna" in question_lower:
        excluded_feature = any(
            marker in text_lower
            for marker in ("featured on", "feature on", "featuring rihanna")
        )
        release_signal = any(
            marker in text_lower
            for marker in (
                "gta 6", "gta vi", "her album", "new album", "r9",
                "release an album", "album release", "rihanna album",
                "rihanna's album", "rihanna’s album",
            )
        )
        if "rihanna" in tweet_tokens and release_signal and not excluded_feature:
            reasons.append("subject_plus_own_album_signal")
            terms.extend(
                ["rihanna", *matched_patterns(
                    text_lower,
                    (
                        "album release", "gta 6", "gta vi", "her album", "new album",
                        "r9", "release an album", "rihanna album", "rihanna's album",
                        "rihanna’s album",
                    ),
                )]
            )
    elif "karen bass" in question_lower:
        aliases, alias_context = context_near_aliases(
            text_lower,
            subjects,
            KAREN_EVENT_CONTEXT,
            window=280,
        )
        if aliases and alias_context:
            reasons.append("subject_plus_mayoral_context")
            terms.extend(aliases + alias_context)
        else:
            direct_market_phrase = any(
                marker in text_lower
                for marker in (
                    "ballot count in los angeles",
                    "la mayor",
                    "los angeles election",
                    "los angeles mayor",
                    "los angeles mayoral",
                    "mayor of la",
                )
            )
            direct_market_phrase = direct_market_phrase or (
                "los angeles" in text_lower and "mayoral" in tweet_tokens
            )
            geographic_context = sorted(tweet_tokens.intersection(KAREN_EVENT_CONTEXT))
            concrete_context = set(geographic_context) - {"mayor", "mayoral"}
            if direct_market_phrase and concrete_context:
                reasons.append("market_phrase_plus_mayoral_update")
                terms.extend(["Los Angeles mayoral", *geographic_context])
    elif "nomination" in question_lower:
        aliases = aliases_in_text(text_lower, subjects)
        patterns = matched_patterns(text_lower, ELECTORAL_SIGNAL_PATTERNS)
        if aliases and patterns:
            reasons.append("subject_plus_nomination_signal")
            terms.extend(aliases + patterns)
    elif "prime minister" in question_lower:
        aliases = aliases_in_text(text_lower, subjects)
        patterns = matched_patterns(text_lower, PRIME_MINISTER_PATTERNS)
        if aliases and patterns:
            reasons.append("subject_plus_succession_signal")
            terms.extend(aliases + patterns)
    elif "jd vance" in question_lower:
        aliases = aliases_in_text(text_lower, subjects)
        patterns = matched_patterns(text_lower, ELECTORAL_SIGNAL_PATTERNS)
        if aliases and patterns:
            reasons.append("subject_plus_presidential_signal")
            terms.extend(aliases + patterns)
    elif "election" in question_lower or "governor" in question_lower:
        general_election_context = {
            "candidate", "candidato", "conceded", "disputa", "election", "eleicao",
            "eleição", "eleitorais", "endorsed", "face", "faces", "front-runner",
            "fortaleceria", "frontrunner", "governor", "leading", "nominee", "poll",
            "pesquisa", "presidential", "primary", "race", "runoff", "turno", "vote",
            "voter", "voters", "votes", "voto", "votos",
        }
        aliases, context = context_near_aliases(
            text_lower,
            subjects,
            general_election_context,
            window=320,
        )
        if aliases and context:
            reasons.append("subject_plus_election_signal")
            terms.extend(aliases + context)

    return sorted(set(reasons)), sorted(set(terms))


def match_market(
    question: str,
    extracted: dict[str, list[str]],
    text: str,
    tweet_cashtags: set[str],
) -> tuple[list[str], list[str]]:
    """Use the current production association rule."""
    return match_market_v3(question, extracted, text, tweet_cashtags)


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Associate EventX KOL tweets to selected markets")
    parser.add_argument("--version")
    parser.add_argument("--markets", type=Path)
    parser.add_argument("--tweets", type=Path)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()

    config = yaml.safe_load(CONFIG_PATH.read_text())
    version = args.version or config["extract"]["version"]
    root = REPO_ROOT / "data" / version
    markets_path = args.markets or root / "toy" / "selected_markets.jsonl"
    tweets_path = args.tweets or root / "raw" / "kol_tweets.jsonl"
    out_dir = args.out_dir or root / "curated"
    lo = parse_ts(config["window"]["start"])
    hi = parse_ts(config["window"]["end"])
    assert lo is not None and hi is not None

    markets = list(read_jsonl(markets_path))
    if not markets:
        raise SystemExit("No selected markets yet; rerun dense-market selection after trades arrive.")

    market_entities: list[dict[str, Any]] = []
    specs: list[dict[str, Any]] = []
    token_index: dict[str, set[int]] = defaultdict(set)
    cashtag_index: dict[str, set[int]] = defaultdict(set)
    for index, market in enumerate(markets):
        extracted = entities_for(str(market["question"]))
        specs.append({**market, "entities": extracted})
        for entity_type, values in extracted.items():
            for value in values:
                market_entities.append(
                    {
                        "venue": market["venue"],
                        "market_id": market["market_id"],
                        "outcome_id": market["outcome_id"],
                        "entity": value,
                        "entity_type": entity_type,
                        "source": "rule_v3",
                        "extract_version": version,
                    }
                )
                if entity_type == "cashtag":
                    cashtag_index[value].add(index)
                else:
                    for token in tokens(value):
                        token_index[token].add(index)

    associations: list[dict[str, Any]] = []
    tweets_scanned = 0
    tweets_in_window = 0
    matched_tweets: set[str] = set()
    seen_content: set[tuple[str, str]] = set()
    duplicate_matches_removed = 0
    matches_by_reason: Counter[str] = Counter()
    for tweet in read_jsonl(tweets_path):
        tweets_scanned += 1
        ts_raw = tweet.get("created_at") or tweet.get("ts")
        ts = parse_ts(ts_raw)
        if ts is None or not lo <= ts <= hi:
            continue
        tweets_in_window += 1
        text = str(tweet.get("text") or "")
        tweet_tokens = tokens(text)
        tweet_cashtags = {
            str(value).lstrip("$").upper() for value in (tweet.get("cashtags") or []) if value
        }
        tweet_cashtags.update(match.upper() for match in CASHTAG_RE.findall(text))
        candidates: set[int] = set()
        for token in tweet_tokens:
            candidates.update(token_index.get(token, ()))
        for cashtag in tweet_cashtags:
            candidates.update(cashtag_index.get(cashtag, ()))
        for index in candidates:
            market = specs[index]
            extracted = market["entities"]
            reasons, terms = match_market(
                str(market["question"]),
                extracted,
                text,
                tweet_cashtags,
            )
            if not reasons:
                continue
            tweet_id = str(tweet.get("tweet_id") or tweet.get("id") or "")
            digest = content_hash(text)
            dedupe_key = (str(market["market_id"]), digest)
            if dedupe_key in seen_content:
                duplicate_matches_removed += 1
                continue
            seen_content.add(dedupe_key)
            associations.append(
                {
                    "kind": "kol_tweet",
                    "doc_id": tweet_id,
                    "handle": tweet.get("kol_username") or tweet.get("author_username") or tweet.get("_kol_handle"),
                    "ts": ts_raw,
                    "venue": market["venue"],
                    "market_id": market["market_id"],
                    "outcome_id": market["outcome_id"],
                    "match_reason": reasons,
                    "matched_terms": sorted(set(terms)),
                    "content_hash": digest,
                    "association_rule": "rule_v3",
                    "extract_version": version,
                }
            )
            matched_tweets.add(tweet_id)
            matches_by_reason.update(reasons)

    write_jsonl_atomic(out_dir / "market_entities.jsonl", market_entities)
    write_jsonl_atomic(out_dir / "kol_market_assoc.jsonl", associations)
    report = {
        "version": version,
        "association_rule": "rule_v3",
        "window": config["window"],
        "selected_markets": len(markets),
        "market_entities": len(market_entities),
        "tweets_scanned": tweets_scanned,
        "tweets_in_window": tweets_in_window,
        "matched_tweets": len(matched_tweets),
        "associations": len(associations),
        "duplicate_matches_removed": duplicate_matches_removed,
        "matches_by_reason": dict(sorted(matches_by_reason.items())),
    }
    (out_dir / "kol_association_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
