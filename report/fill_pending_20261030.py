"""Read-only formatter for the three once-only results that open after the 30 Oct close-out.

It reads the stored outputs of the V02b live evaluation, the V4 confirmatory evaluation and the late-June
test, classifies each under its frozen rule, and prints table cells and reporting language for the report.
It never runs an evaluation, writes nothing under data/, and refuses to guess when an output is missing.

Classification follows the registered rules only:
  late June  PASS = lower LL than activity_logit and global_rate, Brier no higher than activity_logit, and
             contract-clustered 95% lower bound of the gain vs activity_logit > 0 (same rule for V03 vs full_logit).
  V4         positive claim supported only if all four frozen confirmatory_conditions hold.
  live V02b  no pass rule; reporting floor (>=100 known, >=20 positives, >=20 negatives) decides whether
             scores are reportable; `descriptive_improvement` is the evaluator's own descriptive flag.
Usage: python report/fill_pending_20261030.py [--late-june PATH] [--live PATH] [--v4 PATH]
(the path overrides exist only to test the formatter on already-reported outputs).
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LATE = ROOT/'data/v7/late_june_test_20261027_v2/evaluation/result.json'
LIVE = ROOT/'data/v7/forecast_runtime_20261026_v02b/evaluation/report.json'
V4 = ROOT/'data/v4/confirmatory/evaluation/result.json'
SUMMARY = ROOT/'data/close_out_20261030/summary.log'

LANGUAGE = {
    'pass': 'The frozen rule was met: {model} had lower log loss than {comp} ({a:.4f} against {b:.4f}, a {rel:.1f}% '
            'reduction), Brier no higher, and a contract-clustered 95% interval for the gain of [{lo:.3f}, {hi:.3f}] nats.',
    'fail_interval': 'The frozen rule was not met. The point estimate favoured {model} ({a:.4f} against {b:.4f}, '
                     '{rel:.1f}%), but the contract-clustered 95% interval [{lo:.3f}, {hi:.3f}] nats includes zero, '
                     'so this block does not confirm the earlier result.',
    'fail': 'The frozen rule was not met: {model} scored {a:.4f} against {b:.4f} for {comp} ({rel:.1f}%), with '
            'interval [{lo:.3f}, {hi:.3f}] nats. This is reported as a failed replication.',
    'unevaluable': 'No result is available: {why}. Under the evaluate-once rule this is reported as unevaluable, '
                   'not rerun.',
}


def load(path):
    path = Path(path)
    if not path.exists():
        return None, f'{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path} does not exist'
    failure = path.parent/'failure.json'
    if failure.exists():
        return None, 'the evaluation wrote failure.json: '+failure.read_text()[:200]
    return json.loads(path.read_text()), None


def rule(primary, ci, cand, comp):
    a, b = primary[cand]['log_loss'], primary[comp]['log_loss']
    lower = a < b and a < primary['global_rate']['log_loss'] and primary[cand]['brier'] <= primary[comp]['brier']
    verdict = 'pass' if lower and ci[0] > 0 else 'fail_interval' if lower else 'fail'
    return verdict, {'a': a, 'b': b, 'rel': 100*(b-a)/b, 'lo': ci[0], 'hi': ci[1]}


def late_june(path, v03_path=None):
    r, why = load(path)
    if r is None:
        return {'status': 'unevaluable', 'text': LANGUAGE['unevaluable'].format(why=why)}
    out = {'known': r['observed'], 'missing': r['missing_outcomes'], 'contracts': r['contributing_contracts'],
           'wins': f"{r['contracts_favoring_selected_vs_logit']}/{r['contributing_contracts']} contracts, "
                   f"{r.get('dates_favoring_selected_vs_logit')} dates",
           'bounds': r['missing_outcome_bounds']['activity_logit']}
    verdict, v = rule(r['primary'], r['bootstrap']['activity_logit']['by_contract']['ci95'], 'row_hgb7', 'activity_logit')
    out['row_hgb7'] = {'verdict': verdict, **v,
                       'text': LANGUAGE[verdict].format(model='row_hgb7', comp='activity logistic regression', **v)}
    sec = r.get('secondary_v03') or (json.loads(Path(v03_path).read_text()) if v03_path else None)
    if sec:
        verdict, v = rule(sec['primary'], sec['bootstrap_vs_hgb7']['full_logit']['by_contract']['ci95'], 'hgb7', 'full_logit')
        out['v03'] = {'verdict': verdict, **v, 'known': sec['observed'], 'contracts': sec['contributing_contracts'],
                      'text': LANGUAGE[verdict].format(model='V03 hgb7', comp='its full logistic regression', **v)}
    return out


def live(path):
    r, why = load(path)
    if r is None:
        return {'status': 'unevaluable', 'text': LANGUAGE['unevaluable'].format(why=why)}
    m, c = r['metrics'], r['contrasts']
    out = {'scheduled': r['scheduled'], 'issued_on_time': r['timely'], 'abstained_or_uncommitted': r['abstained_or_uncommitted'],
           'coverage_pct': 100*r['timely']/r['scheduled'], 'known': r['known'], 'unknown': r['unknown'],
           'positives': m['hgb7']['positives'], 'floor_met': r['minimum_reporting_passed'],
           'descriptive_improvement': r['descriptive_improvement']}
    if not r['minimum_reporting_passed']:
        out['text'] = (f"The reporting floor was not met ({r['known']} known outcomes, {m['hgb7']['positives']} positives), "
                       'so no scores are reported as a live result.')
        return out
    boot = (r.get('bootstrap_contract_clustered') or {}).get('full_logit') or {}
    ci = boot.get('ci95', [float('nan')]*2)
    out.update(hgb7=m['hgb7'], full_logit=m['full_logit'], global_rate=m['global_rate'],
               gain=c['full_logit']['log_loss_gain'], rel=c['full_logit']['relative_reduction_pct'], ci=ci,
               bounds=c['full_logit']['all_issued_gain_bounds'], clusters=boot.get('clusters'))
    sign = 'lower' if out['gain'] > 0 else 'higher'
    out['text'] = (f"Over {r['timely']:,} of {r['scheduled']:,} scheduled decisions issued on time ({out['coverage_pct']:.1f}%), "
                   f"{r['known']:,} outcomes were known. V03 hgb7 had {sign} log loss than its full logistic regression "
                   f"({m['hgb7']['log_loss']:.4f} against {m['full_logit']['log_loss']:.4f}, {out['rel']:.1f}%), "
                   f"with a contract-clustered 95% interval for the gain of [{ci[0]:.3f}, {ci[1]:.3f}] nats from "
                   f"{out['clusters']} contracts. There is no frozen pass rule for the live test; this is descriptive.")
    return out


def v4(path):
    r, why = load(path)
    if r is None:
        stopped = ''
        if SUMMARY.exists():
            ends = [l for l in SUMMARY.read_text().splitlines() if l.split()[1:2] == ['end'] and 'v4_' in l]
            failed = [l for l in ends if not l.endswith('rc=0')]
            stopped = f'; the close-out chain stopped at {failed[0].split()[2]}' if failed else ''
        return {'status': 'unevaluable', 'text': LANGUAGE['unevaluable'].format(why=why+stopped)}
    p = r['primary_price_age_le_30']
    b3, boot = p['incremental_over_b0']['b3'], p['b3_vs_b0_bootstrap']
    out = {'ll_improvement': b3['log_loss_improvement'], 'brier_improvement': b3['brier_improvement'],
           'ci': [boot['ci_95_lower'], boot.get('ci_95_upper')], 'conditions': r['confirmatory_conditions'],
           'supported': r['positive_claim_supported']}
    unmet = [k for k, ok in r['confirmatory_conditions'].items() if not ok]
    out['text'] = (f"B3 changed log loss by {b3['log_loss_improvement']:+.5f} nats per row relative to B0 (95% interval "
                   f"[{boot['ci_95_lower']:.5f}, {boot.get('ci_95_upper', float('nan')):.5f}]). "
                   + ('All four frozen conditions held, so the positive claim is supported within the frozen cohort, interval, source and model family.'
                      if out['supported'] else f"The positive claim is not supported; unmet conditions: {', '.join(unmet)}."))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--late-june', default=LATE)
    ap.add_argument('--late-june-v03', default=None, help='separate V03 result (only for testing on June 8-14)')
    ap.add_argument('--live', default=LIVE)
    ap.add_argument('--v4', default=V4)
    a = ap.parse_args()
    print(json.dumps({'late_june': late_june(a.late_june, a.late_june_v03), 'live_v02b': live(a.live), 'v4': v4(a.v4)},
                     indent=1, default=str))


if __name__ == '__main__':
    main()
