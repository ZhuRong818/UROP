"""KOL-only candidate matcher for EventX v2.1 association rule v2.

The accepted news-v1 matcher lives in :mod:`eventx.features.v2_1_association`
and is deliberately not imported or changed here. This module reads only market
IDs, the frozen lexical specification, and document text.
"""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable

from eventx.settings import REPO_ROOT


RULE_VERSION = "eventx-v2.1-kol-association-rule-v2-candidate"
LEXICAL_SPEC = REPO_ROOT / "eventx" / "release" / "v2_1" / "kol_association_v2_lexical_spec.json"
SEGMENT_RE = re.compile(r"(?:\n\s*\n+|(?=[•🔸🔹]))")
PERCENT_RE = re.compile(r"\b\d{1,3}(?:[.,]\d+)?\s*(?:%|percent|pp)\b", re.IGNORECASE)
STAT_RE = re.compile(r"\b\d+\s+(?:goals?|assists?|wins?|points?)\b", re.IGNORECASE)
INVASION_RE = re.compile(r"\binvad(?:e|es|ed|ing)\b|\binvasion\b", re.IGNORECASE)


@lru_cache(maxsize=1)
def lexical_spec() -> dict[str, Any]:
    value = json.loads(LEXICAL_SPEC.read_text())
    if value.get("rule_version") != RULE_VERSION:
        raise ValueError("KOL v2 lexical spec rule version mismatch")
    if value.get("scope") != "kol_only":
        raise ValueError("KOL v2 lexical spec has invalid scope")
    return value


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    collapsed = re.sub(r"[^\w]+", " ", without_marks, flags=re.UNICODE)
    return " ".join(collapsed.split())


def segments(text: str) -> list[tuple[str, str]]:
    values = []
    for raw in SEGMENT_RE.split(text):
        raw = raw.strip()
        normalized = normalize(raw)
        if normalized:
            values.append((raw, normalized))
    if not values and text.strip():
        values.append((text.strip(), normalize(text)))
    return values


def normalized_terms(values: Iterable[str]) -> list[str]:
    return [normalize(value) for value in values if normalize(value)]


def present(normalized_text: str, values: Iterable[str]) -> list[str]:
    padded = f" {normalized_text} "
    matches = []
    for value in values:
        term = normalize(value)
        if term and f" {term} " in padded:
            matches.append(value)
    return sorted(set(matches), key=lambda value: (normalize(value), value))


def identity_matches(normalized_text: str, market: dict[str, Any]) -> list[str]:
    matches = present(normalized_text, market.get("identity_any", []))
    padded = f" {normalized_text} "
    for required in market.get("identity_all", []):
        normalized_required = normalized_terms(required)
        if normalized_required and all(f" {term} " in padded for term in normalized_required):
            matches.append(" + ".join(required))
    return sorted(set(matches))


def evidence_for(market_id: str, text: str) -> dict[str, Any]:
    spec = lexical_spec()
    market = spec["markets"].get(market_id)
    if not isinstance(market, dict):
        raise KeyError(f"no KOL v2 lexical profile for market {market_id}")
    globals_ = spec["global"]
    rows = []
    for index, (raw, normalized) in enumerate(segments(text)):
        configured: dict[str, list[str]] = {}
        for field, values in market.items():
            if field.endswith("_any") and isinstance(values, list):
                configured[field] = present(normalized, values)
        identity = identity_matches(normalized, market)
        signal_matches = {
            "candidate": present(normalized, globals_["candidate_prospect_signals"]),
            "conflict": present(normalized, globals_["geopolitical_conflict_signals"]),
            "direct_capacity": present(normalized, globals_["geopolitical_direct_capacity_signals"]),
            "failed_order": present(normalized, globals_["failed_order_markers"]),
            "invasion_escalation": present(normalized, globals_["invasion_escalation_without_us"]),
            "officeholder": present(normalized, globals_["officeholder_status_signals"]),
            "portuguese_candidate": present(normalized, globals_["portuguese_candidate_signals"]),
            "realized_market": present(normalized, globals_["realized_market_signals"]),
            "sanction": present(normalized, globals_["sanction_signals"]),
            "sanction_action": present(normalized, globals_["sanction_action_signals"]),
            "scandal": present(normalized, globals_["scandal_signals"]),
            "sports": present(normalized, globals_["sports_performance_signals"]),
        }
        rows.append(
            {
                "configured": configured,
                "has_invasion_family": bool(INVASION_RE.search(raw)),
                "has_numeric_percentage": bool(PERCENT_RE.search(raw)),
                "has_sports_stat": bool(STAT_RE.search(raw)),
                "identity": identity,
                "segment_index": index,
                "signals": signal_matches,
                "text": raw,
            }
        )
    return {"market_id": market_id, "profile": market["profile"], "segments": rows}


def is_retrieval_candidate(market_id: str, text: str) -> bool:
    """Broad, prediction-independent KOL candidate predicate for audit recall."""
    market = lexical_spec()["markets"].get(market_id)
    if not isinstance(market, dict):
        raise KeyError(f"no KOL v2 lexical profile for market {market_id}")
    normalized = normalize(text)
    retrieval_fields = (
        "identity_any",
        "subject_any",
        "chamber_any",
        "house_any",
        "senate_any",
        "geography_any",
        "venue_any",
        "country_any",
        "us_any",
        "russia_any",
        "ukraine_any",
        "peace_any",
    )
    if any(present(normalized, market.get(field, [])) for field in retrieval_fields):
        return True
    return bool(identity_matches(normalized, market))


def _terms(*groups: Iterable[str]) -> list[str]:
    return sorted({value for group in groups for value in group})


def _local_window(rows: list[dict[str, Any]], center: int, radius: int = 2) -> list[dict[str, Any]]:
    return rows[max(0, center - radius):center + radius + 1]


def _window_configured(rows: list[dict[str, Any]], field: str) -> list[str]:
    return _terms(*(row["configured"].get(field, []) for row in rows))


def _window_signals(rows: list[dict[str, Any]], field: str) -> list[str]:
    return _terms(*(row["signals"][field] for row in rows))


def associate(market_id: str, text: str) -> tuple[list[str], list[str], dict[str, Any]]:
    """Return deterministic KOL-v2 reasons, terms, and segment evidence."""
    spec = lexical_spec()
    market = spec["markets"].get(market_id)
    if not isinstance(market, dict):
        raise KeyError(f"no KOL v2 lexical profile for market {market_id}")
    evidence = evidence_for(market_id, text)
    # A failed-order marker anywhere in the document vetoes proposition copying.
    failed = [
        term
        for row in evidence["segments"]
        for term in row["signals"]["failed_order"]
    ]
    if failed:
        return ["rejected_non_evidentiary_failed_order"], sorted(set(failed)), evidence

    reasons: list[str] = []
    terms: set[str] = set()
    profile = market["profile"]

    # Structured poll and sports posts often put the heading and the named person
    # in adjacent short blocks. Permit a two-block local window around an exact
    # identity, while keeping generic subject/event matching segment-local.
    if profile in {"candidate_election", "individual_sports_award"}:
        for row in evidence["segments"]:
            identity = row["identity"]
            if not identity:
                continue
            window = _local_window(evidence["segments"], row["segment_index"])
            if profile == "candidate_election":
                prospect = _terms(
                    _window_signals(window, "candidate"),
                    _window_signals(window, "portuguese_candidate"),
                    _window_signals(window, "scandal"),
                    _window_signals(window, "realized_market"),
                )
                numeric = any(value["has_numeric_percentage"] for value in window)
                if prospect or numeric:
                    reasons.append(
                        f"exact_candidate_plus_prospect_signal_local_window:segment_{row['segment_index']}"
                    )
                    terms.update(_terms(identity, prospect))
                    if numeric:
                        terms.add("numeric_percentage")
            else:
                sports = _window_signals(window, "sports")
                numeric = any(value["has_sports_stat"] for value in window)
                if sports or numeric:
                    reasons.append(
                        f"exact_athlete_plus_performance_signal_local_window:segment_{row['segment_index']}"
                    )
                    terms.update(_terms(identity, sports))
                    if numeric:
                        terms.add("numeric_sports_stat")
        return sorted(set(reasons)), sorted(terms), evidence

    if profile == "party_race":
        for row in evidence["segments"]:
            window = _local_window(evidence["segments"], row["segment_index"])
            subject = _window_configured(window, "subject_any")
            geography = _window_configured(window, "geography_any")
            venue = _window_configured(window, "venue_any")
            prospect = _window_configured(window, "prospect_any")
            if subject and geography and venue and prospect:
                reasons.append(
                    f"party_plus_jurisdiction_plus_race_signal_local_window:segment_{row['segment_index']}"
                )
                terms.update(_terms(subject, geography, venue, prospect))
        return sorted(set(reasons)), sorted(terms), evidence

    if profile == "composite_chamber_control":
        for row in evidence["segments"]:
            window = _local_window(evidence["segments"], row["segment_index"], radius=1)
            subject = _window_configured(window, "subject_any")
            house = _window_configured(window, "house_any")
            senate = _window_configured(window, "senate_any")
            prospect = _window_configured(window, "prospect_any")
            if subject and (house or senate) and prospect:
                reasons.append(
                    f"party_plus_composite_component_plus_control_signal_local_window:segment_{row['segment_index']}"
                )
                terms.update(_terms(subject, house, senate, prospect))
        return sorted(set(reasons)), sorted(terms), evidence

    for row in evidence["segments"]:
        configured = row["configured"]
        signals = row["signals"]
        identity = row["identity"]

        reason = None
        supporting: list[str] = []
        if profile == "officeholder_status":
            if identity and signals["officeholder"]:
                reason = "exact_officeholder_plus_status_signal_same_segment"
                supporting = _terms(identity, signals["officeholder"])
        elif profile == "us_invasion":
            country = configured.get("country_any", [])
            us = configured.get("us_any", [])
            if country and (
                signals["invasion_escalation"]
                or (
                    us
                    and (
                        signals["conflict"]
                        or signals["direct_capacity"]
                        or signals["realized_market"]
                        or row["has_invasion_family"]
                    )
                )
            ):
                reason = "iran_plus_invasion_or_escalation_signal_same_segment"
                supporting = _terms(
                    country,
                    us,
                    signals["conflict"],
                    signals["direct_capacity"],
                    signals["invasion_escalation"],
                    signals["realized_market"],
                )
                if row["has_invasion_family"]:
                    supporting.append("invasion_verb_family")
        elif profile == "territorial_advance":
            territory = configured.get("territory_context_any", [])
            capacity = _terms(
                signals["direct_capacity"],
                signals["conflict"] if territory else [],
                signals["sanction"] if signals["sanction_action"] else [],
            )
            if identity and capacity:
                reason = "belligerent_plus_operational_capacity_signal_same_segment"
                supporting = _terms(
                    identity,
                    territory,
                    capacity,
                    signals["sanction_action"] if signals["sanction"] else [],
                )
        elif profile == "peace_talks":
            russia = configured.get("russia_any", [])
            ukraine = configured.get("ukraine_any", [])
            peace = configured.get("peace_any", [])
            if (russia or ukraine) and peace:
                reason = "belligerent_plus_peace_process_signal_same_segment"
                supporting = _terms(russia, ukraine, peace)
        elif profile == "legislation":
            if identity and configured.get("signal_any", []):
                reason = "exact_legislation_plus_process_signal_same_segment"
                supporting = _terms(identity, configured["signal_any"])
        elif profile == "single_chamber_control":
            subject = configured.get("subject_any", [])
            chamber = configured.get("chamber_any", [])
            prospect = configured.get("prospect_any", [])
            if subject and chamber and prospect:
                reason = "party_plus_chamber_plus_control_signal_same_segment"
                supporting = _terms(subject, chamber, prospect)
        else:
            raise ValueError(f"unsupported KOL v2 profile {profile!r}")

        if reason:
            reasons.append(f"{reason}:segment_{row['segment_index']}")
            terms.update(supporting)
    return sorted(set(reasons)), sorted(terms), evidence


def prediction(market_id: str, text: str) -> tuple[str, list[str], list[str], dict[str, Any]]:
    reasons, terms, evidence = associate(market_id, text)
    rejected = reasons == ["rejected_non_evidentiary_failed_order"]
    return ("hard_unmatched" if rejected or not reasons else "matched", reasons, terms, evidence)
