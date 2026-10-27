"""Descriptive per-category breakdown of the completed June 1-7 and June 8-14 quote-change evaluations.

Post hoc and descriptive only (guardrail D12): categories come from a fixed keyword rule on the
question text, written before per-contract scores were joined. Nothing is refit; the frozen
per-row predictions in issued_predictions.parquet are only regrouped.
"""
import json
import re

import numpy as np
import pyarrow.parquet as pq

from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT, now, write
from eventx.tasks.run_v7_new_identity_test_20261026 import clustered

OUT = REPO_ROOT / 'data/v7/category_breakdown_20261027'
# First matching rule wins; order is part of the rule.
RULES = [
    ('geopolitics', r'\b(iran|russia|putin|zelensk|ukraine|venezuela|coup|capture|hormuz|warships|ceasefire)'),
    ('finance_crypto', r'(fdv|token|bitcoin|ethereum|crypto|\buni\b|fed\b|rate cut|inflation|unemployment|usd/|crude|gold \(|gas hit|'
                       r'\(nflx\)|\(coin\)|ipo|valuation|market cap|merge|deutsche bank|credit-card|recession|gdp)'),
    ('entertainment', r'(bachelorette|survivor|anime|film|movie|gross|cannes|spider-man|perform|halftime)'),
    ('sports', r'(real madrid)'),  # club presidency, not a political office
    ('politics', r'(election|nominee|nomination|governor|senate|house seat|primary|parliament|president|pardon|attorney general|'
                 r'republican|democrat|delegate|mcconnell|runoff|seats|leadership)'),
    ('sports', r'(win on|win\?|us open|série|liga|fc\b|vs\.?|score|goal|relegat|league|cup|nba|nfl|nhl|mvp|award|trophy|f1|grand prix|serie|'
               r'premier|tour championship|t20|match|fight|cy young|world series|esports|major|draw|pro a|championship|semifinal|final\b)'),
    ('entertainment', r'(bachelorette|survivor|anime|film|movie|gross|cannes|spider-man|perform|halftime)'),
    ('tech_science', r'(ai model|openai|gemini|spacex|starship|earthquake|launch)'),
]
BLOCKS = {
    'june1_7_dev50': ('data/v7/june_replication_20261026/evaluation/issued_predictions.parquet', 'row_hgb7', 'activity_logit'),
    'june8_14_new40': ('data/v7/new_identity_test_20261026_recovered/evaluation/issued_predictions.parquet', 'row_hgb7', 'activity_logit'),
}


def category(question):
    q = question.lower()
    return next((name for name, pattern in RULES if re.search(pattern, q)), 'other')


def questions():
    old = json.loads((REPO_ROOT / 'data/v7/family_training_20261025_v02/cohort/cohorts.json').read_text())
    new = json.loads((REPO_ROOT / 'data/v7/new_identity_test_20261026/cohort/cohort.json').read_text())['new']
    return {m['market_id']: m['question'] for m in old['development50'] + old['unseen10'] + new}


def main():
    qs = questions()
    labels = {cid: category(q) for cid, q in qs.items()}
    write(OUT / 'category_labels.json', {'at': now().isoformat(), 'rules': RULES,
                                          'labels': {cid: {'category': labels[cid], 'question': qs[cid]} for cid in qs}})
    rng = np.random.default_rng(20261027)
    out = {'at': now().isoformat(), 'descriptive_post_hoc': True, 'blocks': {}}
    for block, (path, model, base) in BLOCKS.items():
        t = pq.read_table(REPO_ROOT / path).to_pydict()
        known = np.asarray(t['endpoint_eligible'], dtype=bool)
        if block == 'june1_7_dev50':  # primary population of that test is the development cohort
            cohorts = json.loads((REPO_ROOT / 'data/v7/family_training_20261025_v02/cohort/cohorts.json').read_text())
            dev = {m['market_id'] for m in cohorts['development50']}
            known &= np.isin(t['market_id'], list(dev))
        ids = np.asarray(t['market_id'])[known]
        y = np.asarray([v or 0 for v in t['target']])[known]
        loss = {n: -(y * np.log(np.asarray(t[n])[known]) + (1 - y) * np.log1p(-np.asarray(t[n])[known])) for n in (model, base)}
        cats = np.asarray([labels[c] for c in ids])
        rows = {}
        for c in sorted(set(cats)):
            m = cats == c
            gain = loss[base][m] - loss[model][m]
            per = {cid: float(gain[ids[m] == cid].mean()) for cid in set(ids[m])}
            rows[c] = {'contracts': len(per), 'known': int(m.sum()), 'positives': int(y[m].sum()),
                       'log_loss': {model: float(loss[model][m].mean()), base: float(loss[base][m].mean())},
                       'reduction_pct': float(100 * gain.mean() / loss[base][m].mean()),
                       'contracts_favoring_booster': sum(v > 0 for v in per.values()),
                       'contract_clustered_gain': clustered(gain, ids[m], rng) if len(per) >= 3 else None}
        out['blocks'][block] = rows
    write(OUT / 'result.json', out)
    for block, rows in out['blocks'].items():
        print(block)
        for c, r in rows.items():
            ci = r['contract_clustered_gain']['ci95'] if r['contract_clustered_gain'] else None
            print(f"  {c:15s} n={r['contracts']:2d} known={r['known']:6d} LL {r['log_loss']['row_hgb7']:.4f} vs {r['log_loss']['activity_logit']:.4f} "
                  f"({r['reduction_pct']:+.1f}%) wins {r['contracts_favoring_booster']}/{r['contracts']} CI {ci}")


if __name__ == '__main__':
    main()
