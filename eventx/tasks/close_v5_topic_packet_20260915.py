"""Record authorized topic adjudication; stage remaining reviews without outcomes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v5/topic_adjudication_20260915'
BASE = ROOT / 'data/v5/review_followup_20260915'

def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]

def main():
    submitted = BASE / 'packet_independent_topic_review.jsonl'
    first_path = ROOT / 'data/v5/topic_first_review_20260914/first_review.jsonl'
    queue_path = ROOT / 'data/v5/topic_coverage_triage_20260914/topic_review_queue.jsonl'
    packet_path = BASE / 'second_reviewer/packet.jsonl'
    add_path = BASE / 'belgium_first_review_addendum.json'
    component_path = BASE / 'candidate_components.json'
    first = {r['market_id']: r['reviewer_1_topic'] for r in rows(first_path)}
    add = json.loads(add_path.read_text()); first[add['market_id']] = add['topic']
    packet = {r['market_id']: r for r in rows(packet_path)}
    second = rows(submitted)
    assert len(second) == len({r['market_id'] for r in second}) == 30
    approved = []
    for r in second:
        for key in ('market_id', 'venue', 'question', 'yes_sub_title', 'no_sub_title', 'event_title', 'event_slug'):
            assert r[key] == packet[r['market_id']][key]
        assert r['rationale'] and r['reviewer'] and r['insufficient_context'] is False
        differs = first[r['market_id']] != r['topic']
        if differs:
            assert r['market_id'] == '0x8e7a03cb1970e2ad6533b01892403516b6b3f5b5fa90ed7d104c28b27e40ba00'
            assert r['topic'] == 'corporate_traditional_financial'
        approved.append({**r, 'first_review_topic': first[r['market_id']],
            'adjudicated_topic': r['topic'], 'topic_approved': True,
            'approval_scope': 'cached-context pilot topic only',
            'adjudicator': 'Codex with user authorization 2026-09-15',
            'decision_basis': 'Company action determines settlement; crypto secondary context' if differs else 'Reviewer agreement',
            'secondary_context': ['crypto'] if differs else [],
            'historical_metadata_certified': False, 'family_certified': False})
    reviewed = {r['market_id'] for r in approved}
    queue = rows(queue_path)
    remaining = []
    for r in queue:
        if r['market_id'] in reviewed:
            continue
        remaining.append({k: r.get(k) for k in ('market_id','venue','question','yes_sub_title','no_sub_title')} |
            {'reviewer': None, 'topic': None, 'rationale': None, 'confidence': None, 'insufficient_context': None})
    assert len(remaining) == 4621
    components = json.loads(component_path.read_text())
    families = [{'component_index': i, 'candidate_event_ids': group,
                 'reviewer': None, 'boundary_evidence': None,
                 'additional_must_links': [], 'final_boundary_approved': False}
                for i, group in enumerate(components)]
    report = {'pilot_topics_approved': 30, 'pre_adjudication_agreements': 29,
              'adjudicated_disagreements': 1, 'remaining_topic_reviews': len(remaining),
              'provisional_components': len(families), 'final_families_approved': 0,
              'source_gate_passed': False, 'inference_gate_passed': False,
              'v5_frozen': False, 'prediction_outcomes_accessed': False}
    OUT.mkdir(exist_ok=False)
    for name, data in [('approved_pilot_topics.jsonl', approved),
                       ('remaining_topic_review.jsonl', remaining),
                       ('family_boundary_review.jsonl', families)]:
        (OUT/name).write_text(''.join(json.dumps(r)+'\n' for r in data))
    (OUT/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    inputs = [submitted, first_path, queue_path, packet_path, add_path, component_path, Path(__file__)]
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = {'inputs': {str(p.relative_to(ROOT)): sha(p) for p in inputs},
                'outputs': {p.name: sha(p) for p in OUT.iterdir()}}
    (OUT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
