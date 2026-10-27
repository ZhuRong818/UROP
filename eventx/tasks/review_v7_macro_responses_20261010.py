"""Describe assistant review differences; do not adjudicate or create gold labels."""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/v7/macro_review_diagnostic_20261010'
FIELDS = ('applicability', 'role', 'direction', 'novelty',
          'market_odds_content', 'episode_key', 'duplicate_of', 'public_surprise')
MATERIAL = {'exact_predicate', 'material_context'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    if OUT.exists():
        raise ValueError('Preserve prior diagnostics; use a new version')
    checked = {}
    for directory, name, key in [
        ('macro_pilot_20261010', 'manifest.json', 'outputs'),
        ('macro_metadata_20261010', 'supplement_manifest.json', 'outputs'),
        ('macro_reviewer_id_correction_20261010', 'manifest.json', None),
        ('macro_review_intake_20261010_distinct_ids', 'manifest.json', None),
    ]:
        folder = ROOT / 'data/v7' / directory
        manifest = json.loads((folder / name).read_text())
        for filename, expected in (manifest[key] if key else manifest).items():
            path = folder / filename
            actual = sha(path)
            if actual != expected:
                raise ValueError('Changed input: ' + str(path))
            checked[str(path.relative_to(ROOT))] = actual
    paths = {
        'packet': ROOT / 'data/v7/macro_metadata_20261010/packet_with_rules.jsonl',
        'A': ROOT / 'data/v7/macro_reviewer_id_correction_20261010/reviewer_A_completed.jsonl',
        'B': ROOT / 'data/v7/macro_reviewer_id_correction_20261010/reviewer_B_completed.jsonl',
        'ledger': ROOT / 'data/v7/macro_pilot_20261010/selection_ledger.jsonl',
        'timing': ROOT / 'data/v7/macro_feasibility_20261010/pair_diagnostics.jsonl',
        'source': ROOT / 'data/v7/macro_pilot_20261010/source_context.jsonl',
    }
    p, a, b, ledger, timing = [
        {r['pair_id']: r for r in read(paths[k])}
        for k in ('packet', 'A', 'B', 'ledger', 'timing')]
    sources = {r['article_id']: r for r in read(paths['source'])}
    for rows in (a, b, ledger, timing):
        if set(rows) != set(p):
            raise ValueError('ID mismatch')
    intake = json.loads((ROOT / 'data/v7/macro_review_intake_20261010_distinct_ids/report.json').read_text())
    n = len(p)
    agreement = {}
    for field in FIELDS:
        count = sum(a[k][field] == b[k][field] for k in p)
        agreement[field] = {
            'agree': count, 'total': n, 'fraction': count / n,
            'A_counts': dict(Counter(a[k][field] for k in p)),
            'B_counts': dict(Counter(b[k][field] for k in p)),
        }
    groups = {
        'both_exact': [k for k in p if a[k]['applicability'] == b[k]['applicability'] == 'exact_predicate'],
        'both_material': [k for k in p if a[k]['applicability'] in MATERIAL and b[k]['applicability'] in MATERIAL],
        'either_material': [k for k in p if a[k]['applicability'] in MATERIAL or b[k]['applicability'] in MATERIAL],
        'same_signed_direction': [k for k in p if a[k]['direction'] in {'yes', 'no'} and a[k]['direction'] == b[k]['direction']],
    }
    support = {}
    for name, keys in groups.items():
        support[name] = {
            'pairs': len(keys), 'articles': len({p[k]['article']['article_id'] for k in keys}),
            'contracts': len({p[k]['contract']['contract_id'] for k in keys}),
            'pair_ids': keys,
            'full_nominal_landmark_horizon': sum(timing[k]['full_nominal_landmark_horizon'] for k in keys),
            'at_or_after_nominal_close': sum(timing[k]['at_or_after_nominal_close'] for k in keys),
            'snapshot_after_article': sum(timing[k]['snapshot_after_article'] for k in keys),
            'role_agree': sum(a[k]['role'] == b[k]['role'] for k in keys),
            'direction_agree': sum(a[k]['direction'] == b[k]['direction'] for k in keys),
        }
    strata = {}
    for stratum in sorted({r['stratum'] for r in ledger.values()}):
        keys = [k for k in p if ledger[k]['stratum'] == stratum]
        strata[stratum] = {
            'pairs': len(keys),
            'A_material': sum(a[k]['applicability'] in MATERIAL for k in keys),
            'B_material': sum(b[k]['applicability'] in MATERIAL for k in keys),
            'both_material': sum(k in groups['both_material'] for k in keys),
            'both_exact': sum(k in groups['both_exact'] for k in keys),
        }
    predicate = {}
    for tag, answers in [('A', a), ('B', b)]:
        errors = []
        count = 0
        for k, answer in answers.items():
            fields = {f: p[k]['contract'].get(f) for f in ('question', 'yes_subtitle')}
            fields.update({r['field']: r['text'] for r in p[k]['rules']})
            for component, span in answer['predicate'].items():
                if span is None:
                    continue
                count += 1
                field, start, end = span.get('field'), span.get('start'), span.get('end')
                text = fields.get(field) or ''
                if (type(start) is not int or type(end) is not int or
                        field not in fields or not 0 <= start < end <= len(text) or
                        text[start:end] != span.get('text')):
                    errors.append({'pair_id': k, 'component': component})
        predicate[tag] = {'nonnull_component_spans': count, 'invalid_spans': errors,
                          'all_components_null_pairs': sum(all(v is None for v in r['predicate'].values()) for r in answers.values())}
    cases = []
    for k in p:
        differences = [f for f in FIELDS if a[k][f] != b[k][f]]
        priority = []
        if 'applicability' in differences:
            priority.append('relevance_boundary')
        if 'direction' in differences and {a[k]['direction'], b[k]['direction']} & {'yes', 'no'}:
            priority.append('signed_direction')
        if 'market_odds_content' in differences:
            priority.append('odds_vs_expectation')
        if k in groups['both_exact']:
            priority.append('inspect_joint_exact_match')
        cases.append({'pair_id': k, 'differences': differences, 'priority_reasons': priority,
                      'packet': p[k], 'reviewer_A': a[k], 'reviewer_B': b[k],
                      'source_context': sources[p[k]['article']['article_id']],
                      'nominal_timing': timing[k], 'stratum': ledger[k]['stratum']})
    priority_cases = [r for r in cases if r['priority_reasons']]
    report = {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'status': 'descriptive_assistant_annotation_comparison_not_adjudication',
        'official_intake_status': intake['status'], 'official_intake_error_count': len(intake['errors']),
        'pairs': n, 'articles': len(sources), 'field_agreement': agreement,
        'applicability_confusion': dict(Counter(a[k]['applicability'] + ' -> ' + b[k]['applicability'] for k in p)),
        'any_field_disagreement_pairs': sum(bool(r['differences']) for r in cases),
        'material_binary_agreement': sum((a[k]['applicability'] in MATERIAL) == (b[k]['applicability'] in MATERIAL) for k in p),
        'support': support, 'strata_descriptive_counts': strata, 'predicate_completion': predicate,
        'priority_diagnostic_pairs': len(priority_cases),
        'priority_diagnostic_articles': len({r['packet']['article']['article_id'] for r in priority_cases}),
        'independently_validated_episodes': 0, 'gold_labels_created': 0, 'new_forecast_results': 0,
        'limits': ['Agreement does not estimate accuracy or predictive gain.',
                   'Class and stratum counts are unweighted descriptive counts in an enriched sample.',
                   'Episode-string differences are not verified distinct information events.',
                   'Priority cases are a diagnostic work queue, not an official adjudication packet.',
                   'Nominal timing is not historical activity/version verification.'],
        'checked_manifest_artifacts': len(checked),
        'input_hashes': {str(v.relative_to(ROOT)): sha(v) for v in paths.values()},
    }
    OUT.mkdir()
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    for name, rows in [('comparison_cases.jsonl', cases), ('priority_diagnostic_cases.jsonl', priority_cases)]:
        (OUT / name).write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows))
    (OUT / 'manifest.json').write_text(json.dumps({
        'script_sha256': sha(Path(__file__)), 'checked_inputs': checked,
        'outputs': {f.name: sha(f) for f in sorted(OUT.iterdir()) if f.is_file()},
    }, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('pairs', 'articles', 'support', 'predicate_completion',
                      'priority_diagnostic_pairs', 'priority_diagnostic_articles', 'checked_manifest_artifacts')}, indent=2))


if __name__ == '__main__':
    main()
