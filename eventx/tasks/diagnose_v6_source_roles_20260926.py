"""Opened-development source-clock and existing document-role diagnostic."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from eventx.v6.document_roles import fields as document_fields, hypothesis as document_hypothesis

ROOT=Path(__file__).resolve().parents[2]
COMPARE=ROOT/'data/v6/fixed_pipeline_comparison_20260926'
LEDGER=ROOT/'data/v6/support_ledger_20260926'
CARDS=ROOT/'data/v6/enriched_rule_comparison_20260921'
ARTICLES=ROOT/'data/v6/expanded_coverage_20260919'
INDEX=ROOT/'data/v3_1_historical/primary/development/prepared'
RUNS=ROOT/'data/v5/topic_coverage_triage_20260914'
PRIOR_ROLE=ROOT/'data/v6/document_role_trial_20260921'
OUT=ROOT/'data/v6/source_role_diagnostic_20260926'


def digest(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def read(p:Path):
    with p.open() as f: return [json.loads(x) for x in f if x.strip()]


def write_json(p:Path,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')

def write_jsonl(p:Path,rr):
    with p.open('w') as f:
        for r in rr:f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')


def verify():
    for base in (COMPARE,LEDGER,CARDS,ARTICLES,RUNS,PRIOR_ROLE):
        m=json.loads((base/'manifest.json').read_text())
        for n,h in m.get('outputs',m).items():
            assert digest(base/n)==h,f'changed source {base/n}'
    m=json.loads((INDEX/'manifest.json').read_text())
    locked={x['path']:x['sha256'] for x in m['artifacts']}
    p=INDEX/'market_index.jsonl'
    assert digest(p)==locked[str(p.relative_to(ROOT))]


def inputs():
    paths=[Path(__file__),ROOT/'eventx/v6/document_roles.py',
           ROOT/'eventx/v6/field_aware.py',ROOT/'eventx/v6/clean_speech.py',
           COMPARE/'manifest.json',COMPARE/'pairs.jsonl',COMPARE/'articles.jsonl',
           LEDGER/'manifest.json',LEDGER/'ledger.jsonl',CARDS/'manifest.json',
           CARDS/'cards.jsonl',ARTICLES/'manifest.json',ARTICLES/'articles.jsonl',
           INDEX/'manifest.json',INDEX/'market_index.jsonl',RUNS/'manifest.json',
           RUNS/'news_run_inventory.jsonl',PRIOR_ROLE/'manifest.json']
    return {str(p.relative_to(ROOT)):digest(p) for p in paths}


def utc(s):
    return datetime.fromisoformat(s.replace('Z','+00:00')) if s else None


def prepare():
    assert not OUT.exists(),'version already exists'
    verify()
    pairs=read(COMPARE/'pairs.jsonl')
    cards=read(CARDS/'cards.jsonl')
    articles=read(ARTICLES/'articles.jsonl')
    assert len(pairs)==669 and len(cards)==134
    assert len({p['article_id'] for p in pairs})==70
    assert len({p['article_id'] for p in pairs if p['l1'] is not None})==8
    OUT.mkdir(parents=True)
    spec={
      'version':'v6-source-role-diagnostic-v0.1-20260926',
      'scope':'same 669 opened development candidate pairs; no reserved cases, test labels or outcomes',
      'source_checks':['article availability < metadata snapshot ingestion',
         'article availability < earliest cached rule ingestion',
         'article availability versus recorded terminal (Polymarket nominal)',
         'article availability versus first/last observed development trade',
         'same-day observed trade count and article source-run status'],
      'role_comparison':'apply unchanged document_roles.v0.2 fields/hypothesis to all 669 candidate pairs; compare with stored field_aware.v0.1 hypotheses',
      'interpretation':'diagnostic only; neither heuristic is human gold; snapshot clock does not certify historical version/status; failed source run does not invalidate retained row',
      'admission':0,'predictive_fits':0,
    }
    write_json(OUT/'spec.json',spec)
    write_json(OUT/'receipt.json',{'created_at':datetime.now(timezone.utc).isoformat(),
      'inputs':inputs(),'spec_sha256':digest(OUT/'spec.json'),
      'receipt_written_before_analysis':True})
    print(json.dumps({'prepared':True,'pairs':len(pairs)}),flush=True)


def run():
    assert OUT.exists() and {p.name for p in OUT.iterdir()}=={'spec.json','receipt.json'}
    receipt=json.loads((OUT/'receipt.json').read_text())
    assert receipt['receipt_written_before_analysis']
    assert receipt['spec_sha256']==digest(OUT/'spec.json') and receipt['inputs']==inputs()
    verify()
    pairs=read(COMPARE/'pairs.jsonl')
    article_top={x['article_id']:x for x in read(COMPARE/'articles.jsonl')}
    cards={x['contract_id']:x for x in read(CARDS/'cards.jsonl')}
    articles={x['article_id']:x for x in read(ARTICLES/'articles.jsonl')}
    market={(x['venue'],x['market_id']):x for x in read(INDEX/'market_index.jsonl')}
    runs={x['run_id']:x for x in read(RUNS/'news_run_inventory.jsonl')}
    ledger={(x['contract_id'],x['day']):x for x in read(LEDGER/'ledger.jsonl')}
    typed=[]
    role_changes=[]
    all_status=Counter()
    new_status=Counter()
    for row in pairs:
        aid,cid=row['article_id'],row['contract_id']
        a,c=articles[aid],cards[cid]
        dh=document_hypothesis(a,document_fields(c))
        old=row['field_hypothesis']['status']
        new=dh['status']
        all_status[old]+=1;new_status[new]+=1
        if old!=new:
            role_changes.append({'article_id':aid,'contract_id':cid,
                'old_status':old,'new_status':new,'new_reason':dh['reason'],
                'new_evidence':dh['evidence'],'dense_only_expansion':row['dense_only_expansion']})
        if old=='abstain' and new=='abstain':continue
        clock=utc(a['source_clock_available_at'])
        snap=utc(c['source_ingest_ts'])
        rules=[utc(x.get('available_at')) for x in c['recovered_rule_evidence'] if x.get('available_at')]
        earliest_rule=min(rules) if rules else None
        terminal=c['terminal_fields'].get('close_time') or c['terminal_fields'].get('end_date')
        terminal_clock=utc(terminal)
        m=market[(c['venue'],c['market_id'])]
        first,last=utc(m['first_trade_ts']),utc(m['last_trade_ts'])
        day=clock.date().isoformat()
        day_row=ledger[(cid,day)]
        source_run=runs.get(a['source_run_id'])
        assert source_run is not None
        typed.append({
          'article_id':aid,'contract_id':cid,'venue':c['venue'],
          'article_clock':a['source_clock_available_at'],
          'article_source_run_id':a['source_run_id'],
          'article_source_run_status':source_run['status'],
          'article_historical_content_field_present':bool(a.get('historical_content_available_at')),
          'metadata_snapshot_ingest':c['source_ingest_ts'],
          'metadata_snapshot_precedes_article':snap<=clock,
          'rule_earliest_ingest':earliest_rule.isoformat() if earliest_rule else None,
          'cached_rule_precedes_article':earliest_rule<=clock if earliest_rule else False,
          'recorded_terminal':terminal,
          'recorded_terminal_semantics':'nominal_end' if c['venue']=='polymarket' else 'recorded_close',
          'article_before_recorded_terminal':clock<terminal_clock if terminal_clock else None,
          'first_observed_trade':m['first_trade_ts'],'last_observed_trade':m['last_trade_ts'],
          'article_before_first_observed_trade':clock<first,
          'article_after_last_observed_development_trade':clock>last,
          'observed_trade_count_on_article_day':day_row['observed_trade_count'],
          'legacy_associations_on_article_day':day_row['legacy_association_count'],
          'old_status':old,'new_status':new,
          'old_evidence':row['field_hypothesis']['evidence'],
          'new_evidence':dh['evidence'],
          'dense_only_expansion':row['dense_only_expansion'],
          'provisional_group':c['provisional_split_group'],
          'training_admissible':False,
        })
    old_typed=[x for x in typed if x['old_status']!='abstain']
    new_typed=[x for x in typed if x['new_status']!='abstain']
    top_changes=[]
    for aid,x in article_top.items():
        if x['l1_top_union']==x['l2_top_union']:continue
        top_changes.append({'article_id':aid,'headline':articles[aid]['headline'],
            'l1_top':x['l1_top_union'],'l2_top':x['l2_top_union'],
            'l1_top_questions':[cards[c]['question'] for c in x['l1_top_union']],
            'l2_top_questions':[cards[c]['question'] for c in x['l2_top_union']]})
    report={
      'candidate_pairs':len(pairs),'old_status':dict(all_status),
      'document_role_status':dict(new_status),'role_status_changes':len(role_changes),
      'old_typed_pairs':len(old_typed),'document_role_typed_pairs':len(new_typed),
      'old_typed_articles':len({x['article_id'] for x in old_typed}),
      'document_role_typed_articles':len({x['article_id'] for x in new_typed}),
      'old_typed_snapshot_precedes_article':sum(x['metadata_snapshot_precedes_article'] for x in old_typed),
      'old_typed_rule_precedes_article':sum(x['cached_rule_precedes_article'] for x in old_typed),
      'old_typed_before_recorded_terminal':sum(x['article_before_recorded_terminal'] is True for x in old_typed),
      'old_typed_with_observed_trade_on_day':sum(x['observed_trade_count_on_article_day']>0 for x in old_typed),
      'old_typed_from_failed_runs':sum(x['article_source_run_status']=='failed' for x in old_typed),
      'old_typed_before_first_observed_trade':sum(x['article_before_first_observed_trade'] for x in old_typed),
      'old_typed_after_last_observed_dev_trade':sum(x['article_after_last_observed_development_trade'] for x in old_typed),
      'document_role_snapshot_precedes_article':sum(x['metadata_snapshot_precedes_article'] for x in new_typed),
      'document_role_from_failed_runs':sum(x['article_source_run_status']=='failed' for x in new_typed),
      'distinct_source_runs':len({articles[x['article_id']]['source_run_id'] for x in old_typed}),
      'source_run_statuses':dict(Counter(runs[articles[aid]['source_run_id']]['status']
          for aid in {x['article_id'] for x in old_typed})),
      'l1_l2_top_changes':len(top_changes),'predictive_admissions':0,
      'interpretation':'heuristic and source-clock diagnostic only; no revised-context gold or certified availability',
    }
    write_jsonl(OUT/'typed_pairs.jsonl',typed)
    write_jsonl(OUT/'role_changes.jsonl',role_changes)
    write_jsonl(OUT/'top_changes.jsonl',top_changes)
    write_json(OUT/'report.json',report)
    write_json(OUT/'manifest.json',{'inputs':receipt['inputs'],
        'outputs':{p.name:digest(p) for p in OUT.iterdir() if p.name!='manifest.json'}})
    print(json.dumps(report,indent=2,sort_keys=True),flush=True)

if __name__=='__main__':
    assert len(sys.argv)==2 and sys.argv[1] in ('prepare','run')
    (prepare if sys.argv[1]=='prepare' else run)()
