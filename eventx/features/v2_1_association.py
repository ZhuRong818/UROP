"""Frozen-candidate lexical association primitives for EventX v2.1.

This module uses only market metadata and document text. It deliberately contains
no price, trade, outcome, label, prediction, or performance inputs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

from eventx.features.kol_association import CASHTAG_RE, entities_for


RULE_VERSION = "eventx-v2.1-association-rule-v1-candidate"
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9'._-]*", re.IGNORECASE)
GENERIC = {
    "2026", "2027", "2028", "above", "after", "again", "against", "before",
    "below", "between", "december", "during", "first", "from", "have", "highest",
    "and", "feb", "into", "january", "july", "june", "market", "more", "next",
    "november", "october", "over", "price", "reach", "second", "september",
    "than", "that", "their",
    "this", "through", "under", "what", "when", "where", "which", "while", "will",
    "wil", "with", "would", "year",
}
CATEGORY_GENERIC = {
    "politics": {"election", "government", "leader", "party", "politics", "president"},
    "crypto": {"coin", "crypto", "price", "token"},
    "sports": {"championship", "game", "league", "match", "season", "team", "win"},
    "macro": {"economy", "macro", "rate"},
    "other": set(),
}
CONTEXT = {
    "politics": {
        "act", "approval", "ballot", "bill", "cabinet", "campaign", "candidate",
        "coalition", "congress", "control", "election", "electoral", "endorse", "government",
        "governor", "head", "house", "law", "leader", "legislation", "mayor",
        "midterm", "minister", "nomination", "nominee", "office", "parliament",
        "party", "pass", "passed", "passes", "poll", "president", "presidential",
        "primary", "race", "seat", "senate", "signed", "signs", "state",
        "succession", "vote",
    },
    "crypto": {
        "airdrop", "bitcoin", "blockchain", "btc", "coin", "crypto", "defi", "dip",
        "ethereum", "exchange", "fdv", "flip", "launch", "listed", "mainnet",
        "marketcap", "protocol", "reach", "stablecoin", "token", "wallet",
    },
    "sports": {
        "award", "champion", "championship", "coach", "contract", "cup", "draft",
        "fight", "final", "game", "injury", "league", "match", "mvp", "playoff",
        "player", "race", "roster", "score", "season", "team", "title", "tournament",
        "trade", "win",
    },
    "macro": {
        "bank", "central", "cpi", "cut", "debt", "economy", "fed", "gdp", "gold",
        "hike", "inflation", "interest", "payroll", "rate", "recession", "treasury",
        "unemployment", "yield",
    },
    "other": {
        "advance", "announce", "arrest", "attack", "bankruptcy", "capture",
        "ceasefire", "conflict", "deal", "enter", "entered", "enters", "invade",
        "invaded", "invades", "invasion", "ipo", "launch", "meet", "meeting",
        "meets", "met", "military", "peace", "release", "strike", "talks",
        "valuation", "war",
    },
}


def normalized_tokens(text: str) -> set[str]:
    return {
        token.strip("._-").lower()
        for token in TOKEN_RE.findall(text)
        if token.strip("._-")
    }


@dataclass(frozen=True)
class MarketSpec:
    category: str
    question: str
    phrases: tuple[str, ...]
    anchors: tuple[str, ...]
    event_terms: tuple[str, ...]
    keywords: tuple[str, ...]
    cashtags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def market_spec(question: str, category: str) -> MarketSpec:
    if category not in CONTEXT:
        raise ValueError(f"unsupported category {category!r}")
    extracted = entities_for(question)
    phrases = {
        phrase.lower()
        for phrase in [*extracted["subject_phrase"], *extracted["entity_phrase"]]
        if len(phrase.split()) >= 2 and len(phrase) >= 5
    }
    phrase_tokens = {token for phrase in phrases for token in normalized_tokens(phrase)}
    question_tokens = normalized_tokens(question)
    event_terms = question_tokens.intersection(CONTEXT[category])
    excluded = GENERIC | CATEGORY_GENERIC[category]
    anchors = {
        value.lower()
        for value in extracted["anchor"]
        if value.lower() not in excluded
        and value.lower() not in CONTEXT[category]
        and len(value) >= 3
    }
    anchors.update(
        phrase.split()[-1]
        for phrase in phrases
        if len(phrase.split()[-1]) >= 4
        and phrase.split()[-1] not in excluded
        and phrase.split()[-1] not in CONTEXT[category]
    )
    uppercase = {
        token.lower()
        for token in re.findall(r"\b[A-Z][A-Z0-9.-]{1,9}\b", question)
        if token.lower() not in excluded
        and token.lower() not in CONTEXT[category]
        and token.lower() not in {"us", "uk", "usa", "et", "utc"}
    }
    anchors.update(uppercase)
    # Preserve named subjects written in title/mixed case (for example OpenAI,
    # Donald Trump, or New York Yankees).  Category context words are excluded
    # so a generic token such as "IPO" cannot become its own subject anchor.
    named_subject_tokens = {
        token.lower()
        for token in re.findall(r"\b[A-Z][A-Za-z0-9'.-]{2,}\b", question)
        if token.lower() not in excluded
        and token.lower() not in CONTEXT[category]
        and token.lower() not in {"the", "who"}
    }
    anchors.update(named_subject_tokens)
    compound_parts = {
        part
        for anchor in anchors
        for part in re.split(r"[-.]", anchor)
        if len(part) >= 3
        and part not in excluded
        and part not in CONTEXT[category]
    }
    anchors.update(compound_parts)
    keywords = {
        token
        for token in question_tokens - phrase_tokens - anchors - event_terms - excluded
        if len(token) >= 4 and not token.isdigit()
    }
    return MarketSpec(
        category=category,
        question=question,
        phrases=tuple(sorted(phrases, key=lambda value: (-len(value), value))),
        anchors=tuple(sorted(anchors)),
        event_terms=tuple(sorted(event_terms)),
        keywords=tuple(sorted(keywords)),
        cashtags=tuple(sorted({value.upper() for value in CASHTAG_RE.findall(question)})),
    )


def candidate_evidence(spec: MarketSpec, text: str) -> dict[str, list[str]]:
    lower = text.lower()
    doc_tokens = normalized_tokens(text)
    phrases = [phrase for phrase in spec.phrases if phrase in lower]
    anchors = sorted(doc_tokens.intersection(spec.anchors))
    keywords = sorted(doc_tokens.intersection(spec.keywords))
    context = sorted(doc_tokens.intersection(CONTEXT[spec.category]))
    event_terms = sorted(doc_tokens.intersection(spec.event_terms))
    cashtags = sorted(
        {value.upper() for value in CASHTAG_RE.findall(text)}.intersection(spec.cashtags)
    )
    return {
        "anchors": anchors,
        "cashtags": cashtags,
        "context": context,
        "event_terms": event_terms,
        "keywords": keywords,
        "phrases": phrases,
    }


def is_retrieval_candidate(evidence: dict[str, list[str]]) -> bool:
    return bool(
        evidence["cashtags"]
        or evidence["phrases"]
        or evidence["anchors"]
        or evidence["event_terms"]
        or len(evidence["keywords"]) >= 2
    )


def associate(spec: MarketSpec, text: str) -> tuple[list[str], list[str]]:
    """Return deterministic match reasons and the exact supporting terms."""
    evidence = candidate_evidence(spec, text)
    reasons: list[str] = []
    terms: set[str] = set()
    if evidence["cashtags"]:
        reasons.append("exact_cashtag")
        terms.update(evidence["cashtags"])
    event_context = (
        evidence["event_terms"]
        if spec.category in {"politics", "other"}
        else evidence["context"]
    )
    if evidence["phrases"] and event_context:
        reasons.append("exact_entity_phrase_plus_category_context")
        terms.update(evidence["phrases"])
        terms.update(event_context)
    if len(evidence["anchors"]) >= 2 and event_context:
        reasons.append("multiple_anchors_plus_category_context")
        terms.update(evidence["anchors"])
        terms.update(event_context)
    if (
        spec.category == "sports"
        and evidence["anchors"]
        and evidence["context"]
        and (evidence["keywords"] or len(evidence["context"]) >= 2)
    ):
        reasons.append("subject_anchor_plus_event_context")
        terms.update(evidence["anchors"])
        terms.update(evidence["keywords"])
        terms.update(evidence["context"])
    if (
        spec.category == "politics"
        and evidence["anchors"]
        and evidence["event_terms"]
    ):
        reasons.append("subject_anchor_plus_question_event_context")
        terms.update(evidence["anchors"])
        terms.update(evidence["event_terms"])
    if (
        spec.category == "crypto"
        and evidence["anchors"]
        and evidence["context"]
    ):
        reasons.append("named_topic_anchor_plus_domain_context")
        terms.update(evidence["anchors"])
        terms.update(evidence["context"])
    if (
        spec.category == "other"
        and evidence["anchors"]
        and evidence["event_terms"]
    ):
        reasons.append("named_topic_anchor_plus_question_event_context")
        terms.update(evidence["anchors"])
        terms.update(evidence["event_terms"])
    if (
        spec.category in {"crypto", "macro"}
        and evidence["anchors"]
        and evidence["context"]
        and (evidence["keywords"] or len(evidence["context"]) >= 2)
    ):
        reasons.append("topic_anchor_plus_domain_context")
        terms.update(evidence["anchors"])
        terms.update(evidence["keywords"])
        terms.update(evidence["context"])
    if (
        spec.category == "macro"
        and (evidence["event_terms"] or evidence["keywords"])
        and evidence["context"]
    ):
        reasons.append("macro_indicator_plus_context")
        terms.update(evidence["event_terms"])
        terms.update(evidence["keywords"])
        terms.update(evidence["context"])
    if (
        spec.category == "other"
        and evidence["phrases"]
        and len(evidence["keywords"]) >= 1
    ):
        reasons.append("exact_entity_phrase_plus_market_keyword")
        terms.update(evidence["phrases"])
        terms.update(evidence["keywords"])
    return sorted(set(reasons)), sorted(terms)
