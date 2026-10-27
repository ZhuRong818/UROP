"""Prereceipted development-only semantic review frame; no model acceptance or gold."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import random
import sys

ROOT=Path(__file__).resolve().parents[2]
COMPARE=ROOT/'data/v6/fixed_pipeline_comparison_20260926'
DIAG=ROOT/'data/v6/source_role_diagnostic_20260926'
CARDS=ROOT/'data/v6/enriched_rule_comparison_20260921'
ARTICLES=ROOT/'data/v6/expanded_coverage_20260919'
RUNS=ROOT/'data/v5/topic_coverage_triage_20260914'
OUT=ROOT/'data/v6/context_development_review_20260927'
SEED=20260927
SAMPLE=24

def sha(path:Path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(p:Path):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def put(p:Path,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def putl(p:Path,rows):
 with p.open('w') as f:
  for x in rows:f.write(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n')
def verify():
 for base in (COMPARE,DIAG,CARDS,ARTICLES,RUNS):
  m=json.loads((base/'manifest.json').read_text())
  for n,h in m.get('outputs',m).items():assert sha(base/n)==h,(base,n)
def inputs():
 paths=[Path(__file__),COMPARE/'manifest.json',COMPARE/'spec.json',COMPARE/'pairs.jsonl',
   DIAG/'manifest.json',DIAG/'typed_pairs.jsonl',CARDS/'manifest.json',CARDS/'cards.jsonl',
   ARTICLES/'manifest.json',ARTICLES/'articles.jsonl',RUNS/'manifest.json',RUNS/'news_run_inventory.jsonl']
 return {str(p.relative_to(ROOT)):sha(p) for p in paths}
def frame():
 ids=json.loads((COMPARE/'spec.json').read_text())['article_ids']
 cards={c['contract_id']:c for c in read(CARDS/'cards.jsonl')}
 articles={a['article_id']:a for a in read(ARTICLES/'articles.jsonl')}
 candidates={(r['article_id'],r['contract_id']) for r in read(COMPARE/'pairs.jsonl')}
 typed={(r['article_id'],r['contract_id']) for r in read(DIAG/'typed_pairs.jsonl')}
 universe={(a,c) for a in ids for c in cards}
 assert len(ids)==70 and len(cards)==134 and len(universe)==9380
 assert len(candidates)==669 and len(typed)==54 and typed<=candidates
 return ids,cards,articles,candidates,typed,universe

def prepare():
 assert not OUT.exists()
 verify()
 ids,cards,articles,candidates,typed,universe=frame()
 OUT.mkdir(parents=True)
 spec={'version':'v6-context-development-review-v0.1-20260927',
  'scope':'same 70 opened development articles x 134 retrospective cards; no reserved case, protected outcome or independent audit',
  'frame_counts':{'article_ids':70,'cards':134,'universe':9380,'candidate_union':669,
                  'heuristic_typed_union':54,'candidate_abstained':615,'not_retrieved':8711},
  'selection':'census all 54 heuristic-typed pairs; uniform without replacement 24 of 615 candidate-abstained and 24 of 8711 not-retrieved pairs',
  'seed':SEED,'sample_per_non_census_stratum':SAMPLE,
  'review_blinding':'semantic packet excludes model scores, old/new statuses, selection stratum, source timing and past judgments; source context separate',
  'semantic_labels':['same_event_update','shared_mechanism_context','generic_topic_only','incompatible','unknown'],
  'applicability_labels':['direct_proposition','shared_context_only','not_applicable','unknown'],
  'claim_role_labels':['observed_action_or_measurement','attributed_report','opinion_or_forecast','quotation','unknown'],
  'settlement_evidence_labels':['yes','no','neither','unknown'],
  'inference':'development diagnostic only; no independent precision/recall, admission or audit claim',
  'source_status':'kept separate from semantic review; none certified by this packet'}
 put(OUT/'spec.json',spec)
 put(OUT/'receipt.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),
  'inputs':inputs(),'spec_sha256':sha(OUT/'spec.json'),'written_before_sampling':True})
 print(json.dumps(spec['frame_counts'],sort_keys=True))

def run():
 assert {p.name for p in OUT.iterdir()}=={'spec.json','receipt.json'}
 rec=json.loads((OUT/'receipt.json').read_text())
 assert rec['inputs']==inputs() and rec['spec_sha256']==sha(OUT/'spec.json')
 verify()
 ids,cards,articles,candidates,typed,universe=frame()
 rng=random.Random(SEED)
 abstained=sorted(candidates-typed)
 missed=sorted(universe-candidates)
 selected=[(k,'heuristic_typed') for k in sorted(typed)]
 selected += [(k,'candidate_abstained') for k in rng.sample(abstained,SAMPLE)]
 selected += [(k,'not_retrieved') for k in rng.sample(missed,SAMPLE)]
 assert len(selected)==102 and len({k for k,_ in selected})==102
 runs={x['run_id']:x for x in read(RUNS/'news_run_inventory.jsonl')}
 packet=[]; ledger=[]; source=[]
 for (aid,cid),stratum in selected:
  a,c=articles[aid],cards[cid]
  pair_id=hashlib.sha256((aid+'\0'+cid).encode()).hexdigest()[:24]
  packet.append({'pair_id':pair_id,'article_id':aid,'contract_id':cid,
   'headline':a['headline'],'summary':a.get('summary'),
   'article_content_sha256':a['content_sha256'],
   'contract_question':c['question'],'yes_subtitle':c.get('yes_subtitle'),
   'contract_rules':[{'field':r['field'],'text':r['text']} for r in c['recovered_rule_evidence']]})
  N={'heuristic_typed':54,'candidate_abstained':615,'not_retrieved':8711}[stratum]
  n={'heuristic_typed':54,'candidate_abstained':SAMPLE,'not_retrieved':SAMPLE}[stratum]
  ledger.append({'pair_id':pair_id,'article_id':aid,'contract_id':cid,'stratum':stratum,
   'stratum_population':N,'stratum_sample':n,'inclusion_probability':n/N})
  source.append({'pair_id':pair_id,'article_id':aid,'contract_id':cid,
   'article_clock':a['source_clock_available_at'],'article_historical_content_available_at':a.get('historical_content_available_at'),
   'article_source_run_id':a['source_run_id'],'article_source_run_status':runs[a['source_run_id']]['status'],
   'contract_snapshot_ingest':c['source_ingest_ts'],
   'rule_ingests':sorted({r['available_at'] for r in c['recovered_rule_evidence'] if r.get('available_at')}),
   'terminal_fields':c['terminal_fields'],'pit_certificate':c['pit_certificate'],
   'training_admissible':False})
 packet.sort(key=lambda x:x['pair_id'])
 ledger.sort(key=lambda x:x['pair_id'])
 source.sort(key=lambda x:x['pair_id'])
 response=[{'pair_id':x['pair_id'],'reviewer_id':None,'semantic_relation':None,
   'contract_applicability':None,'claim_role':None,'settlement_evidence':None,
   'article_evidence_spans':[],'contract_evidence_spans':[],
   'identity_problem':None,'uncertain_reason':None,'rationale':None} for x in packet]
 putl(OUT/'semantic_packet.jsonl',packet)
 putl(OUT/'selection_ledger.jsonl',ledger)
 putl(OUT/'source_context.jsonl',source)
 putl(OUT/'reviewer_A_blank.jsonl',response)
 putl(OUT/'reviewer_B_blank.jsonl',response)
 union_articles=sorted({aid for aid,cid in typed})
 union_contracts=sorted({cid for aid,cid in typed})
 scope={'status':'local provider attachment; NOT SENT',
  'articles':[{'article_id':aid,'content_sha256':articles[aid]['content_sha256'],
   'source_run_id':articles[aid]['source_run_id'],
   'source_run_status':runs[articles[aid]['source_run_id']]['status'],
   'source_clock':articles[aid]['source_clock_available_at']} for aid in union_articles],
  'contracts':[{'contract_id':cid,'venue':cards[cid]['venue'],
   'source_ingest_ts':cards[cid]['source_ingest_ts'],
   'rule_ingests':sorted({r['available_at'] for r in cards[cid]['recovered_rule_evidence'] if r.get('available_at')}),
   'terminal_fields':cards[cid]['terminal_fields']} for cid in union_contracts],
  'requested_proofs':['exact article headline/summary version and revision availability field',
   'exact contract question/subtitle/rules/token version and validity',
   'historical active/suspended/closed status',
   'run committed rows, retry lineage, defined feed/time completeness']}
 put(OUT/'provider_scope.json',scope)
 report={'version':'v6-context-development-review-v0.1-20260927',
  'packet_rows':len(packet),'by_stratum':{'heuristic_typed':54,'candidate_abstained':24,'not_retrieved':24},
  'distinct_articles':len({x['article_id'] for x in packet}),
  'distinct_contracts':len({x['contract_id'] for x in packet}),
  'provider_scope_articles':len(scope['articles']),'provider_scope_contracts':len(scope['contracts']),
  'human_labels':0,'predictive_admissions':0,'independent_audit':False,
  'note':'selected universe is opened retrospective 70x134, not the full news/market universe; source status is separate and uncertified'}
 put(OUT/'report.json',report)
 put(OUT/'manifest.json',{'inputs':rec['inputs'],
  'outputs':{p.name:sha(p) for p in OUT.iterdir() if p.name!='manifest.json'}})
 print(json.dumps(report,sort_keys=True))
if __name__=='__main__':
 assert len(sys.argv)==2 and sys.argv[1] in ('prepare','run')
 (prepare if sys.argv[1]=='prepare' else run)()
