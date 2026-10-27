"""Separate snapshot/30-minute quote features; never imputes unavailable history."""
import numpy as np
from eventx.v7.quote_experiment_20261024 import QuoteTape,iso

SNAPSHOT=['midpoint','spread','log_bid_size','log_ask_size','imbalance','weighted_mid_shift','log_quote_message_age_minutes']
SHORT=SNAPSHOT+['momentum5','momentum30','volatility30']

class MemoryQuoteTape(QuoteTape):
    def features(self,cid,t):
        b=self.at(cid,'book_yes_asset_id',t);m=self.at(cid,'market_metadata',t);r=self.at(cid,'resolution_state',t)
        reasons=[]
        if b is None:reasons.append('current_book_missing_stale_or_quality_failed')
        if m is None:reasons.append('current_mapping_rules_or_active_status_unverified')
        if r is None:reasons.append('current_unresolved_status_unverified')
        if m and (m['scheduled_end'] is None or m['scheduled_end']<=t+1800):reasons.append('scheduled_terminal_not_beyond_horizon')
        if reasons:return None,reasons
        x=[b['mid'],b['spread'],np.log1p(b['bid_size']),np.log1p(b['ask_size']),b['imbalance'],b['weighted']-b['mid'],np.log1p((t-b['source_at'])/60)]
        if not np.isfinite(x).all():return None,['nonfinite_features']
        result={'snapshot_features':list(map(float,x)),'short_features':None,'midpoint':b['mid'],'weighted_midpoint':b['weighted'],
            'best_bid':b['mid']-b['spread']/2,'best_ask':b['mid']+b['spread']/2,'spread':b['spread'],
            'latest_book_available_at':iso(b['at']),'latest_book_source_at':iso(b['source_at']),
            'input_payload_hashes':sorted({z['payload_sha256'] for z in [b,m,r]}),
            'short_unavailable_reasons':['incomplete_quality_30m_book_history']}
        if self.covers(cid,'book_yes_asset_id',t-1800,t):
            history=[self.at(cid,'book_yes_asset_id',u) for u in range(t-1800,t+1,60)]
            if all(z is not None for z in history):
                mids=np.array([z['mid'] for z in history]);short=x+[mids[-1]-mids[-6],mids[-1]-mids[0],np.std(np.diff(mids))]
                if np.isfinite(short).all():
                    result.update(short_features=list(map(float,short)),short_unavailable_reasons=[])
                    result['input_payload_hashes']=sorted(set(result['input_payload_hashes'])|{z['payload_sha256'] for z in history})
        return result,[]

def predict(feature,models):
    values={'persistence':feature['midpoint'],'weighted_midpoint':feature['weighted_midpoint']};ood={}
    for tier in ['snapshot','short']:
        x=feature[tier+'_features'];model=models.get(tier)
        if x is None or model is None:continue
        x=np.array(x);delta=model['intercept']+((x-model['center'])/model['scale'])@np.array(model['coefficients'])
        values[tier+'_ridge']=float(np.clip(feature['midpoint']+delta,0,1))
        ood[tier+'_ridge']=bool(np.any(x<model['training_feature_min']) or np.any(x>model['training_feature_max']))
    return values,ood
