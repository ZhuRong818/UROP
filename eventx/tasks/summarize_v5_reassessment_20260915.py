"""Summarize bounded live probes and static algorithm audit evidence."""
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/v5/design_reassessment_20260915'
REC=ROOT/'data/v5/provenance_recovery_20260908'

def rows(path): return list(map(json.loads,path.read_text().splitlines()))

def main():
    kalshi=rows(REC/'reassessment_20260915_kalshi_quality.jsonl')
    poly=rows(REC/'reassessment_20260915_polymarket_quality.jsonl')
    old=rows(ROOT/'data/v5/unresolved_pair_enrichment_20260915/enriched_pairs.jsonl')
    ids={c['market_id'] for p in old for side in ('left','right') for c in p[side]['contracts']}
    subset=[r for r in kalshi if r['ticker'] in ids]
    recovered=rows(REC/'reassessment_20260915_recovered_rule_text.jsonl')
    timestamp=lambda s: datetime.fromisoformat(s.replace('Z','+00:00'))
    queue=rows(ROOT/'data/v5/topic_coverage_triage_20260914/topic_review_queue.jsonl')
    questions=defaultdict(list)
    for r in queue: questions[r['question']].append(r)
    ambiguous=[rs for rs in questions.values() if len({r.get('yes_sub_title') for r in rs})>1]
    requests=[]
    for p in sorted(REC.glob('reassessment_20260915_*.json')):
        if p.name.endswith('_payload.json'): continue
        r=json.loads(p.read_text()); requests.append({k:r.get(k) for k in ('name','path','http_status','status','rows','started_at','completed_at')})
    spec=json.loads((OUT/'openapi.json').read_text())
    report={'scope':'bounded current source probes and opened-history descriptive metadata; no model evaluation',
      'requests':requests,
      'kalshi':{'targeted_rows':len(kalshi),'unique_ids':len({r['ticker'] for r in kalshi}),
         'with_primary_rules':sum(bool(r['primary_rule_chars']) for r in kalshi),
         'with_secondary_rules':sum(bool(r['secondary_rule_chars']) for r in kalshi),
         'with_yes_subtitle':sum(bool(r['yes_sub_title']) for r in kalshi),
         'original_enriched_packet_ids_recovered':len(subset),
         'original_packet_ids_with_primary_rules':sum(bool(r['primary_rule_chars']) for r in subset)},
      'polymarket':{'targeted_rows':len(poly),'with_description':sum(bool(r['description_chars']) for r in poly),
         'with_subtitle':sum(bool(r['contract_subtitle']) for r in poly),
         'with_resolution_source':sum(bool(r['resolution_source']) for r in poly),
         'with_event_array':sum(r['event_container_type']=='array' for r in poly),
         'raw_token_container_types':dict(Counter(r['token_container_type'] for r in poly))},
      'recovered_rule_text':{'rows':len(recovered),'unique_events':len({r['event_ticker'] for r in recovered}),
          'with_primary_rules':sum(bool(r['rules_primary']) for r in recovered),
          'ingested_after_listed_close':sum(timestamp(r['ingest_ts'])>timestamp(r['close_time']) for r in recovered if r['close_time']),
          'historical_feature_admission':False},
      'local_inventory':{'markets':len(queue),'question_groups_with_different_yes_subtitles':len(ambiguous),
         'contracts_in_these_groups':sum(map(len,ambiguous))},
      'rest_news_latest_parameters':[p['name'] for p in spec['paths']['/news/latest']['get']['parameters']],
      'rest_news_latest_limit_max':next(p['schema']['maximum'] for p in spec['paths']['/news/latest']['get']['parameters'] if p['name']=='limit'),
      'sample_is_representative':False,'rules_semantics_validated':False,
      'historical_versions_certified':False,'news_quality_rows_recovered':0,
      'outcomes_accessed':False,'protected_holdouts_touched':False,'models_fitted':0}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
