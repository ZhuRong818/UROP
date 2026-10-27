"""Create the immutable V02 activation receipt. Refuses unless the V02 readiness audit passed.

Run only on an explicit decision to start the seven-day prospective test.
"""
import json

from eventx.v7 import forecast_runtime_20261026_v02 as rt
from eventx.v7.clock_bounded_quote_inputs_20261026 import CONTRACT


def main():
    rt.verify_release()
    path = rt.BASE/'activation_receipt.json'
    if path.exists():
        raise RuntimeError('Activation receipt already exists')
    report = rt.BASE/'readiness_audit/report.json'
    rt.v01.verify_manifest(rt.BASE/'readiness_audit/manifest.json')
    if not json.loads(report.read_text())['passed']:
        raise RuntimeError('Readiness failed; activation blocked')
    rt.now.state_path = None
    at = rt.now()
    receipt = {'activated_epoch': at, **rt.window(at), 'activated_at': rt.iso(at), 'input_contract': CONTRACT,
               'implementation_sha256': rt.sha(rt.REL/'implementation_manifest.json'), 'model_sha256': rt.sha(rt.MODEL),
               'cohort_sha256': rt.sha(rt.COHORT), 'protocol_sha256': rt.sha(rt.PROTOCOL), 'readiness_sha256': rt.sha(report),
               'source_path': str((rt.BASE/'prospective/source').relative_to(rt.REPO_ROOT))}
    rt.require_activation(receipt, at)
    rt.v01.write_new(path, receipt)
    print(json.dumps({**receipt, 'first_grid_at': rt.iso(receipt['first_grid']), 'last_grid_at': rt.iso(receipt['last_grid']),
                      'open_after_at': rt.iso(receipt['open_after'])}, indent=1))


if __name__ == '__main__':
    main()
