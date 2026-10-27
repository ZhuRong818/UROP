"""Explain development errors without refitting or selecting new parameters."""
from collections import Counter
import json
from pathlib import Path
import numpy as np
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write
from eventx.tasks.run_v7_quote_experiment_20261024 import metric

def main():
    dev=REPO_ROOT/'data/v7/memory_quote_20261024/development';out=REPO_ROOT/'data/v7/memory_quote_20261024/error_diagnosis'
    for p,h in json.loads((dev/'manifest.json').read_text())['files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Development drift')
    out.mkdir(exist_ok=False)
    obs=[json.loads(l) for l in (dev/'observations.jsonl').read_text().splitlines()]
    pred=[json.loads(l) for l in (dev/'predictions.jsonl').read_text().splitlines()]
    distributions={};conditional={}
    for tier in ['snapshot','short']:
        distributions[tier]={}
        for split in ['training','validation']:
            rr=[r for r in obs if r['split']==split and r['target'] and r['features'][tier+'_features'] is not None]
            delta=np.array([r['target']['midpoint']-r['features']['midpoint'] for r in rr])
            distributions[tier][split]={'rows':len(rr),'changed':int((abs(delta)>1e-12).sum()),'positive':int((delta>1e-12).sum()),
                'negative':int((delta< -1e-12).sum()),'mean_delta':float(delta.mean()),'median_delta':float(np.median(delta))}
        rr=[r for r in pred if tier=='snapshot' or r['short_eligible']];conditional[tier]={}
        keys=['persistence','weighted_midpoint','snapshot_ridge']+(['short_ridge'] if tier=='short' else [])
        for changed in [False,True]:
            subset=[r for r in rr if (abs(r['target_midpoint']-r['current_midpoint'])>1e-12)==changed]
            conditional[tier]['changed' if changed else 'unchanged']={k:metric([r['target_midpoint'] for r in subset],[r['predictions'][k] for r in subset]) for k in keys} if subset else {}
    report={'at':now().isoformat(),'scope':'Post-result explanation only; no promotion or parameter change','movement_distributions':distributions,
        'outcome_conditioned_error_diagnosis':conditional,'not_eligible_subgroups':'Changed/unchanged is known only after the target; never use to select live forecasts',
        'interpretation':'Most endpoints unchanged. Nonzero learned drift adds errors on stationary quotes; differing train/validation movement rates limit extrapolation.'}
    write(out/'report.json',report);files=[out/'report.json',dev/'manifest.json',Path(__file__).resolve()]
    write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps({'movement_distributions':distributions,'short_conditional':conditional['short']},indent=2))

if __name__=='__main__':main()
