"""Correct figure footnote spacing in a new publication version."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'eventx/release/v7/pilot_20261010'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if (OUT/'figure_revision_manifest.json').exists():raise FileExistsError('Use a new version')
    records=[json.loads(x) for x in (ROOT/'data/v7/macro_pilot_20261010/source_context.jsonl').open()]
    utc=lambda x:datetime.fromisoformat(x.replace('Z','+00:00'))
    lags=[(utc(a['available_at'])-utc(a['published_at'])).total_seconds()/60 for a in records]
    plt.rcParams.update({'font.size':10,'svg.fonttype':'none'})
    fig,ax=plt.subplots(figsize=(8.5,4.9))
    ax.hist(lags,bins=np.arange(60,661,60),color='#27658b',edgecolor='white')
    ax.axvline(np.median(lags),color='#ad3b2c',linestyle='--',label=f'Median {np.median(lags):.1f} min')
    ax.set(xlabel='Publication to conservative availability (minutes)',ylabel='Sampled articles',
           title='Macro pilot: delayed system availability (30 development articles)')
    ax.legend(frameon=False)
    fig.text(.5,.02,'Publication is not verified first-public time. This sample does not establish feed completeness.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.08,1,1))
    for ext in ('png','svg','pdf'):fig.savefig(OUT/('availability_lag_v2.'+ext),dpi=180,bbox_inches='tight')
    plt.close(fig)
    s=json.loads((ROOT/'data/v7/episode_inference_screen_20261010/report.json').read_text())
    methods=[*s['candidate_passes_all_cells'],'known_dgp_oracle']
    cells=[(d,c) for d in s['spec']['calendar_days'] for c in s['spec']['cases']]
    matrix=np.array([[next(r['coverage'] for r in s['rows'] if r['days']==d and r['case']==c and r['method']==m) for d,c in cells] for m in methods])
    fig,ax=plt.subplots(figsize=(12.6,5.2))
    im=ax.imshow(matrix,vmin=.35,vmax=.96,cmap='RdYlGn',aspect='auto')
    ax.set_xticks(range(len(cells)),[f'{d} days\n'+{'independent_days':'Independent','ar_0_5':'AR .5','ar_0_9':'AR .9','regime_random_half_shift':'Regime'}[c] for d,c in cells],fontsize=8)
    ax.set_yticks(range(4),['IID episodes','Calendar clusters','Bartlett HAC, 14 days','Known-DGP oracle*'])
    for i in range(4):
        for j in range(len(cells)):ax.text(j,i,f'{100*matrix[i,j]:.1f}%',ha='center',va='center',fontsize=8)
    ax.set_title('Synthetic 95% interval coverage: 4,096 replications per DGP cell')
    fig.colorbar(im,ax=ax,label='Empirical coverage')
    fig.text(.5,.02,'*Oracle variance is unavailable on real data. Assumed noise scales; no candidate passed all declared cells.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.08,1,1))
    for ext in ('png','svg','pdf'):fig.savefig(OUT/('inference_coverage_v2.'+ext),dpi=180,bbox_inches='tight')
    plt.close(fig)
    (OUT/'PREPARATION_RESULTS_REV2.md').write_text((OUT/'PREPARATION_RESULTS.md').read_text()
        .replace('(availability_lag.png)','(availability_lag_v2.png)')
        .replace('(inference_coverage.png)','(inference_coverage_v2.png)')+
        '\nPublication revision 2 corrects figure footnote spacing only; all source and synthetic results are unchanged. Initial figure versions are preserved.\n')
    old=ROOT/'MARKET_NEWS_NEXT_STEPS_EXECUTION_20261010.md'
    new=ROOT/'MARKET_NEWS_NEXT_STEPS_EXECUTION_20261010_REV2.md'
    if new.exists():raise FileExistsError(new)
    new.write_text(old.read_text().replace('pilot_20261010/PREPARATION_RESULTS.md','pilot_20261010/PREPARATION_RESULTS_REV2.md'))
    outputs=[*sorted(OUT.glob('*_v2.*')),OUT/'PREPARATION_RESULTS_REV2.md',new]
    (OUT/'figure_revision_manifest.json').write_text(json.dumps({'role':'publication layout correction only',
        'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),OUT/'preparation_export_manifest.json']},
        'outputs':{str(p.relative_to(ROOT)):sha(p) for p in outputs},'new_forecast_evaluation':False},indent=2)+'\n')
    print(json.dumps({'report':str(new.relative_to(ROOT)),'revised_artifacts':len(outputs),'numerical_results_changed':False}))


if __name__=='__main__':main()
