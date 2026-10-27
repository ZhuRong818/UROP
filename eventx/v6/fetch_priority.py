"""Fetch planning only: conservative primary-mention roles, no link admission."""
import re

def primary_names(card, entries):
    if card.get('subtitle_conflict'):
        return set()
    match = re.match(r'^(?:Will|What will) (?:the )?(.+?) (?:be added|say|report|announce|have|win|reach|hit|leave|play|close price|hike|cut|resign|retire|defeat|beat)\b', card['question'], re.I)
    if not match:
        return set()
    name = match[1].casefold()
    return {e['name'].casefold() for e in entries if e['name'].casefold() == name}

def mention_role(card, entries, evidence):
    names = primary_names(card, entries)
    if not names:
        return 'primary_unresolved'
    return 'primary_mention' if any(e['contract_evidence']['name'].casefold() in names for e in evidence) else 'context_only'

def group_key(card):
    events = sorted(set(card.get('event_ids', [])))
    # Operational deduplication only; not certified independent families.
    return events[0] if len(events) == 1 else card['contract_id']
