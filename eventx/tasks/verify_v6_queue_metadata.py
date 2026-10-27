import json
from pathlib import Path
from eventx.tasks.check_proposition_v03_development import read,digest

def main():
    base=Path('data/v6/queue_metadata_20260921');plan=json.loads((base/'plan.json').read_text())
    summaries=[];inputs={};allrows=[]
    for b in plan['batches']:
        rp=Path('data/v5/provenance_recovery_20260908')/('v6_queue_'+b['name']+'_20260921.json')
        r=json.loads(rp.read_text());p=Path(r['data_path']);rows=read(p)
        assert r['status']=='complete' and digest(p)==r['data_sha256'] and len(rows)==r['rows'] and len(rows)<500
        key='ticker' if b['venue']=='kalshi' else 'condition_id'
        assert {x[key] for x in rows}==set(b['ids']) and len(rows)==len(b['ids'])
        summaries.append({'batch':b['name'],'requested':len(b['ids']),'returned':len(rows),
            'rules_present':sum(bool(x.get('rules_primary') or x.get('description')) for x in rows),
            'start_present':sum(bool(x.get('open_time') or x.get('start_date')) for x in rows),
            'end_present':sum(bool(x.get('close_time') or x.get('end_date')) for x in rows)})
        inputs[str(rp)]=digest(rp);inputs[str(p)]=digest(p)
    report={'queue_contracts':plan['contracts'],'reused_prior_records':plan['reuse'],'new_records':sum(x['returned'] for x in summaries),'batches':summaries,'admissions':0,'historical_version_certified':False}
    out=Path('data/v6/queue_metadata_verified_20260921');out.mkdir(exist_ok=False)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({'inputs':inputs,'outputs':{'report.json':digest(out/'report.json')}},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
