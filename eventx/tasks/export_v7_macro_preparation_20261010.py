"""Export source-quality and synthetic planning evidence; no forecasting work."""
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'eventx/release/v7/pilot_20261010'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    if (OUT/'PREPARATION_RESULTS.md').exists():raise FileExistsError('Use a new publication version')
    pilot=json.loads((ROOT/'data/v7/macro_pilot_20261010/report.json').read_text())
    rules=json.loads((ROOT/'data/v7/macro_metadata_20261010/report.json').read_text())
    feasibility=json.loads((ROOT/'data/v7/macro_feasibility_20261010/report.json').read_text())
    simulation=json.loads((ROOT/'data/v7/episode_inference_screen_20261010/report.json').read_text())
    records=[json.loads(x) for x in (ROOT/'data/v7/macro_pilot_20261010/source_context.jsonl').open()]
    from datetime import datetime
    utc=lambda x:datetime.fromisoformat(x.replace('Z','+00:00'))
    lags=np.array([(utc(a['available_at'])-utc(a['published_at'])).total_seconds()/60 for a in records])
    plt.rcParams.update({'font.size':10,'svg.fonttype':'none'})
    fig,ax=plt.subplots(figsize=(8.5,4.7),layout='constrained')
    ax.hist(lags,bins=np.arange(60,661,60),color='#27658b',edgecolor='white')
    ax.axvline(np.median(lags),color='#ad3b2c',linestyle='--',label=f'Median {np.median(lags):.1f} min')
    ax.set(xlabel='Publication to conservative availability (minutes)',ylabel='Sampled articles',
           title='Macro pilot: delayed system availability (30 development articles)')
    ax.legend(frameon=False)
    fig.text(.5,.005,'Publication is not verified first-public time. This sample does not establish feed completeness.',ha='center',fontsize=8)
    for ext in ('png','svg','pdf'):fig.savefig(OUT/('availability_lag.'+ext),dpi=180,bbox_inches='tight')
    plt.close(fig)
    methods=[*simulation['candidate_passes_all_cells'],'known_dgp_oracle']
    cells=[(d,c) for d in simulation['spec']['calendar_days'] for c in simulation['spec']['cases']]
    matrix=np.array([[next(r['coverage'] for r in simulation['rows'] if r['days']==d and r['case']==c and r['method']==m) for d,c in cells] for m in methods])
    fig,ax=plt.subplots(figsize=(12,4.8),layout='constrained')
    im=ax.imshow(matrix,vmin=.35,vmax=.96,cmap='RdYlGn',aspect='auto')
    ax.set_xticks(range(len(cells)),[f'{d} days\n'+{'independent_days':'Independent','ar_0_5':'AR .5','ar_0_9':'AR .9','regime_random_half_shift':'Regime'}[c] for d,c in cells],fontsize=8)
    ax.set_yticks(range(4),['IID episodes','Calendar clusters','Bartlett HAC, 14 days','Known-DGP oracle*'])
    for i in range(4):
        for j in range(len(cells)):ax.text(j,i,f'{100*matrix[i,j]:.1f}%',ha='center',va='center',fontsize=8)
    ax.set_title('Synthetic 95% interval coverage: 4,096 replications per DGP cell')
    fig.colorbar(im,ax=ax,label='Empirical coverage')
    fig.text(.5,.005,'*Oracle variance is unavailable on real data. Assumed noise scales; no candidate passed all declared cells.',ha='center',fontsize=9)
    for ext in ('png','svg','pdf'):fig.savefig(OUT/('inference_coverage.'+ext),dpi=180,bbox_inches='tight')
    plt.close(fig)
    p=feasibility['pair_counts'];lag=feasibility['publication_to_conservative_availability_minutes']
    text=f'''# V7 macro pilot preparation: results

Date: 10 October 2026. These are measurement-preparation and synthetic design results, not new forecasting performance.

## Development frame and review packet

| Quantity | Result |
|---|---:|
| Routed retained article rows before exact-content deduplication | {pilot['routed_rows_before_exact_dedup']:,} |
| Distinct routed article content | {pilot['unique_routed_articles']:,} |
| Availability-date × route buckets | {pilot['sampling_bucket_frame']} |
| Sampled articles / buckets | {pilot['sampled_articles']} / {pilot['sampled_date_route_buckets']} |
| Distinct availability dates | {pilot['distinct_availability_dates']} |
| Domain contract cards / provisional source event IDs | {pilot['domain_contracts']} / {pilot['domain_source_event_ids']} |
| Review pairs / unique contracts | {pilot['review_pairs']} / {pilot['unique_reviewed_contracts']} |
| Top-one / alternatives / lower-ranked / outside-top20 pairs | 30 / 30 / 30 / 30 |
| Contracts with resolution text before / after bounded recovery | 0 / {rules['contracts_with_rules']} of {rules['returned_contracts']} |
| Review pairs with recovered rule text | {rules['pairs_with_rules']} of {rules['pairs']} |
| Earlier context entries supplied | {pilot['prior_context_reports']} |
| Independent reviewer responses / validated information episodes | 0 / 0 |

Route composition is 15 monetary-policy, six inflation and nine employment articles. These keyword routes are unvalidated domain hypotheses. The 30 buckets are not 30 independent news episodes. Sampling weights and all strata are recorded before new labels; scores/strata are absent from the review packet. Exact exclusions cover 800 prior/reserved article IDs and content hashes, with reserved records projected solely for exclusion. This new development frame does not reopen the failed V6 audit.

The material preparation improvement is resolution-text coverage: 64/66 contracts (96.97%) and 116/120 pairs (96.67%), compared with no rule text supplied by the original domain cards. It does not establish semantic accuracy or historical version validity. Three exact-ID source requests returned HTTP 200 and all 66 records, with verified data hashes.

## Availability and nominal-window diagnosis

| Diagnostic | Result |
|---|---:|
| Publication to derived availability: minimum / median / maximum, minutes | {lag['min']:.6f} / {lag['median']:.6f} / {lag['max']:.6f} |
| Sampled articles with lag greater than 30 minutes | {lag['above_30_minutes']} / 30 |
| Source runs marked failed / ok / partial | 17 / 12 / 1 |
| Pairs with retrieved metadata snapshot later than article clock | {p['snapshot_after_article']} / 120 |
| Pairs before nominal opening / at or after nominal close | {p['before_nominal_open']} / {p['at_or_after_nominal_close']} |
| Pairs with room for a five-minute landmark plus 30-minute horizon under nominal bounds | {p['full_nominal_landmark_horizon']} / 120 |

The supported timing question is remaining adjustment after system access. The sampled source clock is 90.84–610.28 minutes after publication, not a measured first-public clock. Failed/partial status neither proves a retained article invalid nor certifies completed windows. Nominal bounds and early snapshots do not prove historical active status. The 78 nominally compatible pairs have no independently reviewed relevance or verified source admission; they cannot be called eligible forecast episodes. Current labels can be developed without a support-day certificate, while any independent forecasting claim requires its own evidence.

![Availability delays](availability_lag.png)

## Fixed synthetic inference screen

The prewritten specification used 4,096 replications per DGP cell, 30/60/120 calendar days, capped Poisson episode arrivals, shared calendar shocks, AR persistence and a random half-period regime shift. Calendar and episode noise SDs are assumed at 0.02 nats, with a 0.015-nat regime shift SD. These are sensitivity assumptions, not empirical EventX loss scales. It directly simulates paired losses without fitting forecasts. Four methods across 12 DGP cells give 48 coverage rows; two alternative gains give 96 power rows.

| Candidate | Cells passing the declared coverage/type-I gate | Worst empirical 95% coverage |
|---|---:|---:|
'''
    for method in simulation['candidate_passes_all_cells']:
        rows=[r for r in simulation['rows'] if r['method']==method]
        text+=f"| {method} | {sum(r['passes_declared_cell'] for r in rows)} / {len(rows)} | {min(r['coverage'] for r in rows):.6f} |\n"
    text+='''
None is adopted. Under the known-DGP oracle, the 120-day 80%-power reference detectable effect is 0.007743 nats for independent day shocks and 0.022100 for AR(0.9). At a true 0.001-nat gain, corresponding simulated probabilities of a positive lower bound are only 0.050781 and 0.034180. Oracle variance is unavailable in a real study; these numbers illustrate the assumed design's weakness, not a calibrated real sample-size requirement. The pilot's actual paired-loss scale and independent episode yield remain unknown. A practical threshold must not be changed to hide inadequate power.

![Coverage screen](inference_coverage.png)

## Execution state

- Sampling plan, rubric, real review packets, response intake implementation and budgets: prepared.
- Contract rule recovery and source/window feasibility: completed as descriptive development work.
- Synthetic uncertainty/power screen: completed; all three candidates fail the all-cell gate.
- V7 grid and event-study specification: written, not confirmatory-frozen.
- Independent annotations/adjudication, deployable semantic features, empirical paired-loss comparison and final inference: pending.
- New untouched evaluation dates and forecasting freeze: pending those design gates.
- Paper A: revision 2, independent-review request, method-positioning comparison and rights inventory prepared; no independent judgment or rights clearance received.
- V4: latest label-blind health receipt is [10 October 00:40:11 UTC](../../../../data/v4/health_checks/20261010T004011Z/report.json). Collector and guard alive; 41 news days/34 trade days through 9 October, 41/340 receipt sets, zero backlog, 15/15 frozen hashes matching. No protected downstream artifact exists. After the 30 October UTC close, preserve audit → consumption receipt → preparation → examples → one-shot evaluation and stop on any failed gate.

## Immediate next input and runnable handoff

Return two independent human response files using [review handoff](REVIEW_HANDOFF.md). This unlocks actual episode/role/direction/novelty diagnostics. Run the written intake once per submitted version; preserve originals and one adjudication. Source gaps and untouched-date choices cannot be inferred from those semantic labels. The separately prepared Lumid source request remains unsent because no destination/authorization to send was supplied.

Sources: [pilot](../../../../data/v7/macro_pilot_20261010/report.json), [rule recovery](../../../../data/v7/macro_metadata_20261010/report.json), [feasibility](../../../../data/v7/macro_feasibility_20261010/report.json), [simulation](../../../../data/v7/episode_inference_screen_20261010/report.json), [sampling plan](SAMPLING_PLAN.md), [rubric](ANNOTATION_RUBRIC.md), [study specification](STUDY_SPEC.md), and [paper review](../../paper_a_review_20261010/REVIEW_REQUEST.md).
'''
    (OUT/'PREPARATION_RESULTS.md').write_text(text)
    root=ROOT/'MARKET_NEWS_NEXT_STEPS_EXECUTION_20261010.md'
    if root.exists():raise FileExistsError(root)
    root.write_text('''# Market-news research: next steps executed

10 October 2026. Development preparation is now active; no new forecasting improvement is claimed.

## Completed

1. Built a 120-pair macro evidence packet from 30 historical articles across 26 dates, with fixed sampling, two blank independent-review forms, exact evidence-span fields and a one-adjudication budget.
2. Recovered descriptive metadata for all 66 review contracts; 64 now have resolution text, supplying rules to 116/120 pairs. This improves review evidence coverage, not measured forecast accuracy.
3. Diagnosed source timing: every sampled article's publication-to-derived-availability lag exceeds 90 minutes; median 226.000252 minutes. The feasible research question concerns adjustment remaining after system access.
4. Ran a fixed synthetic dependence/power screen. None of the three proposed uncertainty estimators passed every case. Inference remains unset; simulation noise scales are assumptions.
5. Specified the distinct full-grid and five-minute-landmark studies, strong market/exposure/timing controls, signed-evidence features, population weighting, untouched-data boundaries and final freeze gates.
6. Prepared Paper A revision 2, an independent-review request, focused full-text method comparison and a concrete release-rights inventory.
7. Checked V4 label-blind: collection/guard alive, checkpoint through 9 October, zero backlog and all 15 frozen hashes matching. Its 30 October close and one-shot sequence remain controlling.

## Deliverables

- [Detailed preparation results, figures and source evidence](eventx/release/v7/pilot_20261010/PREPARATION_RESULTS.md)
- [Review packet with recovered rules](data/v7/macro_metadata_20261010/REVIEW_PACKET_WITH_RULES.md)
- [Reviewer handoff and response forms](eventx/release/v7/pilot_20261010/REVIEW_HANDOFF.md)
- [V7 study specification](eventx/release/v7/pilot_20261010/STUDY_SPEC.md)
- [Paper A revision 2](MARKET_NEWS_PAPER_A_DRAFT_20261010_REV2.md)
- [Independent paper review request](eventx/release/paper_a_review_20261010/REVIEW_REQUEST.md)

## Still outstanding

Two real outcome-blind annotations and adjudication, independent scientific review, reviewer/author/venue details and release permission need external input. The automatic semantic feature pipeline, empirical delayed-repricing comparison and final inference/power design follow the annotation findings. No new predictive fit, held-out result, signed-surprise accuracy or independent episode count exists yet. The final V7 freeze cannot be declared complete on the current evidence.

Independent prospective V4 evaluation remains a post-close task; no early consumption or revision occurred. Existing manuscript versions, consumed holdouts and frozen experiment artifacts are preserved.
''')
    inputs={}
    for rel in ('data/v7/macro_pilot_20261010/manifest.json','data/v7/macro_metadata_20261010/supplement_manifest.json',
                'data/v7/macro_feasibility_20261010/manifest.json','data/v7/episode_inference_screen_20261010/manifest.json',
                'data/v4/health_checks/20261010T004011Z/report.json',str(Path(__file__).relative_to(ROOT))):
        inputs[rel]=sha(ROOT/rel)
    (OUT/'preparation_export_manifest.json').write_text(json.dumps({'role':'development preparation and scientific planning export',
         'inputs':inputs,'outputs':{p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file()},
         'root_report':{'path':str(root.relative_to(ROOT)),'sha256':sha(root)},'forecast_freeze':False},indent=2)+'\n')
    print(json.dumps({'root_report':str(root.relative_to(ROOT)),'detailed_report':str((OUT/'PREPARATION_RESULTS.md').relative_to(ROOT)),
                      'new_forecast_evaluation':False},indent=2))


if __name__=='__main__':main()
