"""Preregistered V6 development diagnostic of candidate-ID order sensitivity."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

from eventx.tasks.trial_v6_candidate_id_extraction import FIELDS, SYSTEM, question, score_case

ROOT = Path(__file__).resolve().parents[2]
PRIOR = ROOT / 'data/v6/candidate_id_extraction_trial_20260926'
MODEL = ROOT / 'data/v6/span_model_20260925'
OUT = ROOT / 'data/v6/candidate_id_order_rotation_20260926'
VERSION = 'candidate-id-order-rotation-v0.1-development-20260926'


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def verify_manifest(root: Path) -> None:
    manifest = json.loads((root / 'manifest.json').read_text())
    for relative, expected in manifest['outputs'].items():
        assert digest(root / relative) == expected, f'changed frozen output: {root / relative}'


def input_hashes() -> dict[str, str]:
    return {str(path.relative_to(ROOT)): digest(path) for path in (
        Path(__file__),
        ROOT / 'eventx/tasks/trial_v6_candidate_id_extraction.py',
        PRIOR / 'manifest.json',
        MODEL / 'manifest.json',
    )}


def rotated_case(case: dict, field: str, shift: int) -> dict:
    original = case['candidates'][field]
    n = len(original)
    rotated = [{ 'id': str(i), 'value': original[(i + shift) % n]['value'] }
               for i in range(n)]
    return {'name': case['name'], 'sentence': case['sentence'],
            'reference': case['reference'], 'candidates': {field: rotated}}


def prepare() -> None:
    assert not OUT.exists(), 'version already exists'
    verify_manifest(PRIOR)
    original = json.loads((PRIOR / 'spec.json').read_text())
    assert original['system_prompt'] == SYSTEM
    assert tuple(original['fields']) == FIELDS
    plan = []
    for case in original['cases']:
        for field in FIELDS:
            options = case['candidates'][field]
            assert len(options) == len(set(json.dumps(x['value']) for x in options))
            assert [x['id'] for x in options] == [str(i) for i in range(len(options))]
            for shift in range(len(options)):
                current = rotated_case(case, field, shift)
                assert current['candidates'][field][0]['value'] == options[shift]['value']
                assert len({current['candidates'][field][id]['value']
                            for shift2 in range(len(options))
                            for current in [rotated_case(case, field, shift2)]
                            for id in [0]}) == len(options)
                plan.append({'case': case['name'], 'field': field, 'shift': shift,
                             'candidates': current['candidates'][field],
                             'prompt': question(current, field)})
    assert len(plan) == 97, f'unexpected prompt count: {len(plan)}'
    assert len({(p['case'], p['field'], p['shift']) for p in plan}) == len(plan)
    OUT.mkdir(parents=True)
    spec = {
        'version': VERSION, 'status': 'known_development_regression_not_independent_gold',
        'prior_spec_sha256': digest(PRIOR / 'spec.json'),
        'model_revision': json.loads((MODEL / 'manifest.json').read_text())['receipt']['revision'],
        'design': 'For each case and field, cyclically rotate original candidate values through every digit ID; leave sentence, field question, system prompt and selection rule unchanged.',
        'rotations': 'For n original candidates, ID i at shift k gets original value at (i+k) modulo n; k=0..n-1.',
        'plan': plan, 'fields': FIELDS, 'cases': len(original['cases']),
        'field_groups': len(original['cases']) * len(FIELDS), 'prompts': len(plan),
        'selection_rule': 'single next-token logit argmax among allowed digit IDs; tie to smallest ID',
        'scoring': ['selected ID and value counts by field', 'value invariant across all rotations per case-field',
                    'field correctness per prompt against unchanged original allowed values',
                    'source/object false and missed supported bindings per prompt',
                    'mode ID4 frequency', 'shift-zero agreement with original trial IDs and values'],
        'gate': 'diagnostic only; no promotion, real-article run, independent accuracy claim or predictive admission',
        'device': 'cpu', 'dtype': 'float32', 'torch_threads': 2, 'torch_seed': 0,
        'max_input_tokens': 2048,
    }
    write_json(OUT / 'spec.json', spec)
    receipt = {'created_at': datetime.now(timezone.utc).isoformat(),
               'inputs': input_hashes(), 'spec_sha256': digest(OUT / 'spec.json'),
               'receipt_written_before_inference': True}
    write_json(OUT / 'receipt.json', receipt)
    print(json.dumps({'prepared': True, 'prompts': len(plan),
                      'spec_sha256': receipt['spec_sha256']}, sort_keys=True), flush=True)


def run() -> None:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    assert OUT.exists(), 'prepare first'
    assert {p.name for p in OUT.iterdir()} == {'spec.json', 'receipt.json'}, 'version already run or modified'
    receipt = json.loads((OUT / 'receipt.json').read_text())
    assert receipt['receipt_written_before_inference']
    assert receipt['inputs'] == input_hashes()
    assert receipt['spec_sha256'] == digest(OUT / 'spec.json')
    verify_manifest(PRIOR)
    spec = json.loads((OUT / 'spec.json').read_text())
    assert spec['version'] == VERSION and spec['prompts'] == 97
    model_manifest = json.loads((MODEL / 'manifest.json').read_text())
    assert spec['model_revision'] == model_manifest['receipt']['revision']
    for relative, expected in model_manifest['files'].items():
        assert digest(MODEL / relative) == expected, f'changed model file: {relative}'
    prior_spec = json.loads((PRIOR / 'spec.json').read_text())
    prior_cases = {c['name']: c for c in prior_spec['cases']}
    prior_records = {name: json.loads((PRIOR / f'{name}.json').read_text())
                     for name in prior_cases}

    torch.set_num_threads(2)
    torch.manual_seed(0)
    tokenizer = AutoTokenizer.from_pretrained(MODEL / 'model', local_files_only=True)
    for digit in range(5):
        assert len(tokenizer.encode(str(digit), add_special_tokens=False)) == 1
    model = AutoModelForCausalLM.from_pretrained(
        MODEL / 'model', local_files_only=True, dtype=torch.float32,
        attn_implementation='eager').eval()
    records = []
    for index, item in enumerate(spec['plan']):
        case = prior_cases[item['case']]
        current = rotated_case(case, item['field'], item['shift'])
        assert item['candidates'] == current['candidates'][item['field']]
        assert item['prompt'] == question(current, item['field'])
        prompt = tokenizer.apply_chat_template(
            [{'role': 'system', 'content': SYSTEM},
             {'role': 'user', 'content': item['prompt']}],
            tokenize=False, add_generation_prompt=True)
        tokens = tokenizer(prompt, return_tensors='pt', truncation=False)
        assert tokens['input_ids'].shape[1] < spec['max_input_tokens']
        options = item['candidates']
        token_ids = {opt['id']: tokenizer.encode(opt['id'], add_special_tokens=False)[0]
                     for opt in options}
        with torch.no_grad():
            logits = model(**tokens).logits[0, -1]
        choice = max(options, key=lambda opt: (float(logits[token_ids[opt['id']]]),
                                               -int(opt['id'])))
        reference = case['reference']
        field = item['field']
        allowed = (reference['source_allowed'] if field == 'source' else
                   reference['traded_object_allowed'] if field == 'traded_object' else
                   [reference['mode']])
        correct = choice['value'] in allowed
        record = {'case': item['case'], 'field': field, 'shift': item['shift'],
                  'sentence': case['sentence'], 'reference_allowed': allowed,
                  'candidates': options, 'prompt': prompt,
                  'candidate_token_ids': token_ids,
                  'candidate_logits': {opt['id']: float(logits[token_ids[opt['id']]])
                                       for opt in options},
                  'selected_id': choice['id'], 'selected_value': choice['value'],
                  'correct': correct, 'false_binding': field != 'mode' and
                  choice['value'] is not None and not correct,
                  'missed_supported': field != 'mode' and allowed != [None] and not correct}
        if item['shift'] == 0:
            old = prior_records[item['case']]['decisions'][field]
            record['baseline_id_match'] = choice['id'] == old['selected_id']
            record['baseline_value_match'] = choice['value'] == old['selected_value']
        records.append(record)
        if (index + 1) % 10 == 0 or index + 1 == len(spec['plan']):
            print(f'completed {index + 1}/{len(spec["plan"])}', flush=True)
    write_json(OUT / 'records.json', records)
    groups = {}
    for case in prior_cases:
        for field in FIELDS:
            rows = [r for r in records if r['case'] == case and r['field'] == field]
            groups[f'{case}:{field}'] = {
                'rotations': len(rows), 'selected_values': [r['selected_value'] for r in rows],
                'selected_ids': [r['selected_id'] for r in rows],
                'value_invariant': len({json.dumps(r['selected_value']) for r in rows}) == 1,
                'correct': sum(r['correct'] for r in rows),
            }
    report = {
        'prompts': len(records), 'field_groups': len(groups),
        'value_invariant_groups': sum(g['value_invariant'] for g in groups.values()),
        'by_field': {field: {
            'prompts': sum(r['field'] == field for r in records),
            'correct': sum(r['correct'] for r in records if r['field'] == field),
            'false_bindings': sum(r['false_binding'] for r in records if r['field'] == field),
            'missed_supported': sum(r['missed_supported'] for r in records if r['field'] == field),
            'id_counts': dict(sorted(Counter(r['selected_id'] for r in records
                                             if r['field'] == field).items())),
            'value_invariant_groups': sum(g['value_invariant'] for key, g in groups.items()
                                          if key.endswith(':' + field)),
        } for field in FIELDS},
        'mode_id4': sum(r['field'] == 'mode' and r['selected_id'] == '4' for r in records),
        'mode_prompts': sum(r['field'] == 'mode' for r in records),
        'shift_zero_id_agreement': sum(r.get('baseline_id_match', False) for r in records),
        'shift_zero_value_agreement': sum(r.get('baseline_value_match', False) for r in records),
        'shift_zero_prompts': sum(r['shift'] == 0 for r in records),
        'groups': groups, 'predictive_admissions': 0,
        'interpretation': 'known synthetic development cases; cyclic rotations only; no independent accuracy',
    }
    write_json(OUT / 'report.json', report)
    write_json(OUT / 'runtime.json', {
        'packages': {name: importlib.metadata.version(name)
                     for name in ('torch', 'transformers', 'tokenizers')},
        'device': 'cpu', 'dtype': 'float32',
        'model_revision': model_manifest['receipt']['revision']})
    write_json(OUT / 'manifest.json', {
        'inputs': receipt['inputs'],
        'outputs': {p.name: digest(p) for p in OUT.iterdir() if p.name != 'manifest.json'}})
    print(json.dumps({key: value for key, value in report.items() if key != 'groups'},
                     indent=2, sort_keys=True), flush=True)


if __name__ == '__main__':
    assert len(sys.argv) == 2 and sys.argv[1] in ('prepare', 'run')
    (prepare if sys.argv[1] == 'prepare' else run)()
