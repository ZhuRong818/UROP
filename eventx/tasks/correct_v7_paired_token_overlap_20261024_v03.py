"""Correct signed versus unsigned cross-token overlap interpretation; retain V01."""
from collections import Counter
import json
from pathlib import Path
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write

SRC=REPO_ROOT/'data/v7/paired_token_overlap_20261024'
OUT=REPO_ROOT/'data/v7/paired_token_overlap_20261024_v03'

def main():
    for p,h in json.loads((SRC/'manifest.json').read_text())['files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('V01 hash mismatch')
    rows=[json.loads(l) for l in (SRC/'scoped_records.jsonl').read_text().splitlines()]
    old=json.loads((SRC/'report.json').read_text());sets={'yes':Counter(),'no':Counter()}
    for x in rows:
        key=(x['transaction_hash'],x['timestamp'],round(x['yes_oriented_price'],9),round(x['size'],6))
        sets[x['outcome_side']][key]+=1
    overlap=sets['yes']&sets['no'];t=__import__('datetime').datetime.fromisoformat(old['grid_at']).timestamp()
    pairs60=sum(n for key,n in overlap.items() if key[1]>t-3600)
    result={'at':now().isoformat(),'supersedes_interpretation_only':['data/v7/paired_token_overlap_20261024/report.json','data/v7/paired_token_overlap_20261024_v02/report.json'],
        'correction':'V02 numerical overlap count was8but its prose incorrectly said10; V03derives prose from computed counts. V01 correctly counted0direction-preserving pairs but incorrectly described them as identical signed signatures. Complementary BUY YES/BUY NO rows have opposite YES-oriented directions.',
        'grid_at':old['grid_at'],'market_id':old['market_id'],'question':old['question'],
        'yes_records240m':sum(sets['yes'].values()),'no_records240m':sum(sets['no'].values()),
        'same_direction_pairs240m':old['cross_token_fingerprint_pairs240m'],
        'transaction_time_size_complement_price_pairs240m':sum(overlap.values()),
        'transaction_time_size_complement_price_pairs60m':pairs60,
        'distinct_transactions240m':old['distinct_transactions240m'],
        'raw_pooled_count60':sum(x['in_last60m'] for x in rows),
        'paired_group_count60_if_collapsed':sum(x['in_last60m'] for x in rows)-pairs60,
        'conclusion':f'The one pooled screen pass counts complementary opposite-exposure records separately. {sum(overlap.values())}pairs match transaction,time,size and complemented price under the recorded rounding, including{pairs60}in the last60minutes. Explicit leg accounting is required; this does not certify a general deduplication rule.',
        'execution_identity_certified':False,'predictive_admissions':0}
    OUT.mkdir(parents=True,exist_ok=False);write(OUT/'report.json',result)
    files=list(OUT.iterdir())+[Path(__file__).resolve(),SRC/'manifest.json']
    write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
