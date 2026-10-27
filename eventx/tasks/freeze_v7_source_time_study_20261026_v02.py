"""Mandatory midnight-history consistency repair; no model/metric-driven choices."""
from pathlib import Path
import json
from eventx.tasks.run_v7_source_time_study_20261026_v02 import BASE,REL,DEV,REPO_ROOT
from eventx.tasks.discover_v7_direct_pilot_20261022 import now,sha,write,verify_originals
from eventx.tasks.run_v7_archive_week_pilot_20261025 import verify

def main():
 verify_originals();oldrel=REPO_ROOT/'eventx/release/v7/source_time_study_20261026';oldbase=REPO_ROOT/'data/v7/source_time_study_20261026'
 verify(oldrel/'implementation_manifest.json');verify(oldbase/'development/manifest.json')
 REL.mkdir(parents=True,exist_ok=False);BASE.mkdir(parents=True,exist_ok=False)
 p=json.loads((oldrel/'protocol.json').read_text());p.update(version='source_time_study_20261026_v02',frozen_at=now().isoformat(),
  correction='Carry all prior available May7–9 development rows across midnight; same SourceTimeQuoteTape semantics as continuous live stream. First day remains left-censored; do not fetch May6 or infer missing history.',
  correction_evidence='V01 day-partitioned loader changed22 of100 boundary vectors checked at00:30 onMay8/9; preserveV01 results but do not activate its model.',
  outcome_independence='May9 validation already inspected under V01; V02 is a required implementation repair, not fresh validation. Retain V02 even if its metrics worsen.',
  source_readiness='Reuse ongoing source-only capture data/v7/source_time_study_20261026/readiness; it uses no model and no labels; evaluate against V02 model gate separately.')
 write(REL/'protocol.json',p)
 for name in ['live_cohort.jsonl','readiness_spec.json']:(REL/name).write_bytes((oldrel/name).read_bytes())
 paths=list(REL.iterdir())+[Path(__file__).resolve(),REPO_ROOT/'eventx/tasks/run_v7_source_time_study_20261026_v02.py',
   oldrel/'implementation_manifest.json',oldbase/'development/manifest.json',oldbase/'day_boundary_diagnostic.json']
 write(REL/'implementation_manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
 state=REPO_ROOT/'CURRENT_STATE.md';s=state.read_text();s=s.replace('- Protocol frozen:`eventx/release/v7/source_time_study_20261026/protocol.json`;no prospective test started.',
 '- V02 repair frozen:`eventx/release/v7/source_time_study_20261026_v02/protocol.json`;no prospective test started.')
 s=s.replace('- Development:`data/v7/source_time_study_20261026/development/report.json`;May7–8fit6304,May9known3102.',
 '- V01 historical day reset affected22boundary vectors;V01activation BLOCKED;V02 carries prior available history.')
 s=s.replace('- LLHGB0.3560554746702914 vs logistic0.42676612531016495(16.56894641965373%lower);\n  Brier0.11044113032192052 vs0.1293959722440859. DevelopmentgatePASS,notconfirmation.',
 '- V01 results preserved:`data/v7/source_time_study_20261026/development/report.json`;V02fit in progress.')
 state.write_text(s)
 with (REPO_ROOT/'docs/progress/2026-10.md').open('a') as f:
  f.write('\n## '+now().isoformat()+' — midnight-boundary defect found;V02 repair frozen\n\nV01 training loader reset rows perUTCdate unlike continuous liveSourceTimeQuoteTape. Feature-onlycheck of100decisions00:30May8/9 found22differences in30minlag family;diagnostic data/v7/source_time_study_20261026/day_boundary_diagnostic.json. V01modelnoteligibleforactivation despite favorabledevelopmentmetrics. V02 carries prior availabledevelopmenthistory,noMay6fetch,no newfeatures/hyperparameters/cohort/targetor evaluationchoices. Existinglabels/modelresults outcome-open;repairresults exploratory andretainedregardlessperformance. Ongoing40mincapture source-only andmodel-independent;no restartneeded. Newfreeze:'+str(REL.relative_to(REPO_ROOT))+'/implementation_manifest.json.\n')
 print(json.dumps({'frozen_at':p['frozen_at'],'version':p['version'],'prospective_test_started':False}))
if __name__=='__main__':main()
