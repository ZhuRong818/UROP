"""New target and fixed learners for the frozen source-time 14-feature contract."""
from collections import defaultdict
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import log_loss, brier_score_loss, average_precision_score, roc_auc_score
from eventx.v7.clock_bounded_quote_inputs_20261026 import FEATURES, CONTRACT

NAMES = ['global_rate', 'market_rate', 'full_logit', 'hgb7']

def target_record(tape, t, current_gate=True, endpoint_gate=True):
    """A missing endpoint is unknown, never an unchanged-price negative."""
    features = tape.features(t) if current_gate else None
    endpoint = tape.at(t+1800) if features is not None and endpoint_gate else None
    return {'t': t, 'features': features, 'current_valid': features is not None,
            'current_midpoint': features[0] if features is not None else None,
            'endpoint_midpoint': endpoint['midpoint'] if endpoint is not None else None,
            'target': int(abs(endpoint['midpoint']-features[0]) > 1e-12) if endpoint is not None else None}

def fit(rows):
    x = np.asarray([r['features'] for r in rows]); y = np.asarray([r['target'] for r in rows])
    if x.shape != (len(rows), len(FEATURES)) or len(np.unique(y)) != 2:
        raise ValueError('Training requires 14 finite features and both classes')
    if not np.isfinite(x).all(): raise ValueError('Nonfinite features')
    rate = (int(y.sum())+1)/(len(y)+2)
    groups = defaultdict(list)
    for r in rows: groups[r['market_id']].append(r['target'])
    logistic = make_pipeline(StandardScaler(), LogisticRegression(C=.1, max_iter=2000, random_state=20261026))
    booster = HistGradientBoostingClassifier(max_iter=100, learning_rate=.05, max_leaf_nodes=7,
                min_samples_leaf=100, l2_regularization=10, early_stopping=False, random_state=20261026)
    logistic.fit(x,y); booster.fit(x,y)
    return {'input_contract': CONTRACT, 'features': FEATURES, 'rate': rate,
            'market_rates': {cid:(sum(v)+20*rate)/(len(v)+20) for cid,v in groups.items()},
            'full_logit': logistic, 'hgb7': booster}

def predict(bundle, rows):
    if bundle['input_contract'] != CONTRACT or bundle['features'] != FEATURES:
        raise ValueError('Incompatible input/model contract')
    x = np.asarray([r['features'] for r in rows]).reshape(-1,len(FEATURES))
    # Deliberately no access to labels or endpoint data during prediction.
    p = {'global_rate': np.full(len(rows),bundle['rate']),
         'market_rate': np.asarray([bundle['market_rates'].get(r['market_id'],bundle['rate']) for r in rows])}
    for name in ['full_logit','hgb7']:
        p[name] = bundle[name].predict_proba(x)[:,1] if len(rows) else np.array([])
    return {name:np.clip(v,1e-6,1-1e-6) for name,v in p.items()}

def metrics(y,p):
    y=np.asarray(y); p=np.asarray(p)
    return {'n':len(y),'positives':int(y.sum()),
        'log_loss':float(log_loss(y,p,labels=[0,1])) if len(y) else None,
        'brier':float(brier_score_loss(y,p)) if len(y) else None,
        'average_precision':float(average_precision_score(y,p)) if y.sum() else None,
        'roc_auc':float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None}

def paired_summary(rows,p):
    known=np.array([r['target'] is not None for r in rows]); y=np.array([r['target'] for r in rows if r['target'] is not None])
    scores={n:metrics(y,v[known]) for n,v in p.items()}
    contrasts={}
    for name in ['global_rate','market_rate','full_logit']:
        # Positive means improvement. Missing-label ranges are deterministic, not CIs.
        contrib=[]
        for i,r in enumerate(rows):
            ys=[r['target']] if r['target'] is not None else [0,1]
            gains=[(-yy*np.log(p[name][i])-(1-yy)*np.log1p(-p[name][i]))-
                   (-yy*np.log(p['hgb7'][i])-(1-yy)*np.log1p(-p['hgb7'][i])) for yy in ys]
            contrib.append((min(gains),max(gains)))
        baseline=scores[name]['log_loss']; loss=scores['hgb7']['log_loss']
        contrasts[name]={'log_loss_gain':baseline-loss if loss is not None else None,
           'relative_reduction_pct':100*(baseline-loss)/baseline if baseline else None,
           'all_issued_gain_bounds':[float(np.mean([x[k] for x in contrib])) for k in [0,1]] if contrib else None}
    return {'issued':len(rows),'known':int(known.sum()),'unknown':int((~known).sum()),'metrics':scores,'contrasts':contrasts}
