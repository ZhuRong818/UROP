"""Reconcile recovered windows against fixed development article clocks."""
import json
from pathlib import Path
from collections import Counter
from eventx.tasks.check_proposition_v03_development import read, digest
from eventx.v6.contracts import utc

def main():
    root=Path('data/v6/targeted_recovery_20260921')
    manifest=json.loads((root/'manifest.json').read_text())
    for n,h in manifest['outputs'].items():assert digest(root/n)==h
    receipt_path=Path('data/v5/provenance_recovery_20260908/v6_targeted_metadata_20260921.json')
    receipt=json.loads(receipt_path.read_text()); p=Path(receipt['data_path'])
    assert receipt['status']=='complete' and digest(p)==receipt['data_sha256']
    meta={r['ticker']:r for r in read(p)}
    target=json.loads((root/'fetch_targets.json').read_text())
    assert set(meta)=={r['market_id'] for r in target} and len(read(p))==40
    ap=Path('data/v6/expanded_coverage_20260919/articles.jsonl')
    am=json.loads((ap.parent/'manifest.json').read_text());assert digest(ap)==am[ap.name]
    articles={r['article_id']:r for r in read(ap)}
    rows=[]
    for pair in read(root/'overlap_pairs.jsonl'):
        mid=pair['contract_id'].removeprefix('kalshi:contract:')
        if mid not in meta:continue
        m=meta[mid];t=utc(articles[pair['article_id']]['source_clock_available_at'])
        start,end=utc(m['open_time']),utc(m['close_time'])
        assert start<end
        status='before_open' if t<start else 'at_or_after_close' if t>=end else 'within_recorded_window'
        rows.append({**pair,'recovered_window_status':status,'metadata_available_by_article':utc(m['ingest_ts'])<=t})
    report={'target_contracts':40,'matched_pairs':len(rows),'window_counts':dict(Counter(r['recovered_window_status'] for r in rows)),
        'metadata_available_by_article_pairs':sum(r['metadata_available_by_article'] for r in rows),
        'admissions':0,'scope':'Recorded retrospective windows only; not historical semantic-version certification.'}
    out=Path('data/v6/window_reconciliation_20260921');out.mkdir(exist_ok=False)
    (out/'pairs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({'inputs':{str(x):digest(x) for x in [root/'manifest.json',receipt_path,p,ap,Path(__file__)]},'outputs':{x.name:digest(x) for x in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
