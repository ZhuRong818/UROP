"""Prepare a score-blinded development packet from opened historical text only."""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import random
import re

from eventx.v6.retrieval import BM25

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v7/macro_pilot_20261010'
RELEASE = ROOT / 'eventx/release/v7/pilot_20261010'
CARDS = ROOT / 'data/v6/contract_link_pilot_20260916/contract_cards.jsonl'
INDEX = ROOT / 'data/v5/source_readiness_20260908/news_provenance_staging.jsonl'
NEWS = ROOT / 'data/v3_historical/primary/label_blind_inputs/news.jsonl'
EXCLUSIONS = [ROOT / x for x in (
    'data/v6/contract_link_pilot_20260916/articles.jsonl',
    'data/v6/expanded_coverage_20260919/articles.jsonl',
    'data/v6/hybrid_audit_20260916/reserved_articles.jsonl')]
SEED = 20261010
DOMAIN = re.compile(r'Federal Reserve|\bFed\b|\bFOMC\b|\bCPI\b|\bPCE\b|nonfarm|payroll|unemployment|\bGDP\b', re.I)
FOREIGN = re.compile(r'Brazil|Canada|England|European|Eurozone|China|Japan|German|French|United Kingdom|Australia', re.I)
ROUTES = [('monetary_policy', re.compile(r'Federal Reserve|\bFed\b|\bFOMC\b', re.I)),
          ('inflation', re.compile(r'\bCPI\b|\bPCE\b|consumer prices|U\.?S\.? inflation|American inflation', re.I)),
          ('employment', re.compile(r'nonfarm|payroll|U\.?S\.? jobs|U\.?S\.? unemployment|American jobs', re.I))]


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(p):
    with p.open() as f:
        for x in f:
            yield json.loads(x)


def write(p, x):
    p.write_text(json.dumps(x, indent=2, sort_keys=True) + '\n')


def lines(p, records):
    with p.open('w') as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True) + '\n')


def utc(x):
    return datetime.fromisoformat(x.replace('Z', '+00:00'))


def main():
    if OUT.exists():
        raise FileExistsError('Use a new version; packet is append-only')
    pilot_manifest = json.loads((CARDS.parent / 'manifest.json').read_text())
    for path, expected in [(CARDS, pilot_manifest['outputs'][CARDS.name]),
                           (INDEX, pilot_manifest['inputs'][str(INDEX.relative_to(ROOT))]),
                           (NEWS, pilot_manifest['inputs'][str(NEWS.relative_to(ROOT))])]:
        if sha(path) != expected:
            raise ValueError(f'Frozen source hash mismatch: {path.name}')
    # Read IDs/hashes only from exclusions, including reserved text records.
    excluded = [{k:r[k] for k in ('article_id', 'content_sha256')} for p in EXCLUSIONS for r in read(p)]
    ids = {r['article_id'] for r in excluded}
    hashes = {r['content_sha256'] for r in excluded}
    cards = []
    for c in read(CARDS):
        text = c['question'] + '\n' + (c['yes_subtitle'] or '')
        if c['scope'] == 'single_event_candidate_unverified' and DOMAIN.search(text) and not FOREIGN.search(text):
            cards.append(c)
    if len(cards) < 21:
        raise ValueError('Insufficient contract frame; do not widen silently')
    valid = {r['source_line']:r for r in read(INDEX)
             if r['clock_consistent'] and r['article_id'] not in ids and r['content_sha256'] not in hashes
             and utc('2026-05-17T00:00:00Z') <= utc(r['source_clock_available_at']) < utc('2026-07-22T00:00:00Z')}
    OUT.mkdir(parents=True, exist_ok=False)
    inputs = {str(p.relative_to(ROOT)):sha(p) for p in [CARDS, INDEX, NEWS, *EXCLUSIONS,
              RELEASE / 'SAMPLING_PLAN.md', RELEASE / 'ANNOTATION_RUBRIC.md', Path(__file__), ROOT / 'eventx/v6/retrieval.py']}
    write(OUT / 'preparation_receipt.json', {'created_at':datetime.now(timezone.utc).isoformat(),
          'seed':SEED, 'sampling_plan_fixed_before_labels':True, 'inputs':inputs,
          'scope':'opened historical text and metadata only; no outcome or price files',
          'forecast_freeze':False, 'review_labels_read':False})
    articles = []
    with NEWS.open() as f:
        for n, raw in enumerate(f, 1):
            if n not in valid:
                continue
            r = json.loads(raw)
            p = valid[n]
            content = {k:r.get(k) for k in ('headline', 'summary')}
            text = '\n'.join(content[k] or '' for k in content)
            route = next((name for name, pattern in ROUTES if pattern.search(text)), None)
            if route is None:
                continue
            actual = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
            if str(r['id']) != p['article_id'] or actual != p['content_sha256']:
                raise ValueError('Source identity/content mismatch')
            articles.append({'article_id':p['article_id'], **content,
                'content_sha256':actual, 'available_at':p['source_clock_available_at'],
                'published_at':r['published_at'], 'publisher':r.get('publisher'),
                'route':route, 'source_line':n, 'source_run_id':r.get('source_run_id'),
                'run_status':r.get('run_status'), 'ingest_ts':r.get('ingest_ts'),
                'local_content_observed_at':p.get('local_content_observed_at'),
                'historical_content_available_at':p.get('historical_content_available_at')})
    raw_count = len(articles)
    unique = {}
    multiplicities = Counter(a['content_sha256'] for a in articles)
    for a in sorted(articles, key=lambda a:(utc(a['available_at']),a['article_id'])):
        unique.setdefault(a['content_sha256'],a)
    articles = list(unique.values())
    groups = defaultdict(list)
    for a in articles:
        groups[(utc(a['available_at']).date().isoformat(),a['route'])].append(a)
    write(OUT / 'frame_summary.json', {'routed_rows_before_exact_dedup':raw_count,
          'unique_routed_articles':len(articles), 'sampling_buckets':len(groups),
          'cards':len(cards), 'routes':dict(Counter(a['route'] for a in articles))})
    if len(groups) < 30:
        raise ValueError('Fewer than 30 date/route buckets; preserve shortage evidence')
    rng = random.Random(SEED)
    chosen_groups = rng.sample(sorted(groups),30)
    selected = [rng.choice(sorted(groups[g],key=lambda a:a['article_id'])) for g in chosen_groups]
    engine = BM25([c['question']+'\n'+(c['yes_subtitle'] or '')+'\n'+'\n'.join(r['text'] for r in c['rule_evidence']) for c in cards])
    packet, ledger, source_rows, contexts, pool = [], [], [], [], []
    for a in selected:
        hits = engine.search((a['headline'] or '')+'\n'+(a['summary'] or ''),20)
        if len(hits) < 11:
            raise ValueError('Retrieval strata shortage; no post hoc widening')
        rank_ids = [i for i,_ in hits]
        outside = [i for i in range(len(cards)) if i not in rank_ids]
        strata = [('top_one',rank_ids[:1]), ('hard_alternative_rank2_10',rank_ids[1:10]),
                  ('rejected_by_top1_rank11_20',rank_ids[10:20]), ('outside_top20',outside)]
        g = (utc(a['available_at']).date().isoformat(),a['route'])
        article_pi = 30 / len(groups) / len(groups[g])
        prior = [b for b in articles if b['route']==a['route'] and
                 utc(a['available_at'])-timedelta(days=7) <= utc(b['available_at']) < utc(a['available_at'])]
        prior = sorted(prior,key=lambda b:(utc(b['available_at']),b['article_id']),reverse=True)[:3]
        public_article = {k:a[k] for k in ('article_id','headline','summary','content_sha256')}
        prior_public = [{k:b[k] for k in ('article_id','headline','summary','content_sha256')} for b in prior]
        contexts.append({'article_id':a['article_id'],'earlier_reports':prior_public,
                         'scope':'at most three earlier available route reports within seven days; incomplete public information'})
        source_rows.append({**{k:v for k,v in a.items() if k not in ('headline','summary')},
            'exact_content_multiplicity':multiplicities[a['content_sha256']],
            'feed_completeness':'unknown','first_public_time':'unknown','source_admitted':False})
        for rank,(i,score) in enumerate(hits,1):
            pool.append({'article_id':a['article_id'],'contract_id':cards[i]['contract_id'],'rank':rank,'bm25':score})
        for name, candidates in strata:
            i = rng.choice(candidates)
            c = cards[i]
            pair_id = hashlib.sha256(('v7-pilot|'+a['article_id']+'|'+c['contract_id']).encode()).hexdigest()[:24]
            ledger.append({'pair_id':pair_id,'article_id':a['article_id'],'contract_id':c['contract_id'],
                'stratum':name,'bucket':list(g),'bucket_frame_size':len(groups),'articles_in_bucket':len(groups[g]),
                'bucket_inclusion_probability':30/len(groups),'article_inclusion_probability':article_pi,
                'pair_stratum_size':len(candidates),'conditional_pair_probability':1/len(candidates),
                'pair_inclusion_probability':article_pi/len(candidates),'independent_episode_certified':False})
            packet.append({'pair_id':pair_id,'article':public_article,'earlier_reports':prior_public,
                'contract':{k:c[k] for k in ('contract_id','venue','question','yes_subtitle','subtitle_candidates','subtitle_conflict')},
                'rules':[{'field':r['field'],'text':r['text']} for r in c['rule_evidence']],
                'review_purpose':'development semantic evidence annotation; no historical predictive admission'})
    rng.shuffle(packet)
    template = [{'pair_id':r['pair_id'],'reviewer_id':None,'reviewer_kind':None,
                 'independent_of_other_reviewer':None,'outcome_blind':None,'prior_exposure':None,
                 'applicability':None,'role':None,'direction':None,'novelty':None,
                 'public_surprise':'unknown','market_odds_content':None,'episode_key':None,
                 'duplicate_of':None,'predicate':{},'evidence_spans':[],'prior_evidence_spans':[],
                 'contract_spans':[],'rationale':None} for r in packet]
    for name, rows in [('packet',packet),('reviewer_A_blank',template),('reviewer_B_blank',template),
                       ('selection_ledger',ledger),('source_context',source_rows),('prior_context',contexts),
                       ('retrieval_pool',pool),('domain_contract_cards',cards)]:
        lines(OUT / (name+'.jsonl'),rows)
    report = {'status':'development_packet_ready_human_reviews_pending','sampled_articles':len(selected),
        'sampled_date_route_buckets':len(chosen_groups),'distinct_availability_dates':len({g[0] for g in chosen_groups}),
        'article_route_counts':dict(Counter(a['route'] for a in selected)),
        'domain_contracts':len(cards),'domain_source_event_ids':len({e for c in cards for e in c['event_ids']}),
        'domain_cards_with_rules':sum(bool(c['rule_evidence']) for c in cards),
        'review_pairs':len(packet),'strata':dict(Counter(r['stratum'] for r in ledger)),
        'unique_reviewed_contracts':len({r['contract']['contract_id'] for r in packet}),
        'prior_context_reports':sum(len(r['earlier_reports']) for r in contexts),
        'completed_human_reviews':0,'validated_information_episodes':0,'forecast_fits':0,
        'performance_improvement_estimated':False,'protected_outcomes_accessed':False,
        'excluded_article_ids':len(ids),'excluded_content_hashes':len(hashes),
        'unique_routed_articles':len(articles),'routed_rows_before_exact_dedup':raw_count,
        'sampling_bucket_frame':len(groups),'research_freeze':False,
        'limits':['Keyword and date/route buckets are not verified information episodes.',
                  'Retrospective cards lack historical status and rule certification.',
                  'Production precision/recall require weighting and valid dependence inference.',
                  'Signed evidence is not measured surprise; prior context is bounded.']}
    write(OUT / 'report.json',report)
    pages = ['# Outcome-blind development review packet','',
             'Use ANNOTATION_RUBRIC.md; do not open selection_ledger or retrieval_pool during review.',
             'Record responses in a new copy of reviewer_A_blank.jsonl or reviewer_B_blank.jsonl.','']
    for r in packet:
        pages += ['## Pair '+r['pair_id'],'','Article ID: '+r['article']['article_id'],
                  '',r['article']['headline'] or '(headline absent)','',r['article']['summary'] or '(summary absent)',
                  '', 'Contract: '+r['contract']['contract_id'],'',r['contract']['question'],
                  '', 'YES subtitle: '+str(r['contract']['yes_subtitle']),
                  '', 'Rules: '+('\n'.join(x['text'] for x in r['rules']) or '(not supplied; retain uncertainty)'),
                  '', 'Earlier supplied reporting:','']
        for b in r['earlier_reports']:
            pages += ['### Earlier article '+b['article_id'],'',b['headline'] or '', '', b['summary'] or '', '']
        pages += ['---','']
    (OUT / 'REVIEW_PACKET.md').write_text('\n'.join(pages))
    write(OUT / 'manifest.json',{'created_at':datetime.now(timezone.utc).isoformat(),'inputs':inputs,
         'outputs':{p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file()},'research_freeze':False})
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
