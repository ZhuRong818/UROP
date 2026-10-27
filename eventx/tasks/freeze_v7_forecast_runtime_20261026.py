"""Freeze code and operational policy before a fresh input-only rehearsal."""
import ast
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path
from eventx.v7.forecast_runtime_20261026 import *

def local_dependencies(seeds):
    found=set();todo=list(seeds)
    while todo:
        p=todo.pop().resolve()
        if p in found or not p.is_file(): continue
        found.add(p)
        if p.suffix!='.py': continue
        for node in ast.walk(ast.parse(p.read_text())):
            names=[]
            if isinstance(node,ast.Import): names=[n.name for n in node.names]
            if isinstance(node,ast.ImportFrom) and node.module:
                names=[node.module]+[node.module+'.'+n.name for n in node.names]
            for name in names:
                if name=='eventx' or name.startswith('eventx.'):
                    stem=REPO_ROOT/Path(*name.split('.'))
                    for candidate in [stem.with_suffix('.py'),stem/'__init__.py']:
                        if candidate.is_file(): todo.append(candidate)
    return found

def main():
    if REL.exists() or BASE.exists(): raise RuntimeError('Preserve existing release')
    verify_manifest(OLDREL/'delivery_manifest.json');verify_manifest(OLD/'development/manifest.json')
    tests=['eventx.tasks.check_v7_source_time_quote_inputs_20261026','eventx.tasks.check_v7_source_time_study_20261026','eventx.tasks.check_v7_clock_bounded_inputs_20261026','eventx.tasks.check_v7_forecast_runtime_20261026']
    r=subprocess.run([sys.executable,'-m','unittest',*tests],capture_output=True,text=True)
    if r.returncode: raise RuntimeError(r.stdout+r.stderr)
    REL.mkdir(parents=True);BASE.mkdir(parents=True)
    write_new(REL/'qa.json',{'at':iso(now()),'passed':True,'tests':tests,'output':r.stdout+r.stderr,'synthetic_runtime_checks':25,'combined_checks':51,'live_targets_read':False})
    write_new(REL/'environment.json',{'python':platform.python_version(),'platform':platform.platform(),'packages':{n:importlib.metadata.version(n) for n in ['numpy','scipy','scikit-learn','joblib','pyarrow','httpx','websockets']}})
    policy={'frozen_at':iso(now()),'version':'forecast_runtime_20261026_v01','parent_protocol':str((OLDREL/'protocol.json').relative_to(REPO_ROOT)),
      'input_contract':CONTRACT,'models_refitted':False,'target_changed':False,'cohort_changed':False,
      'online_clock_validation':'Reject invalid native selected SNTP packets before applying unchanged V03 interval rule; raw packets retained',
      'emission':'At grid use data available by grid; decision fsync must complete by grid+30s. Commit binds the durable decision and source prefix. Late/uncommitted records abstain; no probability backfill.',
      'adjudication':'Capture endpoint-source prefix at endpoint+120s; scheduling tolerance30s, no new endpoint information after endpoint is admissible. Late/missing receipt yields unknown endpoint. No online labels.',
      'opening':'Only after last endpoint+120s+30s operational grace, verify stopped source/emitter, code/model/source chains and replay predictions. Write exclusive consumption receipt before endpoint construction/scoring. Any post-receipt failure remains consumed.',
      'restart':'Emitter resumes chain without reissuing keys; missed decisions stay missed. Source intentionally refuses implicit restart; source failure requires explicit versioned recovery review.',
      'rehearsal':'Same40min/twoIDs/30minwarmup; no model calls or labels. >=2 ready decisions across >=1 market; schema/scope errors or abnormal completion fail.',
      'activation':'NOT_CREATED. Separate receipt must bind readiness/model/cohort/protocol/code and exact first full UTC day plus seven-day schedule. Fresh source warmup mandatory.',
      'prospective_test_started':False,'trading':False}
    write_new(REL/'runtime_policy.json',policy)
    write_new(REL/'activation_schema.json',{'description':'Required fields only, NOT an activation receipt','fields':['activated_epoch','first_grid','last_grid','open_after','input_contract','implementation_sha256','model_sha256','cohort_sha256','protocol_sha256','readiness_sha256','source_path'],'window_rule':'First full UTC date after activation; seven dates; daily00:30..23:25 grids; final endpoint+120s','source_path':str((BASE/'prospective/source').relative_to(REPO_ROOT))})
    seeds=[Path(__file__).resolve()]+[REPO_ROOT/'eventx/tasks'/name for name in ['run_v7_frozen_classifier_20261026.py','evaluate_v7_frozen_classifier_20261026.py','collect_v7_classifier_readiness_20261026.py','audit_v7_classifier_readiness_20261026.py','check_v7_forecast_runtime_20261026.py']]
    paths=local_dependencies(seeds)|set(REL.iterdir())|{MODEL,OLDREL/'protocol.json',OLDREL/'live_cohort.jsonl',OLDREL/'readiness_spec.json',OLDREL/'delivery_manifest.json',OLD/'development/manifest.json',REPO_ROOT/'eventx/release/v7/market_capture_20261018/protected_ids.json'}
    write_new(REL/'implementation_manifest.json',{'created_at':iso(now()),'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in sorted(paths)}})
    print(json.dumps({'frozen_at':policy['frozen_at'],'locked_files':len(paths),'implementation_sha256':sha(REL/'implementation_manifest.json'),'prospective_test_started':False},indent=2))
if __name__=='__main__':main()
