"""Freeze a development-only comparison before computing new quote targets."""
import json
from pathlib import Path
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals

RELEASE=REPO_ROOT/'eventx/release/v7/memory_quote_20261024'
BASE=REPO_ROOT/'data/v7/memory_quote_20261024'
AUDIT=REPO_ROOT/'data/v7/direct_source_pilot_20261022_v03/audits/20261024T060327Z_808a25'

def main():
    verify_originals();RELEASE.mkdir(exist_ok=False);BASE.mkdir(exist_ok=True)
    parent=REPO_ROOT/'eventx/release/v7/quote_experiment_20261024'
    for p,h in json.loads((parent/'implementation_manifest.json').read_text())['locked_files'].items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Parent drift')
    for n in ['development_cohort.jsonl','forward_cohort.jsonl']:(RELEASE/n).write_bytes((parent/n).read_bytes())
    p=json.loads((parent/'policy.json').read_text())
    for k in ['features','history_minutes','forward_collector_stop','models']:p.pop(k,None)
    p.update(at=now().isoformat(),version='memory_quote_20261024',
        authorization='User requested continuing local research and usable forecasts after zero-forecast first shadow',
        feature_tiers={'snapshot':'Current valid book and current status; no historical feature requirement','short':'Current valid book/status plus uninterrupted30m quote history'},
        primary_reference='persistence',candidates=['weighted_midpoint','snapshot_ridge','short_ridge'],ridge_alpha=100.0,
        target_unchanged='30-minute receipt-clock midpoint with continuous forward quote/status coverage; no gaps filled',
        new_eligibility='Explicit new experiment, not a rescue or rerun of closed240m shadow',
        models_promoted=False,forecast_horizons_seconds=[1800],
        training='decision+30min <2026-10-24T00:00:00Z',validation='decision>=2026-10-24T00:30:00Z; endpoint within fixed source snapshot',
        development_warning='Outcomes already exposed in earlier related work; all comparisons exploratory',
        comparison='All snapshot-eligible rows and separately all short-eligible rows; models compared only on identical keys',
        publication='Baseline forecast available as research reference; candidates displayed separately; no claimed edge or trading recommendation')
    write(RELEASE/'policy.json',p)
    files=list(RELEASE.iterdir())+[Path(__file__).resolve(),AUDIT/'manifest.json',
        REPO_ROOT/'eventx/v7/memory_quote_20261024.py',REPO_ROOT/'eventx/v7/quote_experiment_20261024.py',
        REPO_ROOT/'eventx/tasks/run_v7_memory_quote_20261024.py',parent/'implementation_manifest.json']
    write(RELEASE/'implementation_manifest.json',{'locked_files':{str(f.relative_to(REPO_ROOT)):sha(f) for f in files}})
    print(json.dumps({'frozen':str(RELEASE.relative_to(REPO_ROOT)),'target':'30-minute midpoint','tiers':['snapshot','short']}))

if __name__=='__main__':main()
