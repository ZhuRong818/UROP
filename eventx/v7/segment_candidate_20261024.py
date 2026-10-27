"""Frozen hypothesis: direction-aligned momentum/imbalance gates a hurdle mean."""
import numpy as np

def forecast(features,model):
    midpoint=float(features['midpoint']);x=features.get('short_features')
    if x is None:return {'prediction':midpoint,'reference':midpoint,'segment_active':False,'reason':'short_history_unavailable','change_probability':None}
    x=np.asarray(x,float);active=bool(x[8]*x[4]>1e-12)
    if not active:return {'prediction':midpoint,'reference':midpoint,'segment_active':False,'reason':'momentum_imbalance_not_aligned','change_probability':None}
    z=(x-np.array(model['center']))/np.array(model['scale']);logits=np.array(model['coefficients'])@z+np.array(model['intercept'])
    logits-=logits.max();p=np.exp(logits);p/=p.sum();delta=float(p@np.array(model['class_mean_changes']))
    return {'prediction':float(np.clip(midpoint+delta,0,1)),'reference':midpoint,'segment_active':True,'reason':None,
        'change_probability':float(sum(v for c,v in zip(model['classes'],p) if c!=0)),
        'direction_probabilities':{str(c):float(v) for c,v in zip(model['classes'],p)},
        'outside_training_range':bool(np.any(x<model['training_feature_min']) or np.any(x>model['training_feature_max']))}
