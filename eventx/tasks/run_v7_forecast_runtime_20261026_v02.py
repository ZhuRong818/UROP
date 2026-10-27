"""V02 emitter: the frozen V01 emitter loop with V02 clock, inputs, cohort and paths.

The decision function, model and emission/endpoint receipt logic are V01's, unchanged.
Before the first grid the wrapper keeps a BoundedInputs advanced on the growing source
journal, so the first decisions are not delayed by a long catch-up read.
"""
import json
import time

from eventx.tasks import run_v7_frozen_classifier_20261026 as v01_emitter
from eventx.v7 import forecast_runtime_20261026_v02 as rt


def patch(module):
    module.BASE, module.REL, module.OLDREL = rt.BASE, rt.REL, rt.REL  # OLDREL/'live_cohort.jsonl' -> V02 cohort
    module.verify_release, module.require_activation = rt.verify_release, rt.require_activation
    module.Inputs, module.now = rt.BoundedInputs, rt.now


def main():
    receipt = json.loads((rt.BASE/'activation_receipt.json').read_text())
    source = rt.REPO_ROOT/receipt['source_path']
    rt.now.state_path = source/'clock_state.json'
    samples = rt.load_cohort()
    primed = None
    while rt.now() < receipt['first_grid']-60:
        if (source/'journal.jsonl').exists():
            primed = rt.BoundedInputs(source, samples) if primed is None else primed
            primed.advance()
        time.sleep(30)
    patch(v01_emitter)
    if primed is not None:
        handoff = [primed]
        v01_emitter.Inputs = lambda root, s: handoff.pop() if handoff and str(root) == str(source) else rt.BoundedInputs(root, s)
    v01_emitter.main()


if __name__ == '__main__':
    main()
