"""State-of-the-art baseline benchmark for the quote-change forecasting task (post hoc, opened blocks only).

Requested by the user's research track on 2 Nov 2026 (local time): baselines must come from ICML / NeurIPS / ICLR papers of
the last two years, implemented on our problem where there is no direct fit. Everything below (models, versions,
configurations, training rows, evaluation rows, metrics, bootstrap) is fixed and committed before any baseline score
is computed. Each baseline is scored once; nothing is tuned on any evaluation block; no frozen EventX model, rule or
stored forecast is changed. Every evaluation block is already consumed, so this is a descriptive benchmark on opened
data, not a new confirmatory test, and it is reported whatever the sign.

Task (unchanged): at each 5-min decision grid, the probability that the observed midpoint 30 min later differs from
the current midpoint. Rows = issued, endpoint-eligible grids. Metric: mean log loss (primary), Brier, ROC AUC.

Tier A  model-class swap for the frozen booster row_hgb7. Same 18 frozen quote features, same 9,212 training rows
        (family_training_20261025_v02 development ledger, endpoint-eligible, 7-9 May). Library defaults, except that
        neural models select their best epoch by validation log loss (our metric) rather than classification error.
  A1 TabM          Gorishniy et al., ICLR 2025        pytabkit TabM_D_Classifier (tabular default config)
  A2 RealMLP       Holzmueller et al., NeurIPS 2024   pytabkit RealMLP_TD_Classifier (tabular default config)
  A3 TabICL        Qu et al., ICML 2025               tabicl, the paper checkpoint tabicl-classifier-v1-20250208, defaults
  A4 CatBoost      default; the strongest tree family in TabArena (Erickson et al., NeurIPS 2025 D&B)
  Comparators: row_hgb7, activity_logit, online contract rate (stored, unchanged).
  Evaluated on all seven opened blocks; none of them was used to train row_hgb7 or any Tier A model.

Tier B  time-series foundation model for the contract's own outcome history (the online rate's information set).
  B1 Moirai-MoE    Liu et al., ICML 2025              uni2ts Salesforce/moirai-moe-1.0-R-small, zero-shot, no fitting
        Series per contract and block: the 5-min grid of matured outcomes (1 change / 0 no change / NaN unknown). At
        decision t the context is the 288 grids ending at the last grid with t' <= t - 2,100 s (the online rate's
        maturity lag), so the forecast target is 7 grids ahead. p = mean of 100 samples, clipped to [0.001, 0.999].
        No matured outcome in context -> the stored global rate (the online rate's prior). Run in .venv-ts.
  Comparators: online contract rate, stack (stored). Evaluated on all seven opened blocks.
  Not run: Sundial (ICML 2025) and Time-MoE (ICLR 2025) ship only as Hugging Face remote code, which this host's
  sandbox does not execute; recorded as excluded, not as failed.

Tier C  end-to-end swap for the final segment-aware stack seg_hgb. Inputs: 18 quote features + logit(online rate) +
        log1p(matured history) (all the information seg_hgb's pipeline has, without the booster). Training rows = the
        six opened blocks seg_hgb was refit on (may_13_19, jun_1_7, jun_8_14, jun_15_28, jun29_jul12, jul_13_21).
  C1 TabM, C2 RealMLP (configs as Tier A). Evaluated only on jul22_aug8, the one block no seg_hgb or Tier C model saw.
  Comparators: seg_stack (seg_hgb), stack, row_hgb7, online rate.

Inference: per block, model minus comparator log loss per row; contract-clustered bootstrap 95% CI (5,000 draws,
seed 20261105) of the comparator-minus-baseline gain; contracts favouring each. Pooled Tier A/B summary = blocks won.
Seeds: models random_state 20261105. Output: data/v7/sota_baselines_20261101/{tier_a,tier_b,tier_c}/ and result.json.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v7/sota_baselines_20261101'
SEED, CONTEXT, HORIZON, LAG, SAMPLES = 20261105, 288, 7, 2100, 100
FEATURES = ['midpoint', 'logit_midpoint', 'spread', 'source_age', 'receive_age', 'hour_sin', 'hour_cos', 'log_valid_updates30',
            'valid_state_fraction30', 'delta5', 'abs_delta5', 'missing5', 'delta15', 'abs_delta15', 'missing15', 'delta30',
            'abs_delta30', 'missing30']
STORED = ['global_rate', 'activity_logit', 'row_hgb7', 'adaptive_rate', 'history']
LATER = {'jul_13_21': ROOT / 'data/v7/segment_confirm_20261101/test/evaluation/issued_predictions.parquet',
         'jul22_aug8': ROOT / 'data/v7/segment_stack_20261101/test/evaluation/issued_predictions.parquet'}
BLOCKS = ['may_13_19', 'jun_1_7', 'jun_8_14', 'jun_15_28', 'jun29_jul12', 'jul_13_21', 'jul22_aug8']
TIER_C_TRAIN = BLOCKS[:6]


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def load_block(name):
    """Issued endpoint-eligible rows with stored forecasts and the 18 frozen features (read-only)."""
    from eventx.tasks.analyze_v7_segment_replication_20261101 import DISCOVERY, REPLICATION, OUT as SEGOUT
    from eventx.tasks.analyze_v7_online_rate_replication_20261028 import load
    if name in LATER:
        k = pd.read_parquet(LATER[name])
        k = k[k.endpoint_eligible].reset_index(drop=True)
        f = pd.read_parquet(OUT / f'features_{name}.parquet')
    elif name == 'jun29_jul12':
        k = pd.read_parquet(REPLICATION[name][0] / 'evaluation/issued_predictions.parquet')
        k = k[k.endpoint_eligible].reset_index(drop=True)
        f = pd.read_parquet(SEGOUT / 'features_jul.parquet')
    else:
        base, cohort = {**DISCOVERY, **REPLICATION}[name]
        k = load(base, cohort)
        led = pd.read_parquet(base / 'evaluation/grid_ledger.parquet', columns=['market_id', 'decision_at', 'features'])
        led = led[led.features.notna()]
        f = pd.DataFrame({'market_id': led.market_id.values, 'decision_at': led.decision_at.values,
                          **{n: [x[i] for x in led.features] for i, n in enumerate(FEATURES)}})
    keep = ['market_id', 'date', 't', 'decision_at', 'target'] + STORED + [c for c in ['stack', 'seg_stack'] if c in k]
    k = k[keep].merge(f[['market_id', 'decision_at'] + FEATURES], on=['market_id', 'decision_at'], how='left',
                      validate='one_to_one')
    assert k[FEATURES].notna().all().all(), name
    k['block'] = name
    return k


def training_rows():
    led = pd.read_parquet(ROOT / 'data/v7/family_training_20261025_v02/development/grid_ledger.parquet')
    led = led[led.endpoint_eligible].reset_index(drop=True)
    assert len(led) == 9212
    return np.stack(led.features.values).astype('float32'), led.target.to_numpy(int)


def tabular(name):
    if name == 'tabm':
        from pytabkit import TabM_D_Classifier
        return TabM_D_Classifier(device='cpu', random_state=SEED, val_metric_name='cross_entropy', verbosity=0)
    if name == 'realmlp':
        from pytabkit import RealMLP_TD_Classifier
        return RealMLP_TD_Classifier(device='cpu', random_state=SEED, val_metric_name='cross_entropy', verbosity=0)
    if name == 'tabicl':
        from tabicl import TabICLClassifier
        return TabICLClassifier(checkpoint_version='tabicl-classifier-v1-20250208.ckpt', device='mps', random_state=SEED,
                                kv_cache=True)
    if name == 'catboost':
        from catboost import CatBoostClassifier
        return CatBoostClassifier(random_seed=SEED, verbose=0, thread_count=4)
    raise KeyError(name)


def predict(model, x, chunk=20000):
    return np.concatenate([model.predict_proba(x[i:i + chunk])[:, 1] for i in range(0, len(x), chunk)])


def tier_a(names):
    x, y = training_rows()
    out = OUT / 'tier_a'
    out.mkdir(parents=True, exist_ok=True)
    blocks = {b: load_block(b) for b in BLOCKS}
    for name in names:
        model = tabular(name).fit(x, y)
        for b, k in blocks.items():
            p = out / f'{name}_{b}.parquet'
            if p.exists():
                continue
            pd.DataFrame({'market_id': k.market_id, 'decision_at': k.decision_at,
                          name: predict(model, k[FEATURES].to_numpy('float32'))}).to_parquet(p)
            print(json.dumps({'tier': 'A', 'model': name, 'block': b, 'rows': len(k)}), flush=True)


def tier_c(names):
    def design(k):
        return np.c_[k[FEATURES].to_numpy(), logit(k['adaptive_rate'].to_numpy()), np.log1p(k['history'].to_numpy())].astype('float32')
    train = pd.concat([load_block(b) for b in TIER_C_TRAIN], ignore_index=True)
    test = load_block('jul22_aug8')
    out = OUT / 'tier_c'
    out.mkdir(parents=True, exist_ok=True)
    for name in names:
        model = tabular(name).fit(design(train), train['target'].to_numpy(int))
        pd.DataFrame({'market_id': test.market_id, 'decision_at': test.decision_at,
                      name: predict(model, design(test))}).to_parquet(out / f'{name}_jul22_aug8.parquet')
        print(json.dumps({'tier': 'C', 'model': name, 'train_rows': len(train), 'test_rows': len(test)}), flush=True)


def tier_b_inputs():
    """Write each block's matured-outcome series inputs (main venv); tier_b_forecast reads them in .venv-ts."""
    out = OUT / 'tier_b'
    out.mkdir(parents=True, exist_ok=True)
    for b in BLOCKS:
        k = load_block(b)
        k[['market_id', 'decision_at', 't', 'target', 'global_rate']].to_parquet(out / f'input_{b}.parquet')


def tier_b_forecast():
    import torch
    from uni2ts.model.moirai_moe import MoiraiMoEForecast, MoiraiMoEModule
    torch.manual_seed(SEED)
    model = MoiraiMoEForecast(module=MoiraiMoEModule.from_pretrained('Salesforce/moirai-moe-1.0-R-small'),
                              prediction_length=HORIZON, context_length=CONTEXT, patch_size=16, num_samples=SAMPLES,
                              target_dim=1, feat_dynamic_real_dim=0, past_feat_dynamic_real_dim=0).eval()
    out = OUT / 'tier_b'
    for b in BLOCKS:
        dest = out / f'moirai_moe_{b}.parquet'
        if dest.exists():
            continue
        k = pd.read_parquet(out / f'input_{b}.parquet')
        pred = np.full(len(k), np.nan)
        ctx, idx = [], []
        for _, g in k.groupby('market_id', sort=False):
            t0 = int(g['t'].min()) - (CONTEXT + HORIZON) * 300
            n = (int(g['t'].max()) - t0) // 300 + 1
            series = np.full(n, np.nan, dtype='float32')
            series[(g['t'].to_numpy() - t0) // 300] = g['target'].to_numpy()
            for i, t in zip(g.index.to_numpy(), g['t'].to_numpy()):
                end = (int(t) - LAG - t0) // 300 + 1  # grids with t' <= t - LAG
                c = series[end - CONTEXT:end]
                if np.isfinite(c).any():
                    ctx.append(c)
                    idx.append(i)
                else:
                    pred[i] = k.at[i, 'global_rate']
        for s in range(0, len(ctx), 512):
            c = torch.tensor(np.stack(ctx[s:s + 512]))[..., None]
            obs = torch.isfinite(c)
            with torch.no_grad():
                f = model(past_target=torch.nan_to_num(c), past_observed_target=obs,
                          past_is_pad=torch.zeros(c.shape[:2], dtype=torch.bool))
            pred[idx[s:s + 512]] = np.clip(f[:, :, HORIZON - 1].mean(1).numpy(), 1e-3, 1 - 1e-3)
        assert np.isfinite(pred).all()
        pd.DataFrame({'market_id': k.market_id, 'decision_at': k.decision_at, 'moirai_moe': pred}).to_parquet(dest)
        print(json.dumps({'tier': 'B', 'block': b, 'rows': len(k), 'fallback_rows': int(len(k) - len(idx))}), flush=True)


def metrics(y, p):
    from sklearn.metrics import roc_auc_score
    from eventx.tasks.analyze_v7_dependence_coverage_20261028 import logloss
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {'log_loss': float(logloss(y, p).mean()), 'brier': float(np.mean((p - y) ** 2)), 'roc_auc': float(roc_auc_score(y, p))}


def compare(k, base, comp, rng):
    from eventx.tasks.analyze_v7_dependence_coverage_20261028 import logloss, one_way
    y, ids = k['target'].to_numpy(float), k['market_id'].to_numpy()
    d = logloss(y, np.clip(k[comp].to_numpy(), 1e-6, 1 - 1e-6)) - logloss(y, np.clip(k[base].to_numpy(), 1e-6, 1 - 1e-6))
    return {'gain_nats': float(d.mean()), 'relative_pct': float(100 * d.mean() / logloss(y, np.clip(k[comp].to_numpy(), 1e-6, 1 - 1e-6)).mean()),
            'by_contract': one_way(d, ids, rng), 'contracts_favouring_baseline': int(sum(d[ids == c].mean() > 0 for c in set(ids))),
            'contracts': int(len(set(ids)))}


def evaluate():
    rng = np.random.default_rng(SEED)
    res = {'at': datetime.now(timezone.utc).isoformat(), 'post_hoc_on_opened_blocks': True, 'scored_once': True,
           'tiers': {'A': {}, 'B': {}, 'C': {}}}
    a_models, c_models = ['tabm', 'realmlp', 'tabicl', 'catboost'], ['tabm', 'realmlp']
    for b in BLOCKS:
        k = load_block(b)
        for m in a_models:
            k = k.merge(pd.read_parquet(OUT / f'tier_a/{m}_{b}.parquet'), on=['market_id', 'decision_at'], validate='one_to_one')
        k = k.merge(pd.read_parquet(OUT / f'tier_b/moirai_moe_{b}.parquet'), on=['market_id', 'decision_at'], validate='one_to_one')
        y = k['target'].to_numpy(float)
        res['tiers']['A'][b] = {'rows': len(k), 'metrics': {m: metrics(y, k[m].to_numpy()) for m in a_models + ['row_hgb7', 'activity_logit', 'adaptive_rate']},
                                'vs_row_hgb7': {m: compare(k, m, 'row_hgb7', rng) for m in a_models}}
        bm = ['moirai_moe', 'adaptive_rate'] + (['stack'] if 'stack' in k else [])
        res['tiers']['B'][b] = {'rows': len(k), 'metrics': {m: metrics(y, k[m].to_numpy()) for m in bm},
                                'vs_online_rate': compare(k, 'moirai_moe', 'adaptive_rate', rng)}
        if b == 'jul22_aug8':
            for m in c_models:
                k = k.merge(pd.read_parquet(OUT / f'tier_c/{m}_{b}.parquet').rename(columns={m: m + '_e2e'}),
                            on=['market_id', 'decision_at'], validate='one_to_one')
            cm = [m + '_e2e' for m in c_models]
            res['tiers']['C'][b] = {'rows': len(k), 'metrics': {m: metrics(y, k[m].to_numpy()) for m in cm + ['seg_stack', 'stack', 'row_hgb7', 'adaptive_rate']},
                                    'vs_seg_stack': {m: compare(k, m, 'seg_stack', rng) for m in cm},
                                    'vs_stack': {m: compare(k, m, 'stack', rng) for m in cm}}
    res['summary'] = {'A_blocks_baseline_beats_row_hgb7': {m: int(sum(res['tiers']['A'][b]['vs_row_hgb7'][m]['gain_nats'] > 0 for b in BLOCKS)) for m in a_models},
                      'B_blocks_moirai_beats_online_rate': int(sum(res['tiers']['B'][b]['vs_online_rate']['gain_nats'] > 0 for b in BLOCKS)),
                      'blocks': len(BLOCKS)}
    (OUT / 'result.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res['summary'], indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('phase', choices=['tier_a', 'tier_b_inputs', 'tier_b_forecast', 'tier_c', 'evaluate'])
    ap.add_argument('--models', nargs='*', default=None)
    a = ap.parse_args()
    if a.phase == 'tier_a':
        tier_a(a.models or ['tabm', 'realmlp', 'tabicl', 'catboost'])
    elif a.phase == 'tier_c':
        tier_c(a.models or ['tabm', 'realmlp'])
    else:
        {'tier_b_inputs': tier_b_inputs, 'tier_b_forecast': tier_b_forecast, 'evaluate': evaluate}[a.phase]()
