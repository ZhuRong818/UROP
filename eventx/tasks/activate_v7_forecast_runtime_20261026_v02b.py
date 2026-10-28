"""Create the immutable V02b activation receipt (separately versioned continuation of V02; see the v02b module)."""
import json

from eventx.v7 import forecast_runtime_20261026_v02b as b
from eventx.v7 import forecast_runtime_20261026_v02 as rt
from eventx.v7.clock_bounded_quote_inputs_20261026 import CONTRACT


def main():
    rt.verify_release()
    path = b.BASE/'activation_receipt.json'
    if path.exists():
        raise RuntimeError('Activation receipt already exists')
    report = b.V02_BASE/'readiness_audit/report.json'
    rt.v01.verify_manifest(b.V02_BASE/'readiness_audit/manifest.json')
    if not json.loads(report.read_text())['passed']:
        raise RuntimeError('Readiness failed; activation blocked')
    if (b.V02_BASE/'evaluation').exists():
        raise RuntimeError('V02 outcomes already evaluated; V02b would no longer be pre-outcome')
    rt.now.state_path = None
    at = rt.now()
    receipt = {'activated_epoch': at, **b.window(at), 'activated_at': rt.iso(at), 'input_contract': CONTRACT,
               'implementation_sha256': rt.sha(rt.REL/'implementation_manifest.json'), 'model_sha256': rt.sha(rt.MODEL),
               'cohort_sha256': rt.sha(rt.COHORT), 'protocol_sha256': rt.sha(rt.PROTOCOL), 'readiness_sha256': rt.sha(report),
               'v02b_implementation_sha256': rt.sha(b.REL/'implementation_manifest.json'),
               'continues': str(b.V02_BASE.relative_to(rt.REPO_ROOT)),
               'source_path': str((b.BASE/'prospective/source').relative_to(rt.REPO_ROOT))}
    b.require_activation(receipt, at)
    rt.v01.write_new(path, receipt)
    print(json.dumps({**receipt, 'first_grid_at': rt.iso(receipt['first_grid']), 'last_grid_at': rt.iso(receipt['last_grid']),
                      'open_after_at': rt.iso(receipt['open_after'])}, indent=1))


if __name__ == '__main__':
    main()
