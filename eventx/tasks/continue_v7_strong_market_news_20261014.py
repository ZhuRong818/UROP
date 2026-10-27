"""Fixed opened-data calibration and unsigned-context comparison on condition_120k.

No search, independent review assertion, model promotion or protected-data use.
"""
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,re
import numpy as np
from scipy.special import expit,logit
from scipy.optimize import minimize
from eventx.tasks.run_v5_residual_feasibility import REPO_ROOT,OOF,EVENTS,START_US,metric,point_loss,read_jsonl,sha256_file,verify_manifest
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE
from eventx.tasks.run_v7_signed_evidence_exploration_20261010 import fit_offset,predict_offset
from eventx.tasks.diagnose_v7_signed_evidence_coverage_20261012 import write_json,write_jsonl,MINUTE_US

BASE=REPO_ROOT/'data/v5/market_condition_tuning_20261012'
CONTEXT=REPO_ROOT/'data/v7/relaxed_policy_context_v04_1_20261012'
OUT=REPO_ROOT/'data/v7/strong_market_context_comparison_20261014'
PENALTY=.1

# Single assistant development review of the fixed packet, using text/evidence
# before new scores. These coarse roles do not certify link correctness or novelty.
ROLES={
 'official_statement':[1,53,61,71,74,86],
 'reported_policy_decision_or_minutes':[22,51,52,55,70,72,85,87,96],
 'attributed_forecast_or_policy_analysis':[9,10,29,44,45,49,77,81,97],
 'calendar_or_meeting_preview':[17,18,19,25,40,50,82,83,84,95],
 'market_expectation_or_reaction':[3,7,8,12,13,14,15,20,21,24,26,27,30,31,33,37,38,41,43,46,47,54,56,60,62,63,65,66,69,73,75,76,78,79,89,90,91,92,93,100],
 'peripheral_investment_or_opinion':[2,4,5,6,11,16,23,28,32,34,35,36,39,42,48,57,58,59,64,67,68,80,88,94,98],
 'prediction_market_odds_repetition':[99],
}

def review_packet():
    packet=list(read_jsonl(CONTEXT/'policy_decision_review_100.jsonl'))
    assignments={i:r for r,indices in ROLES.items() for i in indices}
    if set(assignments)!=set(range(1,101)) or sum(map(len,ROLES.values()))!=100:
        raise RuntimeError('Review role partition must cover each packet item once')
    rows=[]
    for i,r in enumerate(packet,1):
        spans=r['context']['spans'];role=assignments[i]
        flags=[]
        if 'Most Read from Bloomberg' in r['summary']:flags.append('summary_contains_sidebar')
        if re.search(r'polymarket|prediction markets?',r['headline']+' '+r['summary'],re.I):flags.append('prediction_market_reference')
        if re.search(r'FedWatch|CME|fully pric|priced in|bets?|wagers|odds',r['headline']+' '+r['summary'],re.I):flags.append('may_repeat_market_expectations')
        if re.search(r'over the past|since September 2025|late 2025',r['summary'],re.I):flags.append('past_policy_background')
        rows.append({'packet_number':i,'article_id':r['article_id'],'headline':r['headline'],'reviewer_kind':'assistant','reviewer_id':'codex_development_20261014','coarse_claim_role':role,'context_plausibility':'uncertain_or_peripheral' if role in ('peripheral_investment_or_opinion','prediction_market_odds_repetition') else 'plausible_policy_context','exact_predicate_correctness':'unreviewed','novelty':'unknown','independent_episode':'unverified','flags':flags,'evidence_span':spans[0]['text'],'rationale':'Single assistant inspection of supplied headline and policy spans. Role describes article framing; exact period/quantity applicability and new information remain unresolved.'})
    write_jsonl(OUT/'assistant_context_review_100.jsonl',rows)
    traces=list(read_jsonl(CONTEXT/'association_trace.jsonl'))
    articles={}
    for r in traces:
        if r['context']['tier']=='policy_decision_context' and r['coverage']['30']['rows']:
            articles.setdefault(r['article_id'],r)
    # Exact summary/headline duplicates only. No heuristic similarity threshold
    # or episode merge is used to inflate the independent-event claim.
    summarygroups=defaultdict(list);headgroups=defaultdict(list)
    for r in articles.values():
        headgroups[re.sub(r'\s+',' ',r['headline']).strip().lower()].append(r['article_id'])
        if r['summary'].strip():
            text=re.sub(r'\s+',' ',r['summary'].split('Most Read from Bloomberg')[0]).strip().lower()
            summarygroups[hashlib.sha256(text.encode()).hexdigest()].append(r['article_id'])
    review={'status':'single_assistant_development_review_complete','articles':len(rows),'role_counts':dict(Counter(r['coarse_claim_role'] for r in rows)),'flag_counts':dict(Counter(f for r in rows for f in r['flags'])),'plausibility_counts':dict(Counter(r['context_plausibility'] for r in rows)),'eligible_articles':len(articles),'exact_duplicate_headline_groups':[ids for ids in headgroups.values() if len(ids)>1],'exact_duplicate_summary_groups':[ids for ids in summarygroups.values() if len(ids)>1],'independent_human_reviews_completed':0,'independent_episode_count':None,'review_used_to_select_forecast_articles':False}
    write_json(OUT/'review_report.json',review)
    return traces,review

def features(oof,events,selected,traces):
    positive={r['event_index'] for r in traces if r['context']['tier']=='policy_decision_context'}
    timing=np.zeros((len(selected),3));context=np.zeros((len(selected),2))
    exposed=np.zeros(len(selected),bool);covered=np.zeros(len(selected),bool)
    contributing=defaultdict(set)
    for market in np.unique(oof['market'][selected]):
        pos=np.flatnonzero(oof['market'][selected]==market)
        a,b=np.searchsorted(events['market'],[market,market+1]);ev=events[a:b]
        grid=START_US+oof['minute'][selected[pos]].astype(np.int64)*MINUTE_US
        left=np.searchsorted(ev['timestamp_us'],grid-30*MINUTE_US,side='right');right=np.searchsorted(ev['timestamp_us'],grid,side='right')
        for p,lo,hi,t in zip(pos,left,right,grid):
            if hi<=lo:continue
            exposed[p]=True
            timing[p]=(np.log1p(hi-lo),(t-int(ev['timestamp_us'][hi-1]))/(30*MINUTE_US),np.log1p(len(np.unique(ev['publisher'][lo:hi]))))
            idx=[j for j in range(a+lo,a+hi) if j in positive]
            if idx:
                covered[p]=True;context[p]=(1.,np.log1p(len(idx)));contributing[int(oof['fold'][selected[p]])].update(idx)
    trace_lookup={r['event_index']:r for r in traces}
    return timing,context,exposed,covered,{str(f):{'articles':len({trace_lookup[i]['article_id'] for i in indices}),'associations':len(indices)} for f,indices in contributing.items()}

def calibration(y,p):
    bins=[];ece=0.
    for lo in np.arange(0,1,.1):
        mask=(p>=lo)&(p<lo+.1 if lo<.9 else p<=1)
        if not mask.any():continue
        mp=float(p[mask].mean());rate=float(y[mask].mean());n=int(mask.sum());ece+=n/len(y)*abs(mp-rate)
        bins.append({'lower':float(lo),'upper':float(min(lo+.1,1)),'rows':n,'mean_prediction':mp,'observed_event_rate':rate})
    return {'mean_prediction':float(p.mean()),'event_rate':float(y.mean()),'mean_prediction_minus_event_rate':float(p.mean()-y.mean()),'fixed_10_bin_ece':ece,'bins':bins,'scope':'descriptive calibration, not an independent validity test'}

def main():
    if OUT.exists():raise SystemExit('Existing cycle output preserved')
    verify_manifest(BASE/'manifest.json');verify_manifest(CONTEXT/'delivery_manifest.json')
    OUT.mkdir(parents=True)
    inputs=[OOF,EVENTS,BASE/'predictions.npz',CONTEXT/'association_trace.jsonl',CONTEXT/'policy_decision_review_100.jsonl',BASE/'selection_receipt.json']
    contract={'created_at':datetime.now(timezone.utc).isoformat(),'scope':'fixed opened development continuation, no search or confirmation','baseline':'selected condition_120k saved fold4/fold5 forecasts','fit_fold':4,'report_fold':5,'fold5_previously_opened':True,'penalty':PENALTY,'primary_population':'all 112616 fold5 keys; also identical article-exposed and context-covered subsets','arms':['M raw market','E exposure-only intercept and market-logit correction','T E plus 30m article count/age/publisher count','C frozen T plus gated unsigned policy-context presence/count correction'],'content_correction':'fit two gated coefficients with L2=0.1; zero effect where context absent, no refit of T','availability_and_target':'unchanged 30m availability windows and original labels','review':'single assistant coarse-role development inspection, no gold or independent accuracy; raw context rules held fixed','no_hyperparameter_search':True,'no_inference_or_promotion':True,'code_sha256':sha256_file(Path(__file__)),'inputs':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in inputs]}
    write_json(OUT/'contract.json',contract)
    traces,review=review_packet()
    print('Development review complete; contract receipted before new forecast fits',flush=True)
    oof=np.memmap(OOF,mode='r',dtype=OOF_DTYPE);events=np.memmap(EVENTS,mode='r',dtype=EVENT_DTYPE)
    selected=np.flatnonzero((oof['fold']==4)|(oof['fold']==5))
    saved=np.load(BASE/'predictions.npz',allow_pickle=False)
    oldsel=np.flatnonzero(oof['fold']>=3)
    for k in ('market','minute','fold'):
        if not np.array_equal(saved[k],oof[k][oldsel]):raise RuntimeError('key mismatch')
    baseline=np.concatenate([saved['condition_120k__fold4'],saved['condition_120k__fold5']])
    if len(baseline)!=len(selected):raise RuntimeError('baseline length')
    timing,ctx,exposed,covered,contributing=features(oof,events,selected,traces)
    f=oof['fold'][selected];y=oof['label'][selected];m=oof['market'][selected];minutes=oof['minute'][selected]
    train=(f==4)&exposed;valid=f==5
    if np.intersect1d(m[train],m[valid]).size or minutes[train].max()+30>=minutes[valid].min():raise RuntimeError('purge/group failure')
    if int(covered[(f==4)].sum())!=55 or int(covered[valid].sum())!=17:raise RuntimeError('coverage reproduction failed')
    xbase=logit(np.clip(baseline,1e-7,1-1e-7))[:,None]
    predictions={'M':baseline.copy()};fits={}
    for arm,x in [('E',xbase),('T',np.column_stack([xbase,timing]))]:
        beta,fit=fit_offset(x[train],y[train],baseline[train]);pred=baseline.copy()
        pred[exposed]=predict_offset(x[exposed],baseline[exposed],beta,fit)
        predictions[arm]=pred;fits[arm]={'coefficients':beta.tolist(),**fit}
    # Normalize the context count only on covered training rows and multiply
    # design by the presence gate, so correction is identically zero elsewhere.
    z=ctx.copy();count=ctx[train&covered,1];mean=float(count.mean());scale=float(count.std())
    if scale<1e-12:scale=1.
    z[:,1]=covered*((ctx[:,1]-mean)/scale)
    off=logit(np.clip(predictions['T'][train],1e-7,1-1e-7));d=z[train]
    def objective(beta):
        value=off+d@beta
        return float(np.mean(np.logaddexp(0,value)-y[train]*value)+.5*PENALTY*(beta@beta)),d.T@(expit(value)-y[train])/len(d)+PENALTY*beta
    fit=minimize(objective,np.zeros(2),jac=True,method='L-BFGS-B',options={'maxiter':2000,'gtol':1e-7,'ftol':1e-12})
    if not fit.success:raise RuntimeError(fit.message)
    c=predictions['T'].copy();c[covered]=expit(logit(np.clip(c[covered],1e-7,1-1e-7))+z[covered]@fit.x)
    predictions['C']=c;fits['C']={'coefficients':fit.x.tolist(),'count_mean_on_covered_training':mean,'count_scale_on_covered_training':scale,'iterations':int(fit.nit),'fit_success':bool(fit.success)}
    if not np.array_equal(c[~covered],predictions['T'][~covered]):raise RuntimeError('context changed absent rows')
    populations={}
    for name,mask in [('all_rows',valid),('article_exposed',valid&exposed),('context_covered',valid&covered)]:
        yy=y[mask];populations[name]={'rows':int(mask.sum()),'markets':len(np.unique(m[mask])),'metrics':{a:metric(yy,p[mask]) for a,p in predictions.items()},'log_loss_gain':{f'{a}_versus_{b}':float((point_loss(yy,predictions[b][mask])-point_loss(yy,predictions[a][mask])).mean()) for a,b in [('E','M'),('T','E'),('C','T'),('C','M')]}}
    report={'status':'complete','baseline':contract['baseline'],'training_rows':int(train.sum()),'training_context_rows':int((train&covered).sum()),'contributing_articles_by_fold':contributing,'populations':populations,'calibration_market_only':calibration(y[valid],baseline[valid]),'fits':fits,'review':review,'checks':{'keys_matched':True,'purge_and_market_groups':True,'context_55_17_reproduced':True,'outside_context_C_equals_T':True,'no_protected_payload_access':True,'no_search_or_promotion':True},'limits':['Post-selection opened development, not independent evidence.','Context covers only six fold5 articles/17 rows, not independent events.','Single assistant role review does not validate exact relevance or novelty.','Exposure gate uses legacy semantic routing; content contrast is conditional.','No valid confidence intervals or causal news claims.']}
    write_json(OUT/'report.json',report)
    np.savez_compressed(OUT/'predictions.npz',market=m[valid],minute=minutes[valid],label=y[valid],exposed=exposed[valid],context_covered=covered[valid],**{k:v[valid] for k,v in predictions.items()})
    for item in contract['inputs']:
        if sha256_file(REPO_ROOT/item['path'])!=item['sha256']:raise RuntimeError('input changed during run')
    if sha256_file(Path(__file__))!=contract['code_sha256']:raise RuntimeError('code changed during run')
    write_json(OUT/'manifest.json',{'artifacts':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in list(OUT.iterdir())+[Path(__file__)] if p.is_file()]})
    print(json.dumps({'training_rows':report['training_rows'],'training_context_rows':report['training_context_rows'],'populations':populations,'review':review},indent=2),flush=True)

if __name__=='__main__':main()
