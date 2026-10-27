"""Add verified descriptive source records to the new development review packet."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'data/v7/macro_pilot_20261010'
OUT = ROOT / 'data/v7/macro_metadata_20261010'


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def read(p):
    return [json.loads(x) for x in p.open()]


def main():
    if (OUT / 'supplement_manifest.json').exists():
        raise FileExistsError('Supplement is append-only')
    m = json.loads((BASE/'manifest.json').read_text())
    for name,h in m['outputs'].items():
        if sha(BASE/name)!=h:
            raise ValueError('Pilot artifact changed: '+name)
    req = json.loads((OUT/'request_receipt.json').read_text())
    metadata, inputs, counts = {}, {}, []
    for b in req['batches']:
        rp = ROOT/'data/v5/provenance_recovery_20260908'/('v7_macro_'+b['name']+'_20261010.json')
        r = json.loads(rp.read_text())
        p = ROOT/r['data_path']
        if r['status']!='complete' or sha(p)!=r['data_sha256']:
            raise ValueError('Unverified metadata batch')
        rows = read(p)
        key = 'ticker' if b['venue']=='kalshi' else 'condition_id'
        if len(rows)!=len(b['ids']) or {x[key] for x in rows}!=set(b['ids']):
            raise ValueError('Exact-ID/count mismatch')
        for x in rows:
            metadata[b['venue']+':contract:'+x[key]] = x
        inputs.update({str(p.relative_to(ROOT)):sha(p),str(rp.relative_to(ROOT)):sha(rp)})
        counts.append({'batch':b['name'],'returned':len(rows),'http_status':r['http_status']})
    packet = read(BASE/'packet.jsonl')
    ledger, enriched, pages = [], [], ['# Macro pilot review packet with descriptive rules','',
        'Use the fixed annotation rubric. Keep responses in new copies of the original blank forms.',
        'Rules are retrospective review evidence; historical validity is not certified.','']
    for r in packet:
        c = r['contract']; meta = metadata[c['contract_id']]
        rules = [{'field':k,'text':meta[k]} for k in ('rules_primary','rules_secondary','description') if meta.get(k)]
        extra = {**r,'rules':rules}
        enriched.append(extra)
        source_time = meta.get('ingest_ts')
        ledger.append({'pair_id':r['pair_id'],'contract_id':c['contract_id'],
            'source_ingest_ts':source_time,'source_run_id':meta.get('source_run_id'),
            'rules_present':bool(rules),'historical_validity':'unknown','active_status':'unknown',
            'retrieved_question':meta.get('title',meta.get('question')),
            'original_question':c['question'],'source_version_admitted':False})
        pages += ['## Pair '+r['pair_id'],'', 'Article '+r['article']['article_id'],'',
            r['article']['headline'] or '(missing headline)','',r['article']['summary'] or '(missing summary)',
            '', 'Contract '+c['contract_id'],'',c['question'],'','YES subtitle: '+str(c['yes_subtitle']),
            '', 'Retrospective resolution text:','']
        pages += [x['field']+': '+x['text']+'\n' for x in rules] or ['(not available)\n']
        pages += ['Earlier supplied reporting:','']
        for b in r['earlier_reports']:
            pages += ['### Earlier article '+b['article_id'],'',b['headline'] or '', '', b['summary'] or '', '']
        pages += ['---','']
    for name, rows in [('packet_with_rules',enriched),('contract_source_context',ledger)]:
        (OUT/(name+'.jsonl')).write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in rows))
    (OUT/'REVIEW_PACKET_WITH_RULES.md').write_text('\n'.join(pages))
    rule_contracts = {x['contract_id'] for x in ledger if x['rules_present']}
    report = {'status':'descriptive_rule_recovery_complete','requested_contracts':66,
        'returned_contracts':len(metadata),'contracts_with_rules':len(rule_contracts),
        'pairs_with_rules':sum(x['rules_present'] for x in ledger),'pairs':len(ledger),
        'source_batches':counts,'source_identity_and_hash_checks':'pass',
        'historical_version_or_active_status_certified':False,'predictive_admissions':0,
        'packet_ids_and_article_content_preserved':True,'independent_human_reviews_completed':0}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    inputs[str(BASE.relative_to(ROOT)/'manifest.json')]=sha(BASE/'manifest.json')
    inputs[str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__))
    (OUT/'supplement_manifest.json').write_text(json.dumps({'inputs':inputs,
        'outputs':{p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file()},'research_freeze':False},indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
