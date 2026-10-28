"""One-command reproducibility check for the final report.

1. Verifies every hash in every frozen release manifest under eventx/release/, plus the data manifests the report
   cites, and reports each mismatch or missing file (nothing is repaired or rewritten); any missing file fails.
2. Checks the 24 headline claims in report/claims.json against their canonical artifacts, and that each claim's
   printed text still appears in both report sources. Numbers not listed there are not checked.
3. Re-renders the report figures from frozen outputs and compares them with the committed PNGs.
4. With --recompute, reruns the post hoc news-bound and booster-driver analyses into a scratch directory and
   compares them with the stored results.

Read-only for every frozen artifact; never touches a holdout, consumption receipt or live collector.
Usage: python -m eventx.tasks.verify_report_reproducibility_20261027 [--recompute]
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT, now, write

OUT = REPO_ROOT / 'data/reproducibility'
FIGURES = REPO_ROOT / 'docs/figures'
CITED_DATA_MANIFESTS = [
    'data/v7/june_replication_20261026/evaluation/manifest.json',
    'data/v7/june_replication_20261026/source/capture_manifest.json',
    'data/v3_1_historical/primary/power/manifest.json',
    'data/v3_1_historical/primary/development/examples_manifest.json',
    'data/v3_1_historical/primary/holdout/evaluation_manifest.json',
    'data/v7/verified_event_ledger_20261015_v02/manifest.json',
]
# Earlier locks replaced by a documented later manifest; a mismatch there passes only if the successor holds the hash.
SUPERSEDED_BY = {
    'eventx/release/v3_1_historical_primary/holdout_implementation_manifest.json':
        'eventx/release/v3_1_historical_primary/holdout_receipt_amendment_manifest.json',
    'eventx/release/v7/forecast_runtime_20261026_v02/implementation_manifest_at_readiness.json':
        'eventx/release/v7/forecast_runtime_20261026_v02/implementation_manifest.json',
}
# (label, artifact, key path, value printed in the report, tolerance)
CLAIMS_FILE = REPO_ROOT / 'report/claims.json'  # claim -> artifact, cohort, model, comparator, printed text
REPORT_SOURCES = {'builder': REPO_ROOT / 'report/build_report.js', 'draft': REPO_ROOT / 'EVENTX_FINAL_REPORT_DRAFT_20261101.md'}


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def entries(manifest):
    """Yield (path, sha256) from every manifest layout used in this repo."""
    for value in manifest.values():
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, str) and len(item) == 64:
                    yield key, item
                elif isinstance(item, dict) and isinstance(item.get('sha256'), str):
                    yield item.get('path', key), item['sha256']
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and 'path' in item and isinstance(item.get('sha256'), str):
                    yield item['path'], item['sha256']


def resolve(name, manifest_path):
    for base in (REPO_ROOT, manifest_path.parent):
        if (base / name).is_file():
            return base / name
    return None


def verify_manifests():
    paths = sorted(REPO_ROOT.glob('eventx/release/**/*manifest*.json')) + [REPO_ROOT / p for p in CITED_DATA_MANIFESTS]
    rows, cache = [], {}
    for path in paths:
        manifest = json.loads(path.read_text())
        if not isinstance(manifest, dict):
            continue
        checked, mismatched, missing = 0, [], []
        for name, expected in entries(manifest):
            if '.' not in name and '/' not in name:  # hash fields such as protocol_sha256, not file paths
                continue
            target = resolve(name, path)
            if target is None:
                missing.append(name)
                continue
            if target not in cache:
                cache[target] = sha256(target)
            checked += 1
            if cache[target] != expected:
                mismatched.append(name)
        rows.append({'manifest': str(path.relative_to(REPO_ROOT)), 'checked': checked,
                     'mismatched': mismatched, 'missing': missing})
    for row in rows:
        successor = SUPERSEDED_BY.get(row['manifest'])
        if row['mismatched'] and successor:
            current = dict(entries(json.loads((REPO_ROOT / successor).read_text())))
            row['superseded_by'] = successor
            row['superseded_ok'] = all(current.get(n) == cache.get(REPO_ROOT / n) for n in row['mismatched'])
    return rows


def lookup(artifact, keys):
    value = json.loads((REPO_ROOT / artifact).read_text())
    for key in keys:
        value = value[key]
    return value


def check_claims():
    """Each claim's artifact value must match its printed value, and the printed text must appear in each source."""
    texts = {name: path.read_text() for name, path in REPORT_SOURCES.items()}
    rows = []
    for c in json.loads(CLAIMS_FILE.read_text()):
        try:
            value = lookup(c['artifact'], c['keys'])
            ok = abs(float(value) - c['value']) <= c['tolerance']
        except (FileNotFoundError, KeyError, IndexError, TypeError) as e:
            value, ok = f'{type(e).__name__}: {e}', False
        absent = [name for name in c['must_appear_in'] if c['printed'] not in texts[name]]
        rows.append({'claim': c['id'], 'artifact': c['artifact'], 'report_value': c['value'], 'printed': c['printed'],
                     'artifact_value': value, 'absent_from': absent, 'ok': ok and not absent})
    return rows


def rebuild_figures():
    before = {p.name: sha256(p) for p in FIGURES.glob('fig*.png')}
    with tempfile.TemporaryDirectory() as scratch:
        backup = Path(scratch) / 'figures'
        shutil.copytree(FIGURES, backup)
        run = subprocess.run([sys.executable, '-m', 'eventx.tasks.plot_v7_report_figures_20261027'], cwd=REPO_ROOT,
                             capture_output=True, text=True)
        after = {p.name: sha256(p) for p in FIGURES.glob('fig*.png')}
        changed = sorted(n for n in before.keys() | after.keys() if before.get(n) != after.get(n))  # incl. added/removed
        if changed:  # keep the committed figures; a byte change is reported, not silently adopted
            shutil.rmtree(FIGURES)
            shutil.copytree(backup, FIGURES)
    return {'returncode': run.returncode, 'stderr_tail': run.stderr[-400:], 'figures': sorted(after),
            'byte_identical': run.returncode == 0 and not changed, 'changed': changed}


def recompute():
    """Rerun the post hoc analyses into scratch copies and compare headline values."""
    out = {}
    import eventx.tasks.analyze_v3_1_news_mde_20261027 as news
    import eventx.tasks.analyze_v7_booster_drivers_20261027 as drivers
    for module, keys in [(news, ['bootstrap', 'brier_improvement', 'one_sided_95_upper']),
                         (drivers, ['permute_all_features_unavailable_to_logistic', 'mean_logloss_increase'])]:
        stored = lookup(str((module.OUT / 'result.json').relative_to(REPO_ROOT)), keys)
        with tempfile.TemporaryDirectory() as scratch:
            original, module.OUT = module.OUT, Path(scratch)
            try:
                module.main()
                fresh = json.loads((Path(scratch) / 'result.json').read_text())
            finally:
                module.OUT = original
        for key in keys:
            fresh = fresh[key]
        out[module.__name__.rsplit('.', 1)[1]] = {'stored': stored, 'recomputed': fresh, 'identical': stored == fresh}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recompute', action='store_true', help='also rerun post hoc analyses (~5 min)')
    args = parser.parse_args()
    manifests = verify_manifests()
    claims = check_claims()
    figures = rebuild_figures()
    result = {
        'at': now().isoformat(),
        'manifests': {'count': len(manifests), 'files_checked': sum(m['checked'] for m in manifests),
                      'with_mismatch': [m for m in manifests if m['mismatched'] and not m.get('superseded_ok')],
                      'superseded_locks': [m for m in manifests if m.get('superseded_ok')],
                      'with_missing': [m for m in manifests if m['missing']]},
        'claims': claims, 'figures': figures,
        'recompute': recompute() if args.recompute else 'skipped (pass --recompute)',
    }
    result['pass'] = (not result['manifests']['with_mismatch'] and not result['manifests']['with_missing']
                      and all(c['ok'] for c in claims)
                      and figures['byte_identical']
                      and (not args.recompute or all(v['identical'] for v in result['recompute'].values())))
    folder = OUT / now().strftime('%Y%m%dT%H%M%SZ')
    folder.mkdir(parents=True, exist_ok=True)
    write(folder / 'report.json', result)
    m = result['manifests']
    print(f"manifests {m['count']}, files checked {m['files_checked']}, "
          f"with mismatch {len(m['with_mismatch'])}, superseded {len(m['superseded_locks'])}, with missing {len(m['with_missing'])}")
    for c in claims:
        print(('OK  ' if c['ok'] else 'FAIL'), c['claim'], c['report_value'], '->', c['artifact_value'])
    print('figures byte-identical:', figures['byte_identical'], figures['changed'])
    if args.recompute:
        print('recompute:', json.dumps(result['recompute']))
    print('PASS' if result['pass'] else 'FAIL', folder.relative_to(REPO_ROOT) / 'report.json')
    sys.exit(0 if result['pass'] else 1)


if __name__ == '__main__':
    main()
