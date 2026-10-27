"""Fixed synthetic dependence/power screen; no observational labels or models."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import NormalDist
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
SPEC=ROOT/'eventx/release/v7/pilot_20261010/INFERENCE_SCREEN_SPEC.json'
OUT=ROOT/'data/v7/episode_inference_screen_20261010'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def wilson(k,n):
    z=NormalDist().inv_cdf(.975);p=k/n;den=1+z*z/n
    half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    center=(p+z*z/(2*n))/den
    return [float(center-half),float(center+half)]


def main():
    if OUT.exists():raise FileExistsError('Use a new screen version')
    s=json.loads(SPEC.read_text());OUT.mkdir(parents=True)
    (OUT/'receipt.json').write_text(json.dumps({'started_at':datetime.now(timezone.utc).isoformat(),
        'spec_sha256':sha(SPEC),'script_sha256':sha(Path(__file__)),
        'protected_outcomes_accessed':False,'forecast_fits':0},indent=2)+'\n')
    rng=np.random.default_rng(s['seed']);n=s['replications_per_cell'];z=NormalDist().inv_cdf(.975)
    rows=[];power=[]
    for days in s['calendar_days']:
        for case in s['cases']:
            rho={'independent_days':0.,'ar_0_5':.5,'ar_0_9':.9,'regime_random_half_shift':.5}[case]
            counts=np.minimum(rng.poisson(1.5,size=(n,days)),4)
            if np.any(counts.sum(axis=1)==0):raise ValueError('No event replicate')
            mask=np.arange(4)[None,None,:]<counts[:,:,None]
            shock=np.empty((n,days));shock[:,0]=rng.normal(0,.02,n)
            for t in range(1,days):shock[:,t]=rho*shock[:,t-1]+rng.normal(0,.02*np.sqrt(1-rho*rho),n)
            if case=='regime_random_half_shift':
                shift=rng.normal(0,.015,n)
                shock[:,:days//2]+=shift[:,None]
            episode_noise=rng.normal(0,.02,size=(n,days,4))
            values=(shock[:,:,None]+episode_noise)*mask
            total=counts.sum(axis=1);day_sum=values.sum(axis=2)
            mean=day_sum.sum(axis=1)/total
            deviations=(shock[:,:,None]+episode_noise-mean[:,None,None])*mask
            iid_var=(deviations**2).sum(axis=(1,2))/(total-1)/total
            influence=day_sum-mean[:,None]*counts
            cluster_var=(influence**2).sum(axis=1)*days/(days-1)/(total**2)
            hac_sum=(influence**2).sum(axis=1)
            for lag in range(1,min(14,days-1)+1):
                hac_sum+=2*(1-lag/15)*(influence[:,lag:]*influence[:,:-lag]).sum(axis=1)
            hac_var=np.maximum(hac_sum,0)*days/(days-1)/(total**2)
            distances=np.abs(np.arange(days)[:,None]-np.arange(days)[None,:])
            cov=.02**2*rho**distances
            oracle_var=np.einsum('bi,ij,bj->b',counts,cov,counts)/(total**2)+.02**2/total
            if case=='regime_random_half_shift':oracle_var+=(.015*counts[:,:days//2].sum(axis=1)/total)**2
            ses={'iid_episode_normal':np.sqrt(iid_var),'calendar_cluster_normal':np.sqrt(cluster_var),
                 'bartlett_hac_14_normal':np.sqrt(hac_var),'known_dgp_oracle':np.sqrt(oracle_var)}
            for method,se in ses.items():
                cover=np.abs(mean)<=z*se;type1=~cover
                ci=wilson(int(cover.sum()),n);sizeci=wilson(int(type1.sum()),n)
                passes=ci[0]>=.93 and sizeci[1]<=.07
                rows.append({'days':days,'case':case,'method':method,'replications':n,
                    'mean_simulated_episode_count':float(total.mean()),'coverage':float(cover.mean()),
                    'coverage_wilson_95':ci,'two_sided_type_I':float(type1.mean()),
                    'type_I_wilson_95':sizeci,'mean_estimated_se':float(se.mean()),'passes_declared_cell':bool(passes),
                    'mde_80_reference_nats':float((z+NormalDist().inv_cdf(.8))*np.median(se))})
                for gain in s['gains_nats'][1:]:
                    estimate=mean+gain;lower=estimate-z*se
                    power.append({'days':days,'case':case,'method':method,'true_gain':gain,
                        'lower_bound_above_zero_rate':float((lower>0).mean()),
                        'lower_positive_and_point_ge_0_001_rate':float(((lower>0)&(estimate>=.001)).mean()),
                        'power_interpretable_as_size_controlled':bool(passes)})
    candidates=s['candidates']
    adoption={m:all(r['passes_declared_cell'] for r in rows if r['method']==m) for m in candidates}
    report={'status':'candidate_screen_complete','cells':len(rows),'power_cells':len(power),
        'replications_per_cell':n,'simulation_dgp_cells':len(s['calendar_days'])*len(s['cases']),
        'candidate_passes_all_cells':adoption,'adopted_real_data_inference':None,
        'rows':rows,'power':power,'spec':s,'observational_scale_estimated':False,
        'forecast_fits':0,'protected_outcomes_accessed':False}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'manifest.json').write_text(json.dumps({'inputs':{str(SPEC.relative_to(ROOT)):sha(SPEC),
        str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},
        'outputs':{p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file()}},indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','cells','power_cells','replications_per_cell','candidate_passes_all_cells','adopted_real_data_inference')},indent=2))


if __name__=='__main__':main()
