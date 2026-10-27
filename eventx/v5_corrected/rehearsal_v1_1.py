"""Synthetic-only one-shot/manifest rehearsal, NOT a production admission runner."""

import hashlib
import json
from pathlib import Path


REQUIRED_EVIDENCE = ('source_versions', 'news_completeness', 'family_review',
                     'split_ledger', 'uncertainty_validation', 'full_hierarchy_power',
                     'target_adapter', 'model_bundle')


def verify_evidence(root, entries):
    """Integrity check only: matching hashes do not prove scientific certification."""
    root = Path(root).resolve()
    if set(entries) != set(REQUIRED_EVIDENCE):
        raise ValueError('All required evidence roles must be specified')
    for role, entry in entries.items():
        path = (root/entry['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f'Missing/out-of-root evidence: {role}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f'Evidence hash mismatch: {role}')
    return True


def synthetic_once(directory, *, synthetic, evidence, approved, load_labels, evaluate):
    """Receipt precedes callback; failure consumes synthetic attempt; no real mode.

    Directory must contain a SYNTHETIC_ONLY marker. Callbacks supply test data.
    `approved` cannot enable a real run. Future production authority needs its own
    reviewed scope/date/family validator and frozen runner.
    """
    root = Path(directory)
    if synthetic is not True or not (root/'SYNTHETIC_ONLY').is_file():
        raise ValueError('Only explicitly marked synthetic fixtures supported')
    if approved is not True:
        return {'status': 'incomplete', 'labels_accessed': False}
    verify_evidence(root, evidence)
    receipt = root/'attempt.json'
    with receipt.open('x') as out:
        json.dump({'synthetic': True, 'status': 'consumed_before_label_access',
                   'evidence': evidence}, out, sort_keys=True)
    try:
        result = evaluate(load_labels())
    except Exception as error:
        with (root/'failure.json').open('x') as out:
            json.dump({'synthetic': True, 'error_type': type(error).__name__}, out)
        raise
    with (root/'result.json').open('x') as out:
        json.dump(result, out)
    return result
