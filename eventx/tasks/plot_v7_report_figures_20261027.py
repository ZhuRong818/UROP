"""Report figures from completed, frozen quote-change evaluations (no new scoring or fitting)."""
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pyarrow.parquet as pq

from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT

OUT = REPO_ROOT / 'docs/figures'
BOOSTER, LOGIT = '#2a78d6', '#eb6834'
INK, MUTED, GRID, SURFACE = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'


def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def load(path):
    return json.loads((REPO_ROOT / path).read_text())


def ladder():
    june = load('data/v7/june_replication_20261026/bootstrap.json')
    new = load('data/v7/new_identity_test_20261026_recovered/evaluation/result.json')
    v03 = load('data/v7/new_identity_test_20261026_recovered/evaluation_v03/result.json')
    rows = [('June 1–7\nsame cohort (18)', june_dev(june)),
            ('June 8–14\nnew contracts (35)', new['bootstrap']['activity_logit']['by_contract']),
            ('June 8–14, live model\nnew contracts (35)', v03['bootstrap_vs_hgb7']['full_logit']['by_contract'])]
    fig, ax = plt.subplots(figsize=(7, 3.2), facecolor=SURFACE)
    style(ax)
    ax.grid(axis='y', visible=False)
    for i, (label, b) in enumerate(rows):
        lo, hi = b['ci95']
        ax.plot([lo, hi], [i, i], color=BOOSTER, linewidth=2, solid_capstyle='round')
        ax.plot(b['mean'], i, 'o', color=BOOSTER, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
        ax.annotate(f"{b['mean']:.3f}  [{lo:.3f}, {hi:.3f}]", (hi, i), xytext=(8, 0), textcoords='offset points',
                    va='center', fontsize=9, color=INK)
    ax.axvline(0, color=MUTED, linewidth=1)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=9, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(-0.01, 0.21)
    ax.set_xlabel('Log-loss gain over logistic (nats per forecast), 95% contract-clustered CI', fontsize=9, color=MUTED)
    ax.set_title('Frozen booster vs logistic baseline on unopened June blocks', fontsize=11, color=INK, loc='left')
    fig.tight_layout()
    fig.savefig(OUT / 'fig1_evidence_ladder.png', dpi=200)


def june_dev(boot):
    return boot['cohorts']['development50']['activity_logit']['by_contract']


def calibration():
    t = pq.read_table(REPO_ROOT / 'data/v7/new_identity_test_20261026_recovered/evaluation/issued_predictions.parquet').to_pydict()
    known = np.asarray(t['endpoint_eligible'], dtype=bool)
    y = np.asarray([v or 0 for v in t['target']])[known]
    fig, ax = plt.subplots(figsize=(4.6, 4.4), facecolor=SURFACE)
    style(ax)
    ax.plot([0, 1], [0, 1], color=MUTED, linewidth=1, linestyle=(0, (3, 3)))
    for name, label, color in [('row_hgb7', 'Booster', BOOSTER), ('activity_logit', 'Logistic', LOGIT)]:
        p = np.asarray(t[name])[known]
        edges = np.quantile(p, np.linspace(0, 1, 11))
        k = np.clip(np.searchsorted(edges, p, side='right') - 1, 0, 9)
        mp = [p[k == i].mean() for i in range(10)]
        ob = [y[k == i].mean() for i in range(10)]
        ax.plot(mp, ob, '-o', color=color, linewidth=2, markersize=6, markeredgecolor=SURFACE, markeredgewidth=1.5, label=label)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel('Mean forecast probability (decile bins)', fontsize=9, color=MUTED)
    ax.set_ylabel('Observed share with a midpoint change', fontsize=9, color=MUTED)
    ax.set_title('Calibration, June 8–14 new contracts', fontsize=11, color=INK, loc='left')
    ax.legend(frameon=False, fontsize=9, loc='upper left')
    fig.tight_layout()
    fig.savefig(OUT / 'fig2_calibration_june8_14.png', dpi=200)


def categories():
    r = load('data/v7/category_breakdown_20261027/result.json')['blocks']
    cats = sorted({c for b in r.values() for c in b}, key=lambda c: -sum(b.get(c, {}).get('known', 0) for b in r.values()))
    fig, ax = plt.subplots(figsize=(7, 3.9), facecolor=SURFACE)
    style(ax)
    ax.grid(axis='y', visible=False)
    series = [('june1_7_dev50', 'June 1–7', LOGIT, -0.15), ('june8_14_new40', 'June 8–14 (new contracts)', BOOSTER, 0.15)]
    for block, label, color, dy in series:
        for i, c in enumerate(cats):
            if c in r[block]:
                v = r[block][c]
                ax.plot(v['reduction_pct'], i + dy, 'o', color=color, markersize=8, markeredgecolor=SURFACE,
                        markeredgewidth=1.5, label=label if i == min(j for j, cc in enumerate(cats) if cc in r[block]) else None)
                ax.annotate(f"{v['contracts']}", (v['reduction_pct'], i + dy), xytext=(7, 0), textcoords='offset points',
                            va='center', fontsize=8, color=MUTED)
    ax.axvline(0, color=MUTED, linewidth=1)
    ax.set_yticks(range(len(cats)), [c.replace('_', ' / ') for c in cats], fontsize=9, color=INK)
    ax.invert_yaxis()
    ax.set_xlabel('Log-loss reduction vs logistic (%); label = contracts', fontsize=9, color=MUTED)
    ax.set_title('Booster gain by market category (descriptive)', fontsize=11, color=INK, loc='left', pad=24)
    ax.legend(frameon=False, fontsize=9, loc='lower left', bbox_to_anchor=(-0.01, 0.99), ncol=2, borderaxespad=0)
    fig.tight_layout()
    fig.savefig(OUT / 'fig3_category_breakdown.png', dpi=200)


def news_bound():
    r = load('data/v3_1_historical/news_bound_20261027/result.json')
    names = {'very_small': 'very small', 'small': 'small', 'moderate': 'moderate', 'clear': 'clear'}
    b = r['bootstrap']['brier_improvement']
    fig, ax = plt.subplots(figsize=(7, 2.8), facecolor=SURFACE)
    style(ax)
    ax.grid(axis='y', visible=False)
    scale = 1e4
    lo, hi = b['ci95']
    ax.plot([lo * scale, hi * scale], [0, 0], color=LOGIT, linewidth=3, solid_capstyle='round')
    ax.plot(r['point']['brier_improvement'] * scale, 0, 'o', color=LOGIT, markersize=9, markeredgecolor=SURFACE, markeredgewidth=2)
    ax.annotate('observed news effect, 95% market-clustered CI', (hi * scale, 0), xytext=(8, 0), textcoords='offset points',
                va='center', fontsize=9, color=INK)
    for s in r['frozen_design_sensitivity']:
        if s['name'] in names:
            v = s['brier_improvement'] * scale
            ax.plot(v, 1, 'D', color=MUTED, markersize=6)
            below = s['name'] in ('very_small', 'moderate')
            ax.annotate(f"{names[s['name']]}\npower {s['promotion_probability']['all_h1_h5']:.0%}", (v, 1),
                        xytext=(0, -10 if below else 10), textcoords='offset points', ha='center',
                        va='top' if below else 'bottom', fontsize=8, color=MUTED)
    ax.axvline(0, color=MUTED, linewidth=1)
    ax.set_yticks([0, 1], ['V3.1 development\n(4,651 markets)', 'pre-registered\neffect sizes'], fontsize=9, color=INK)
    ax.set_ylim(-0.6, 2.0)
    ax.invert_yaxis()
    ax.set_xlabel('Brier improvement from adding news counts (x 1e-4; right = news helps)', fontsize=9, color=MUTED)
    ax.set_title('Adding news: effect below zero, all positive effects excluded', fontsize=11, color=INK, loc='left')
    fig.tight_layout()
    fig.savefig(OUT / 'fig4_news_bound.png', dpi=200)


def drivers():
    r = load('data/v7/booster_drivers_20261027/result.json')
    g = sorted(r['group_permutation'].items(), key=lambda kv: kv[1]['mean_logloss_increase'])
    booster_only = set(r['features_unavailable_to_logistic'])
    fig, ax = plt.subplots(figsize=(7, 3.6), facecolor=SURFACE)
    style(ax)
    ax.grid(axis='y', visible=False)
    for i, (name, v) in enumerate(g):
        only_booster = all(f in booster_only for f in v['features'])
        color = BOOSTER if only_booster else MUTED
        ax.barh(i, v['mean_logloss_increase'], color=color, height=0.6)
        ax.annotate(f"{v['share_of_booster_gap_over_logistic']:.0%}", (max(v['mean_logloss_increase'], 0), i), xytext=(5, 0),
                    textcoords='offset points', va='center', fontsize=8, color=MUTED)
    ax.set_yticks(range(len(g)), [n.replace('_', ' ') for n, _ in g], fontsize=9, color=INK)
    ax.set_xlabel('Log-loss increase when the group is permuted (nats); label = share of booster-vs-logistic gap',
                  fontsize=8, color=MUTED)
    ax.set_title('What the frozen booster relies on (June 1–7, 16,453 forecasts)', fontsize=11, color=INK, loc='left')
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=BOOSTER, label='booster-only inputs'), Patch(color=MUTED, label='includes logistic inputs')],
              frameon=False, fontsize=8, loc='lower right')
    fig.tight_layout()
    fig.savefig(OUT / 'fig5_booster_drivers.png', dpi=200)


def reliability_june1_7():
    r = load('data/v7/booster_drivers_20261027/result.json')['reliability']
    fig, ax = plt.subplots(figsize=(4.6, 4.4), facecolor=SURFACE)
    style(ax)
    ax.plot([0, 1], [0, 1], color=MUTED, linewidth=1, linestyle=(0, (3, 3)))
    for name, label, color in [('booster', 'Booster', BOOSTER), ('logistic', 'Logistic', LOGIT)]:
        b = r[name]['bins']
        ax.plot([x['mean_prediction'] for x in b], [x['observed_rate'] for x in b], '-o', color=color, linewidth=2,
                markersize=6, markeredgecolor=SURFACE, markeredgewidth=1.5,
                label=f"{label} (ECE {r[name]['ece_equal_frequency']:.3f})")
    ax.set_xlim(0, 0.7)
    ax.set_ylim(0, 0.7)
    ax.set_xlabel('Mean forecast probability (decile bins)', fontsize=9, color=MUTED)
    ax.set_ylabel('Observed share with a midpoint change', fontsize=9, color=MUTED)
    ax.set_title('Calibration, June 1–7 (same contracts)', fontsize=11, color=INK, loc='left')
    ax.legend(frameon=False, fontsize=9, loc='upper left')
    fig.tight_layout()
    fig.savefig(OUT / 'fig6_calibration_june1_7.png', dpi=200)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ladder()
    calibration()
    categories()
    news_bound()
    drivers()
    reliability_june1_7()
    print(sorted(p.name for p in OUT.glob('fig*.png')))


if __name__ == '__main__':
    main()
