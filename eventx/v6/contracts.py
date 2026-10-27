"""Evidence-preserving contract representations with fail-closed PIT admission."""

from datetime import datetime, timezone
import json


def utc(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)


def canonical_id(venue, kind, value):
    if venue not in {"kalshi", "polymarket"} or kind not in {"event", "contract"}:
        raise ValueError("Unknown namespace")
    prefix = f"{venue}:{kind}:"
    value = str(value).strip()
    if value.startswith(prefix):
        value = value[len(prefix):]
    if not value or ":" in value:
        raise ValueError("Missing or conflicting identifier namespace")
    if venue == "polymarket" and kind == "contract":
        value = value.lower()
    return prefix + value


def outcome_mapping(outcomes, token_ids):
    """Parse provider JSON strings without guessing YES from array position."""
    def array(value):
        for _ in range(2):
            if isinstance(value, str):
                value = json.loads(value)
        if not isinstance(value, list):
            raise ValueError("Expected array")
        return value
    labels, tokens = array(outcomes), array(token_ids)
    if len(labels) != len(tokens) or len(labels) != 2:
        raise ValueError("Binary outcome/token length mismatch")
    names = [str(x).strip().lower() for x in labels]
    if set(names) != {"yes", "no"} or any(not str(x).strip() for x in tokens):
        raise ValueError("Unverified binary outcome mapping")
    if len(set(map(str, tokens))) != 2:
        raise ValueError("Duplicate token")
    return dict(zip(names, map(str, tokens)))


def review_text(card):
    """Retrospective retrieval only: evidence can be newer than the event."""
    parts = [card.get("question"), card.get("yes_subtitle"), *card.get("event_titles", [])]
    parts += [e["text"] for e in card.get("rule_evidence", [])]
    return "\n".join(dict.fromkeys(p.strip() for p in parts if p and p.strip()))


def predictive_text(card, decision_ts):
    """Never promote a review card or silently drop uncertified fields."""
    proof = card.get("pit_certificate")
    if not proof or not proof.get("verified") or not proof.get("evidence_ref"):
        raise ValueError("Contract historical version/validity not certified")
    t = utc(decision_ts)
    if utc(proof["available_at"]) > t or utc(proof["valid_from"]) > t:
        raise ValueError("Metadata not yet available/valid")
    if proof.get("valid_until") and t >= utc(proof["valid_until"]):
        raise ValueError("Metadata validity expired")
    # Certificate must cover the exact full representation, including rules.
    import hashlib
    text = review_text(card)
    if proof.get("text_sha256") != hashlib.sha256(text.encode()).hexdigest():
        raise ValueError("Certificate does not cover this text version")
    return text
