"""Post-freeze synthetic integration QA. Does not start a live forecast service."""
from contextlib import ExitStack
from pathlib import Path
import json
import tempfile
from unittest.mock import patch
from eventx.tasks.check_v7_forecast_runtime_20261026 import RuntimeChecks
from eventx.v7.forecast_runtime_20261026 import REL,BASE,OLDREL,MODEL,sha,write_new,read_chain
from eventx.tasks import run_v7_frozen_classifier_20261026 as emit
from eventx.tasks import evaluate_v7_frozen_classifier_20261026 as evaluate

fixture=RuntimeChecks();RuntimeChecks.setUpClass();fixture.setUp()
try:
    fixture.setup_valid();t=fixture.t
    fixture.add('process_stopped',t+1810)
    source=fixture.root
    write_new(source/'capture_manifest.json',{'files':{str(p):sha(p) for p in source.rglob('*') if p.is_file()}})
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);base=root/'study';base.mkdir()
        receipt={'activated_epoch':t-86400,'first_grid':t,'last_grid':t,'open_after':t+1920,'source_path':str(source)}
        write_new(base/'activation_receipt.json',receipt)
        clock=[t+1]
        def advance(_): clock[0]=t+1921 if clock[0]<t+1920 else t+2000
        with ExitStack() as stack:
            for mod in [emit,evaluate]:
                stack.enter_context(patch.object(mod,'BASE',base));stack.enter_context(patch.object(mod,'REPO_ROOT',root))
                stack.enter_context(patch.object(mod,'verify_release'))
                stack.enter_context(patch.object(mod,'require_activation'))  # Synthetic one-grid window only.
                stack.enter_context(patch.object(mod,'now',lambda:clock[0]))
            stack.enter_context(patch.object(emit.time,'sleep',advance))
            emit.main()
            rr=read_chain(base/'prospective/emitter/journal.jsonl')[0]
            dec=[r for r in rr if r['kind']=='decision'];commits=[r for r in rr if r['kind']=='emission_commit']
            assert len(dec)==2 and sum(c['timely'] for c in commits)==1
            assert len([r for r in rr if r['kind']=='endpoint_receipt'])==2
            assert not any('target' in r or 'endpoint_midpoint' in r for r in rr)
            clock[0]=t+1900
            try: evaluate.main()
            except RuntimeError as e: assert str(e)=='Window still sealed'
            else: raise AssertionError('Premature evaluator admitted')
            assert not (base/'evaluation').exists()
            clock[0]=t+2000;evaluate.main()
            result=json.loads((base/'evaluation/report.json').read_text())
            assert result['known']==1 and result['timely']==1 and result['scheduled']==2
            assert json.loads((base/'evaluation/endpoint_ledger.json').read_text())[0]['target']==1
            assert (base/'evaluation/consumption_receipt.json').exists()
            try: evaluate.main()
            except RuntimeError as e: assert 'already attempted' in str(e)
            else: raise AssertionError('Repeat consumption admitted')
            receipt_guard=True
    write_new(BASE/'integration_qa.json',{'passed':True,'scope':'Synthetic one-grid fixture; no live forecasts/targets','real_frozen_models_used_on_synthetic_inputs':True,'emitter_main_exercised':True,'evaluator_main_exercised':True,'timely_forecast':1,'abstention':1,'endpoint_receipts':2,'premature_opening_blocked':True,'repeated_evaluation_blocked':receipt_guard,'live_labels_constructed':0,'prospective_test_started':False})
    print('Synthetic emitter-to-evaluator integration passed')
finally: fixture.tearDown()
