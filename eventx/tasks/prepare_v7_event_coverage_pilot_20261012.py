"""Fix an outcome-blind missed-evidence sample and policy-event census.

Opened development only; existing frozen extractors and populations are unchanged.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import re

import numpy as np

from eventx.tasks.prepare_v4_discovery_news_quality import load_documents, EVENT_DTYPE
from eventx.tasks.run_v5_residual_feasibility import REPO_ROOT, EVENTS, MARKETS, read_jsonl, sha256_file
from eventx.tasks.diagnose_v7_signed_evidence_coverage_20261012 import write_json, write_jsonl
from eventx.v7.signed_evidence_v03_3 import extract_signed_evidence

OUT = REPO_ROOT / 'data/v7/event_coverage_pilot_20261012'
PRIOR = REPO_ROOT / 'data/v7/signed_evidence_v03_3_development_20261012'
SEED = 20261012
ROUTES = [
    ('monetary_policy', re.compile(r'Federal Reserve|\bFed\b|\bFOMC\b', re.I)),
    ('inflation', re.compile(r'\bCPI\b|\bPCE\b|consumer prices|U\.?S\.? inflation', re.I)),
    ('employment', re.compile(r'nonfarm|payroll|U\.?S\.? jobs|U\.?S\.? unemployment', re.I)),
]
# Candidate discovery only: the wording does not verify an official event.
POLICY_HEAD = re.compile(r'(?:\bFed\b|Federal Reserve|\bFOMC\b).{0,90}(?:hold|held|keep|kept|maintain|leave|left|cut|raise|hike|unchanged|steady)|(?:rate|interest).{0,45}(?:unchanged|steady).{0,60}(?:\bFed\b|FOMC)', re.I)
DOMAIN = re.compile(r'Federal Reserve|\bFed\b|\bFOMC\b', re.I)


def public(d, index):
    summary = d['text'][len(d['headline']):].strip() if d['text'].startswith(d['headline']) else d['text']
    return {'document_index': index, 'article_id': d['doc_id'], 'headline': d['headline'],
            'summary': summary, 'available_at': d['available_at'].isoformat(),
            'published_at': d['published_at'].isoformat(), 'publisher': d['publisher']}


def main():
    if OUT.exists():
        raise SystemExit('Preserve existing pilot; create another version')
    verified = {}
    for p in (PRIOR/'manifest.json', PRIOR/'publication_manifest.json'):
        for e in json.loads(p.read_text())['artifacts']:
            verified[e['path']] = e['sha256']
    for e in json.loads((PRIOR/'contract.json').read_text())['inputs']:
        verified[e['path']] = e['sha256']
    for name, digest in verified.items():
        if sha256_file(REPO_ROOT/name) != digest:
            raise RuntimeError(f'Frozen hash mismatch: {name}')
    # Reserve exclusion uses identity/content hashes only, never reserved labels/text.
    reserve = REPO_ROOT/'data/v6/hybrid_audit_20260916/reserved_articles.jsonl'
    reserved = [{k:r[k] for k in ('article_id','content_sha256')} for r in read_jsonl(reserve)]
    ids, hashes = {r['article_id'] for r in reserved}, {r['content_sha256'] for r in reserved}
    provenance = REPO_ROOT/'data/v5/source_readiness_20260908/news_provenance_staging.jsonl'
    source_hashes = defaultdict(set)
    for r in read_jsonl(provenance):
        source_hashes[r['article_id']].add(r['content_sha256'])
    verified[str(reserve.relative_to(REPO_ROOT))] = sha256_file(reserve)
    verified[str(provenance.relative_to(REPO_ROOT))] = sha256_file(provenance)
    OUT.mkdir()
    code = Path(__file__).resolve()
    write_json(OUT/'design_receipt.json', {
        'created_at': datetime.now(timezone.utc).isoformat(), 'seed': SEED,
        'scope': '[2026-05-17,2026-07-22) UTC opened development only',
        'fixed_before_prices_or_outcomes': True,
        'sample': '12 distinct date buckets per macro route from documents with no current exact legacy association; choose date then document uniformly using fixed seed',
        'event_census': 'All policy-headline regex candidates, followed by assistant text review; no price-guided event selection',
        'landmark': 'exact available_at+5 minutes; next 30 minutes; one earliest supported arrival per episode-contract',
        'freshness_primary_minutes': 30, 'freshness_secondary_minutes': 60,
        'eligible_history': '>=3 positive executions and >=100 original prepared notional units in trailing 240 minutes; at least 30 one-minute log-odds differences',
        'notional_limit': 'Prepared notional is source size/count; not proven YES-price-times-size dollar notional.',
        'endpoint': 'record observed future execution and endpoint age; absent execution/coverage is unknown, never label zero by default',
        'fit_gate': 'Must have supported signed arrivals with eligible landmarks in both original training/evaluation date blocks and sufficient distinct reviewed episode diversity; otherwise no fit. No new split/window search.',
        'review_kind': 'assistant development inspection, not independent human gold',
        'inputs': [{'path':p,'sha256':h} for p,h in sorted(verified.items())],
        'new_code': {'path':str(code.relative_to(REPO_ROOT)),'sha256':sha256_file(code)},
        'protected_holdouts_accessed': False, 'software_tests_run': False,
    })
    docs, stats = load_documents()
    events = np.memmap(EVENTS, mode='r', dtype=EVENT_DTYPE)
    markets = {int(m['market_index']):m for m in read_jsonl(MARKETS)}
    exact_documents = {int(events[r['event_index']]['document']) for r in read_jsonl(PRIOR/'exact_association_trace.jsonl')}
    allowed = [i for i,d in enumerate(docs) if datetime(2026,5,17,tzinfo=timezone.utc)<=d['available_at']<datetime(2026,7,22,tzinfo=timezone.utc)
               and d['doc_id'] not in ids and not (source_hashes[d['doc_id']] & hashes)]
    buckets = defaultdict(lambda:defaultdict(list))
    candidates = []
    for i in allowed:
        d = docs[i]
        if POLICY_HEAD.search(d['headline']):
            candidates.append(public(d,i))
        if i in exact_documents:
            continue
        route = next((name for name,regex in ROUTES if regex.search(d['text'])),None)
        if route:
            buckets[route][d['available_at'].date().isoformat()].append(i)
    rng = random.Random(SEED)
    sample = []
    for route,_ in ROUTES:
        dates = sorted(buckets[route])
        for day in rng.sample(dates,min(12,len(dates))):
            options = sorted(buckets[route][day],key=lambda i:docs[i]['doc_id'])
            i = rng.choice(options)
            sample.append({**public(docs[i],i),'route':route,'date_bucket':day,
                'bucket_documents':len(options),'date_buckets':len(dates),
                'article_selection_probability':min(12,len(dates))/len(dates)/len(options)})
    # Candidate pool includes every Fed contract, independent of legacy retrieval.
    fed_markets = [m for m in markets.values() if DOMAIN.search(m['question'])]
    sampled = {a['document_index']:a for a in sample+candidates}
    legacy = defaultdict(set)
    for e in events:
        if int(e['document']) in sampled:
            legacy[int(e['document'])].add(int(e['market']))
    decisions = []
    for i,a in sampled.items():
        for m in fed_markets:
            decision = extract_signed_evidence(a['headline'],a['summary'],m['question'],available_at=a['available_at']).to_dict()
            if int(m['market_index']) in legacy[i] or decision['direction']:
                decisions.append({'article_id':a['article_id'],'document_index':i,'market_index':m['market_index'],
                    'market_id':m['market_id'],'question':m['question'],'legacy_retrieved':int(m['market_index']) in legacy[i],
                    'automatic':decision})
    write_jsonl(OUT/'miss_sample.jsonl',sample)
    write_jsonl(OUT/'policy_headline_census.jsonl',candidates)
    write_jsonl(OUT/'fed_contracts.jsonl',fed_markets)
    write_jsonl(OUT/'candidate_decisions.jsonl',decisions)
    write_json(OUT/'preparation_report.json', {'documents':stats, 'reserved_excluded_documents':len(docs)-len(allowed),
        'miss_sample_articles':len(sample),'sample_dates':len({r['date_bucket'] for r in sample}),
        'route_frames':{name:{'documents':sum(map(len,dates.values())),'date_buckets':len(dates)} for name,dates in buckets.items()},
        'policy_headline_candidates':len(candidates),'fed_contracts':len(fed_markets),
        'new_exact_outside_legacy':sum(r['automatic']['direction']!=0 and not r['legacy_retrieved'] for r in decisions),
        'inputs_verified':len(verified),'outcomes_read':False,'prices_read':False,'models_fit':0})
    paths = sorted(p for p in OUT.iterdir() if p.is_file())+[code]
    write_json(OUT/'preparation_manifest.json',{'artifacts':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in paths]})
    print((OUT/'preparation_report.json').read_text())


if __name__=='__main__':
    main()
