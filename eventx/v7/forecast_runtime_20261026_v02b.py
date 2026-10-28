"""V02b: separately versioned continuation of the frozen V02 runtime after the 27 Oct host outage.

The V02 source died when the host slept (04:42 UTC) and rebooted (05:16 UTC); its protocol forbids
restarting the source into the same run. V02b reuses every frozen V02 file unchanged (code, V03 model,
30-contract cohort, gates, emitter, evaluator) and changes only:
  - the run directory (data/v7/forecast_runtime_20261026_v02b), so no V02 journal is touched;
  - the window: first grid >=45 min after V02b activation (room for the 30 min transport warmup),
    last grid and evaluation time identical to V02 (29 Oct 23:25 UTC / 23:57:30 UTC).
Readiness is bound to the V02 readiness PASS, which ran on the same frozen implementation and host.
Importing this module installs these overrides into the V02 runtime module.
"""
import json
import math

from eventx.v7 import forecast_runtime_20261026_v02 as rt
from eventx.v7.clock_bounded_quote_inputs_20261026 import CONTRACT

V02_BASE = rt.BASE
V02_VERIFY_RELEASE = rt.verify_release
BASE = rt.REPO_ROOT/'data/v7/forecast_runtime_20261026_v02b'
REL = rt.REPO_ROOT/'eventx/release/v7/forecast_runtime_20261026_v02b'
LAST_GRID = 1793316300  # V02 last grid, 2026-10-29T23:25:00Z
LEAD = 2700


def window(activated):
    first = int(math.ceil((activated+LEAD)/300))*300
    return {'first_grid': first, 'last_grid': LAST_GRID, 'open_after': LAST_GRID+1920}


def verify_release():
    V02_VERIFY_RELEASE()
    rt.v01.verify_manifest(REL/'implementation_manifest.json')


def verify_readiness_binding():
    saved = rt.BASE
    rt.BASE = V02_BASE  # the V02 binding check reads the V02 readiness capture
    try:
        rt.V02_VERIFY_READINESS_BINDING()
    finally:
        rt.BASE = saved


def require_activation(receipt, at):
    expected = window(receipt['activated_epoch'])
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise RuntimeError('Invalid V02b window')
    if receipt['activated_epoch'] >= receipt['first_grid'] or at < receipt['activated_epoch']:
        raise RuntimeError('Activation clock invalid')
    if receipt.get('input_contract') != CONTRACT:
        raise RuntimeError('Activation input mismatch')
    for key, path in [('implementation_sha256', rt.REL/'implementation_manifest.json'), ('model_sha256', rt.MODEL),
                      ('cohort_sha256', rt.COHORT), ('protocol_sha256', rt.PROTOCOL),
                      ('v02b_implementation_sha256', REL/'implementation_manifest.json')]:
        if receipt.get(key) != rt.sha(path):
            raise RuntimeError('Activation hash mismatch: '+key)
    ready = V02_BASE/'readiness_audit/report.json'
    rt.v01.verify_manifest(V02_BASE/'readiness_audit/manifest.json')
    verify_readiness_binding()
    if receipt.get('readiness_sha256') != rt.sha(ready) or not json.loads(ready.read_text())['passed']:
        raise RuntimeError('Readiness missing or failed')
    if receipt['activated_epoch'] < rt.stamp(json.loads(ready.read_text())['completed_at']):
        raise RuntimeError('Activation predates readiness')
    if receipt.get('source_path') != str((BASE/'prospective/source').relative_to(rt.REPO_ROOT)):
        raise RuntimeError('Source path mismatch')
    return expected


if not hasattr(rt, 'V02_VERIFY_READINESS_BINDING'):
    rt.V02_VERIFY_READINESS_BINDING = rt.verify_readiness_binding
rt.BASE, rt.window, rt.verify_release, rt.require_activation = BASE, window, verify_release, require_activation
rt.verify_readiness_binding = verify_readiness_binding
