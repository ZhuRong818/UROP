"""Freeze a bounded ordering correction from clock evidence, not forecasting outcomes."""
from pathlib import Path
import json
from eventx.tasks.run_v7_source_time_study_20261026_v03 import BASE,REL,REPO_ROOT
from eventx.tasks.discover_v7_direct_pilot_20261022 import now,sha,write,verify_originals
from eventx.tasks.run_v7_archive_week_pilot_20261025 import verify
from eventx.v7.clock_bounded_quote_inputs_20261026 import CONTRACT

def main():
 verify_originals();oldrel=REPO_ROOT/'eventx/release/v7/source_time_study_20261026_v02';probe=REPO_ROOT/'data/v7/clock_alignment_20261026'
 verify(oldrel/'delivery_manifest.json');verify(probe/'manifest.json')
 evidence=json.loads((probe/'report.json').read_text());google=evidence['ntp_by_host']['time.google.com']
 assert len(google)==3 and all(0<r['offset_seconds']-r['reported_uncertainty_seconds']<r['offset_seconds']+r['reported_uncertainty_seconds']<.1 for r in google)
 REL.mkdir(parents=True,exist_ok=False);BASE.mkdir(parents=True,exist_ok=False)
 p=json.loads((oldrel/'protocol.json').read_text());p.update(version='source_time_study_20261026_v03',frozen_at=now().isoformat(),input_contract=CONTRACT,
  correction='Bound apparent source-minus-durable lead to250ms instead of demanding zero lead. Still require BOTH source<=decision and durable availability<=decision. Preserve all raw times; no timestamp shifts or system clock writes.',
  correction_evidence='Three Google offsets58.124–61ms with7.302–9.534ms reporteduncertainty;Cloudflare compatible;Apple broad uncertainty uninformative. Earlier84/92WSsource times led localdurability by<=91ms. Contemporary offsets do not prove historical host or venue offsets.',
  tolerance_justification='250ms is a predeclared engineering cap with margin over measured host offset and observed91ms lead; NOT a confidence interval or venue accuracy guarantee. Causality is enforced separately by durable availability<=decision;source<=decision also retained.',
  measurement='SourceTimeQuoteTape V03:onlyprice_changeBBO;source<=decision,availability<=decision,source-availability<=.250s;sourceage<=120s;invalidlatestclocklead fails;otherquote/tie/lagrules unchanged.',
  clock_monitor='At each decision use latestcompletedprobe<=decision andage<=360s;>=2independent hosts withreporteduncertainty<=100ms,atleastone<=20ms;offsetintervalintersection nonempty andcontained[-100ms,+100ms]. Wall-versus-monotonic step>20ms resets30minwarmup.',
  outcome_independence='May9 already outcome-open inV01/V02. V03 is a clock-measurement repair;allfixedmodels retrained,allresults retained regardlessscore. No sweepoverclocktolerances.',
  source_readiness='Fresh40mincapture on same twoIDs;strictV02 andcorrectedV03 compared side-by-side on identicalrawmessages. No models scored or live labels built.')
 p['future_test']['current_live_gate']+='; V03 bounded ordering and independent as-of clock-health monitor required'
 p['future_test']['endpoint_live_gate']+='; same V03 ordering and as-of clock-health gate atendpoint; clocksteps resettransporthistory'
 p['live_readiness']='Same40min/same2IDs/samegrid/30minwarmup;no projectionscopeerrors,normalcompletion,>=2fully-ready decisions>=1market,now also independentclockhealth. ReportstrictV02 andcorrectedV03 on identicalcapture. No forecast test.'
 write(REL/'protocol.json',p)
 for name in ['live_cohort.jsonl','readiness_spec.json']:(REL/name).write_bytes((oldrel/name).read_bytes())
 spec=json.loads((REL/'readiness_spec.json').read_text());spec.update(version='clock_readiness_20261026_v03',clock_probe_interval_seconds=300,clock_rule=p['clock_monitor']);write(REL/'readiness_spec.json',spec)
 paths=list(REL.iterdir())+[Path(__file__).resolve(),oldrel/'delivery_manifest.json',probe/'manifest.json']
 for name in ['eventx/v7/clock_bounded_quote_inputs_20261026.py','eventx/v7/source_time_study_20261026_v03.py','eventx/tasks/run_v7_source_time_study_20261026_v03.py','eventx/tasks/check_v7_clock_bounded_inputs_20261026.py','eventx/tasks/collect_v7_clock_readiness_20261026.py','eventx/tasks/collect_v7_source_time_readiness_20261026.py']:
  paths.append(REPO_ROOT/name)
 write(REL/'implementation_manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in paths}})
 state=REPO_ROOT/'CURRENT_STATE.md';s=state.read_text();(REPO_ROOT/'docs/progress/CURRENT_STATE_BEFORE_CLOCK_CORRECTION_20261026.md').write_text(s)
 s=s.replace('source-time V02 fitted/frozen; live input check failed on clock/freshness; no prospective test.','V03 clock correction frozen from independent probes; development/repeat readiness in progress; no test.')
 s=s.replace('## Source-time classifier preparation (26October)','## Clock correction (26October)\n\n- IN PROGRESS:`eventx/release/v7/source_time_study_20261026_v03/protocol.json`;independentGoogleSNTPoffset+58.124..61ms.\n- V03bounds apparentlead250ms,but BOTHsourceandavailabilitymustprecededecision;no rawtimechanges.\n- Refit samefixedmodels onrebuiltMay7–9development;repeat40mininput-onlycapture withclockmonitor. No test.\n\n## Source-time classifier preparation (26October)')
 a=s.index('## Prior quote experiments (25October)');b=s.index('## Seven-day fixed-model replication (25October)')
 s=s[:a]+'''## Earlier quote experiments

- April25–30,May4–6 andMay10–12opened;no retuning. Oldpointfailure and18featuremodels preserved.
- Fullhistory:`docs/progress/CURRENT_STATE_BEFORE_CLOCK_CORRECTION_20261026.md`;frozenreportsgovern.

'''+s[b:];state.write_text(s)
 with (REPO_ROOT/'docs/progress/2026-10.md').open('a') as f:
  f.write('\n## '+now().isoformat()+' — independentclockaudit andV03correctionfreeze\n\nSandboxSNTPDNSfailed;read-onlynetworkescalationapproved.No systemclocksettingflagsused. Threeproviders×3SNTPsuccess,12CLOB/timeHTTPsuccess.OfficialAsyncAPIdocumentsUnixmilliseconds;CLOB/timesecondsquantizationcannotverify91msskew. Probe manifest:data/v7/clock_alignment_20261026/manifest.json. '+json.dumps(evidence,sort_keys=True)+'\n')
  f.write('V03correctionfrozenbeforemodelrebuild/newcapture:250msapparentleadcap;actualdurableavailabilityandsourceboth<=decision,nobackdating. Capengineeringassumption,notvenueSLAorconfidencebound. Independentclockmonitor+wall/monotonicstepguard added. Samefeaturecount,models/cohort/targethorizon;allresultsretained. V02failurepreserved;no prospectivetest.\n')
 print(json.dumps({'version':p['version'],'frozen_at':p['frozen_at'],'protocol_sha256':sha(REL/'protocol.json')}))
if __name__=='__main__':main()
