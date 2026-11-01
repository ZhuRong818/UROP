"""Amendment v3 of the SOTA baseline benchmark (user request, 2 Nov 2026 local: "add Sundial and Time-MoE too").

Made before any baseline score. Adds two time-series foundation models to Tier B and bounds Tier C's compute; every
v1/v2 rule not named here is unchanged. See eventx/release/v7/sota_baselines_20261101_v3/AMENDMENT.md.

Tier B2  Sundial     Liu et al., ICML 2025 (oral)   thuml/sundial-base-128m, zero-shot, MPS, 20 samples, revin
Tier B3  Time-MoE    Shi et al., ICLR 2025          Maple728/TimeMoE-50M, zero-shot, CPU float32, per-series z-score
  Both are run from a local copy of the model-hub code in .hf_remote/ (read before use: torch/transformers only, no
  I/O or network; file hashes in the v3 manifest). Same series, context (288 grids), maturity lag (2,100 s) and
  horizon (7 grids) as Moirai-MoE. Neither accepts missing values, so unknown context values are replaced by the mean
  of the observed values in that context; no observed value -> stored global rate. p = forecast at step 7 (Sundial:
  mean of 20 samples), clipped to [0.001, 0.999].
  Population: the nonoverlapping half-hour grid (rows with t mod 1,800 = 0) of all seven blocks, because Sundial
  (~0.1 s/row on MPS) and Time-MoE (~0.16 s/row on CPU) cannot score all ~510k rows before the deadline. Moirai-MoE,
  the online rate and the stack are also reported on exactly these rows.
Tier C   compute bound: TabM and RealMLP are trained on a seeded random 100,000-row subsample (seed 20261105) of the
  six-block training rows (TabM took ~800 s on 9,212 rows on this host's CPU). seg_hgb was fitted on all rows; this
  favours seg_hgb and is disclosed.
Output: tier_b/{sundial,time_moe}_{block}.parquet, tier_c/*, result_v3.json (v1 result.json is also written).
"""
import argparse
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import eventx.tasks.benchmark_v7_sota_baselines_20261101_v2  # noqa: F401  (applies the v2 TabICL override)
import eventx.tasks.benchmark_v7_sota_baselines_20261101 as v1

HUB = v1.ROOT / '.hf_remote'
TIER_C_ROWS = 100_000


def contexts(k):
    """Yield (row index, context with NaN imputed) for the nonoverlapping rows of one block; others get the fallback."""
    pred, ctx, idx = {}, [], []
    for _, g in k.groupby('market_id', sort=False):
        t0 = int(g['t'].min()) - (v1.CONTEXT + v1.HORIZON) * 300
        series = np.full((int(g['t'].max()) - t0) // 300 + 1, np.nan, dtype='float32')
        series[(g['t'].to_numpy() - t0) // 300] = g['target'].to_numpy()
        for i, t in zip(g.index.to_numpy(), g['t'].to_numpy()):
            if int(t) % 1800:
                continue
            end = (int(t) - v1.LAG - t0) // 300 + 1
            c = series[end - v1.CONTEXT:end].copy()
            ok = np.isfinite(c)
            if ok.any():
                c[~ok] = c[ok].mean()
                ctx.append(c)
                idx.append(i)
            else:
                pred[i] = float(k.at[i, 'global_rate'])
    return pred, ctx, idx


def tier_b2(names):
    import torch
    from transformers import AutoModelForCausalLM
    torch.manual_seed(v1.SEED)
    for name in names:
        dev = 'mps' if name == 'sundial' else 'cpu'
        path = HUB / ('sundial-base-128m' if name == 'sundial' else 'TimeMoE-50M')
        model = AutoModelForCausalLM.from_pretrained(path, trust_remote_code=True, torch_dtype=torch.float32).eval().to(dev)
        for b in v1.BLOCKS:
            dest = v1.OUT / f'tier_b/{name}_{b}.parquet'
            if dest.exists():
                continue
            k = pd.read_parquet(v1.OUT / f'tier_b/input_{b}.parquet')
            pred, ctx, idx = contexts(k)
            for s in range(0, len(ctx), 256):
                x = torch.tensor(np.stack(ctx[s:s + 256])).to(dev)
                with torch.no_grad():
                    if name == 'sundial':
                        f = model.generate(x, max_new_tokens=v1.HORIZON, num_samples=20, revin=True)[:, :, v1.HORIZON - 1].mean(1)
                    else:
                        mu, sd = x.mean(-1, keepdim=True), x.std(-1, keepdim=True).clamp_min(1e-6)
                        f = (model.generate((x - mu) / sd, max_new_tokens=v1.HORIZON)[:, -v1.HORIZON:] * sd + mu)[:, v1.HORIZON - 1]
                for i, p in zip(idx[s:s + 256], np.clip(f.float().cpu().numpy(), 1e-3, 1 - 1e-3)):
                    pred[i] = float(p)
            rows = sorted(pred)
            pd.DataFrame({'market_id': k.market_id.to_numpy()[rows], 'decision_at': k.decision_at.to_numpy()[rows],
                          name: [pred[i] for i in rows]}).to_parquet(dest)
            print(json.dumps({'tier': 'B2', 'model': name, 'block': b, 'rows': len(rows), 'fallback_rows': len(rows) - len(idx)}), flush=True)


def tier_c(names):
    def design(k):
        return np.c_[k[v1.FEATURES].to_numpy(), v1.logit(k['adaptive_rate'].to_numpy()), np.log1p(k['history'].to_numpy())].astype('float32')
    train = pd.concat([v1.load_block(b) for b in v1.TIER_C_TRAIN], ignore_index=True)
    train = train.iloc[np.sort(np.random.default_rng(v1.SEED).choice(len(train), TIER_C_ROWS, replace=False))]
    test = v1.load_block('jul22_aug8')
    out = v1.OUT / 'tier_c'
    out.mkdir(parents=True, exist_ok=True)
    for name in names:
        model = v1.tabular(name).fit(design(train), train['target'].to_numpy(int))
        pd.DataFrame({'market_id': test.market_id, 'decision_at': test.decision_at,
                      name: v1.predict(model, design(test))}).to_parquet(out / f'{name}_jul22_aug8.parquet')
        print(json.dumps({'tier': 'C', 'model': name, 'train_rows': len(train), 'test_rows': len(test)}), flush=True)


def evaluate():
    v1.evaluate()
    res = json.loads((v1.OUT / 'result.json').read_text())
    rng = np.random.default_rng(v1.SEED + 3)
    res['amendment'] = 'v3'
    res['tiers']['B_nonoverlap'] = {}
    for b in v1.BLOCKS:
        k = v1.load_block(b)
        k = k[k['t'] % 1800 == 0]
        for m in ['moirai_moe', 'sundial', 'time_moe']:
            k = k.merge(pd.read_parquet(v1.OUT / f'tier_b/{m}_{b}.parquet'), on=['market_id', 'decision_at'], validate='one_to_one')
        y = k['target'].to_numpy(float)
        ms = ['sundial', 'time_moe', 'moirai_moe', 'adaptive_rate'] + (['stack'] if 'stack' in k else [])
        res['tiers']['B_nonoverlap'][b] = {'rows': len(k), 'metrics': {m: v1.metrics(y, k[m].to_numpy()) for m in ms},
                                           'vs_online_rate': {m: v1.compare(k, m, 'adaptive_rate', rng) for m in ['sundial', 'time_moe', 'moirai_moe']}}
    res['summary']['B_nonoverlap_blocks_beating_online_rate'] = {
        m: int(sum(res['tiers']['B_nonoverlap'][b]['vs_online_rate'][m]['gain_nats'] > 0 for b in v1.BLOCKS)) for m in ['sundial', 'time_moe', 'moirai_moe']}
    res['at_v3'] = datetime.now(timezone.utc).isoformat()
    (v1.OUT / 'result_v3.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res['summary'], indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('phase', choices=['tier_b2', 'tier_c', 'evaluate'])
    ap.add_argument('--models', nargs='*', default=None)
    a = ap.parse_args()
    if a.phase == 'tier_b2':
        tier_b2(a.models or ['sundial', 'time_moe'])
    elif a.phase == 'tier_c':
        tier_c(a.models or ['tabm', 'realmlp'])
    else:
        evaluate()
