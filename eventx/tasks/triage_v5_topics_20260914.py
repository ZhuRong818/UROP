"""Source-only topic suggestions and review priorities; no automatic certification."""
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v5/topic_coverage_triage_20260914'
QUEUE = ROOT / 'data/v5/recovery_summary_20260910/candidate_family_queue.jsonl'
META = ROOT / 'data/v3_historical/feasibility/raw/kalshi_markets/kalshi_markets.jsonl'
NEWS = ROOT / 'data/v3_historical/primary/label_blind_inputs/news.jsonl'
CORPORATE = re.compile(r'\b(earnings|earnings per share|eps|ipo|initial public offering|'
                       r'market cap|market capitalization|stock price|share price|'
                       r'quarterly revenue|acquisition|merger|s&p 500|nasdaq|dow jones)\b', re.I)
MAP = {'politics': 'politics_public_policy', 'macro': 'macroeconomics',
       'crypto': 'crypto', 'sports': 'sports', 'other': 'other_ambiguous'}


def records(path):
    with path.open() as f:
        for line in f:
            yield json.loads(line)


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def suggest(row):
    matches = sorted(set(m.group().lower() for m in CORPORATE.finditer(row['question'])))
    topic = MAP[row['category']]
    if matches and row['category'] in {'other', 'macro'}:
        topic = 'corporate_traditional_financial'
    return topic, matches


def main():
    if OUT.exists():
        raise FileExistsError('Append-only release already exists')
    queue = list(records(QUEUE))
    meta = {r['ticker']: {k: r.get(k) for k in ['yes_sub_title', 'no_sub_title']}
            for r in records(META)}
    groups = defaultdict(list)
    for row in queue:
        groups[row['candidate_family_id']].append(row)
    topics, flags, prepared, repeated_groups = Counter(), Counter(), [], set()
    for group, rows in sorted(groups.items()):
        if len({r['question'].strip().lower() for r in rows}) < len(rows):
            repeated_groups.add(group)
        for r in rows:
            topic, cues = suggest(r)
            review_flags = ['topic_requires_semantic_review', 'family_boundary_review_required']
            if group in repeated_groups:
                review_flags.append('repeated_question_requires_named_outcome')
            if group.startswith('kalshi:event:KXMVE'):
                review_flags.append('multi_leg_dependency')
            if cues:
                review_flags.append('corporate_cue_requires_resolution_criteria_review')
            if r['venue'] == 'kalshi':
                subtitles = meta.get(r['market_id'], {})
                if group in repeated_groups and not subtitles.get('yes_sub_title'):
                    review_flags.append('missing_yes_subtitle')
            else:
                subtitles = {}
            topics[topic] += 1
            flags.update(review_flags)
            prepared.append({**r, **subtitles, 'suggested_topic': topic,
                'suggestion_basis': 'legacy_label_plus_lexical_triage_not_human_annotation',
                'corporate_cues': cues, 'flags': review_flags,
                'reviewer_1': None, 'reviewer_2': None, 'adjudicated_topic': None,
                'topic_approved': False, 'family_verified': False})
    # Deterministic, label-free review packet. One representative per source event.
    packet, seen = [], set()
    for topic in sorted(topics):
        candidates = sorted((r for r in prepared if r['suggested_topic'] == topic),
                            key=lambda r: hashlib.sha256(r['market_id'].encode()).hexdigest())
        n = 0
        for r in candidates:
            if r['candidate_family_id'] in seen:
                continue
            packet.append(r)
            seen.add(r['candidate_family_id'])
            n += 1
            if n == 5:
                break
    # Timing diagnostics of already opened discovery news; text and outcomes unused.
    lag, run_delay, runs, source_counts = [], [], {}, Counter()
    for r in records(NEWS):
        if not '2026-05-17' <= r['available_at'] < '2026-07-22':
            continue
        ts = lambda k: datetime.fromisoformat(r[k].replace('Z', '+00:00'))
        lag.append((ts('ingest_ts')-ts('published_at')).total_seconds()/60)
        run_delay.append((ts('available_at')-ts('ingest_ts')).total_seconds()/60)
        source_counts[str(r.get('source_endpoint'))] += 1
        run = runs.setdefault(r['source_run_id'], {'run_id': r['source_run_id'],
            'status': r['run_status'], 'source_endpoint': r.get('source_endpoint'), 'articles': 0})
        run['articles'] += 1
    quantiles = lambda x: dict(zip(['p0','p50','p90','p99','p100'],
                                  map(float, np.quantile(x,[0,.5,.9,.99,1]))))
    report = {'status': 'triage_and_review_packet_prepared_not_certified',
        'markets': len(prepared), 'candidate_event_groups': len(groups),
        'repeated_question_groups': len(repeated_groups),
        'suggested_topics': dict(topics), 'market_flag_counts': dict(flags),
        'review_packet_markets': len(packet), 'approved_topics': 0,
        'news_rows': len(lag), 'news_source_counts': dict(source_counts),
        'publication_to_ingest_minutes': quantiles(lag),
        'ingest_to_conservative_availability_minutes': quantiles(run_delay),
        'unique_news_runs': len(runs),
        'interpretation': 'Filtered historical export diagnostics; no upstream completeness or independent family claim',
        'new_labels_read': False, 'models_fitted': 0}
    OUT.mkdir(parents=True)
    for name, vals in [('topic_review_queue.jsonl', prepared), ('review_packet.jsonl', packet),
                        ('news_run_inventory.jsonl', sorted(runs.values(),key=lambda r:-r['articles']))]:
        with (OUT/name).open('w') as f:
            for r in vals:
                f.write(json.dumps(r)+'\n')
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'manifest.json').write_text(json.dumps({'inputs': {str(p.relative_to(ROOT)):sha(p)
        for p in [QUEUE,META,NEWS,Path(__file__)]},
        'outputs':{p.name:sha(p) for p in OUT.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
