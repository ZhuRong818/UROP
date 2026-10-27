"""Publish 100 unsigned policy-decision candidates, preserving corpus receipts."""
from collections import defaultdict,Counter
from pathlib import Path
import json
import numpy as np
from eventx.tasks.diagnose_v7_signed_evidence_coverage_20261012 import write_json,write_jsonl
from eventx.tasks.run_v5_residual_feasibility import REPO_ROOT,read_jsonl,sha256_file

OUT=REPO_ROOT/'data/v7/relaxed_policy_context_v04_1_20261012'
REPORT=REPO_ROOT/'eventx/release/v7/pilot_20261010/RELAXED_POLICY_CONTEXT_20261012.md'

def main():
    if (OUT/'POLICY_DECISION_REVIEW_100.md').exists(): raise SystemExit('Published output preserved')
    manifest=json.loads((OUT/'manifest.json').read_text())
    for e in manifest['artifacts']:
        if sha256_file(REPO_ROOT/e['path'])!=e['sha256']: raise RuntimeError(e['path'])
    traces=list(read_jsonl(OUT/'association_trace.jsonl')); unique={}
    for r in sorted(traces,key=lambda r:(r['available_at'],r['article_id'],r['market_id'])):
        if r['context']['tier']=='policy_decision_context' and r['coverage']['30']['rows']>0:
            unique.setdefault(r['article_id'],r)
    buckets=defaultdict(list)
    for r in unique.values(): buckets[r['available_at'][:10]].append(r)
    packet=[]
    while buckets and len(packet)<100:
        for day in sorted(list(buckets)):
            packet.append(buckets[day].pop(0))
            if not buckets[day]: del buckets[day]
            if len(packet)==100: break
    assert len(packet)==len({r['article_id'] for r in packet})==100
    assert all(r['context']['direction'] is None and r['coverage']['30']['rows']>0 for r in packet)
    article_links=defaultdict(list)
    for r in traces:
        if r['article_id'] in unique and r['context']['tier']=='policy_decision_context' and r['coverage']['30']['rows']>0:
            article_links[r['article_id']].append({k:r[k] for k in ('event_index','market_id','question','coverage')})
    review=[]; md=['# 100 policy-decision context candidates','','Development review only. These articles overlap existing forecast keys within 30 minutes of conservative system availability. Exact contract month/amount entailment was waived; YES/NO direction is unknown. Article eligibility here means operational context coverage, not validated relevance or source certification.','','## Review instructions','','For each article, judge whether the quoted policy context plausibly informs the linked contract, classify forecast/official statement/observed decision/general expectations/background, flag wrong periods and market-odds repetition, and quote a supporting or rejecting span. Mark uncertainty explicitly. Do not force direction or surprise. Rows and repeated coverage are not independent events.','']
    for i,r in enumerate(packet,1):
        record=dict(r,pair_id=f'context-review-{i:03d}',eligible_context_links=article_links[r['article_id']],review={'reviewer_id':None,'relevance':None,'claim_role':None,'period_relation':None,'repeats_market_odds':None,'evidence_span':None,'rationale':None})
        review.append(record)
        md += [f'## {i}. {r["headline"]}','',f'Article `{r["article_id"]}`; available `{r["available_at"]}`; publication lag {r["lag_minutes"]:.1f} minutes.','',f'Example contract: {r["question"]}','',f'Existing 30-minute rows for this example link: {r["coverage"]["30"]["rows"]}. Context direction: **unknown**.','', 'Quoted policy context:','']
        md += ['> '+s['text'].replace('\n','\n> ') for s in r['context']['spans']]
        md += ['','Review judgment: ______','']
    write_jsonl(OUT/'policy_decision_review_100.jsonl',review)
    (OUT/'POLICY_DECISION_REVIEW_100.md').write_text('\n'.join(md))
    stats={'articles':100,'arrival_dates':len({r['available_at'][:10] for r in packet}),'packet_coverage_by_fold':{str(f):sum(any(link['coverage']['30']['folds'][str(f)]>0 for link in article_links[r['article_id']]) for r in packet) for f in range(1,6)},'all_primary_eligible_decision_context_articles':len(unique),'eligible_article_lag_median_minutes':float(np.median([r['lag_minutes'] for r in unique.values()])),'packet_headline_duplicates':100-len({r['headline'].lower().strip() for r in packet}),'review_labels':'blank'}
    write_json(OUT/'review_packet_report.json',stats)
    REPORT.write_text('''# Relaxed policy-context yield — 12 October 2026

## Result

**The 100-article development candidate target is achievable without changing market eligibility or the availability clock.**

| Stage | Articles | Existing OOF rows within 30 minutes |
|---|---:|---:|
| Previous exact signed extractor | 2 | 0 |
| New policy-decision context, before row screening | 331 | — |
| Policy-decision context with row coverage | **144** | **1,056** |
| Broader topic + decision context with coverage | 154 | 1,093 |
| Selected policy-decision review package | **100** | See link-level traces |

All 147,377 deduplicated documents and 479,179 legacy candidate associations were processed. The broader context extractor retained 9,338 associations: 8,196 decision-context links and 1,142 topic-context links, across 380 articles and 29 markets. Distinct articles are not independent episodes; the policy-decision covered population spans 32 arrival dates.

## What was loosened

Exact evidence required the action to imply the specific contract month, quantity and bucket. The new v0.4 development tier accepts Fed and policy-rate language in the same text segment, including forecasts, conditional statements and market expectations. Decision-language context is distinguished from broader topic context. Exact month and amount entailment is not required. **Direction remains unknown**: no YES/NO signal or information surprise is inferred from these contextual matches.

Conservative system availability, existing market decision eligibility, held-group keys and the primary 30-minute window were preserved. The 60/180-minute windows are descriptive sensitivity only, not the selected task. No labels were read and no forecasting model was fit.

## The remaining bottleneck

| Existing fold | Covered decision-context articles | Covered rows |
|---|---:|---:|
| 1 | 51 | 440 |
| 2 | 71 | 537 |
| 3 | 3 | 7 |
| 4 | 13 | 55 |
| 5 | **6** | **17** |

Counts are deduplicated within each fold; do not sum article counts to infer independent events. Earlier-fold concentration means the overall 144-article yield does not imply 100 usable articles in the latest fold. At 60 minutes fold 5 has eight articles/28 rows; at 180 minutes fourteen/62. Widening the window does not establish useful predictive information.

This operational coverage screen does not validate semantic relevance, historic contract status or feed completeness. Broad context can include investment commentary, stale forecasts and coverage repeating market expectations. For example, the packet includes conditional Fed statements and dividend/ETF commentary; review must distinguish direct information from peripheral coverage.

## Deliverables and next step

- [100 policy-decision articles, readable review package](../../../../data/v7/relaxed_policy_context_v04_1_20261012/POLICY_DECISION_REVIEW_100.md)
- [Structured blank review packet](../../../../data/v7/relaxed_policy_context_v04_1_20261012/policy_decision_review_100.jsonl)
- [Full coverage report](../../../../data/v7/relaxed_policy_context_v04_1_20261012/report.json)

Review the 100 candidates for material relevance and evidence role, then group repeated coverage into event episodes. A subsequent development comparison should use the selected strong market model plus exposure/timing controls versus unsigned policy context, on identical keys. Report all-population and exposed-subset outcomes separately. The latest-fold sample is presently too small for a strong independent claim; do not change frozen V4 or use consumed holdouts to enlarge it.

## Execution record

The first run completed candidate processing but failed JSON serialization on a NumPy integer. Its partial output remains in `data/v7/relaxed_policy_context_20261012/`. A separate corrected run in `relaxed_policy_context_v04_1_20261012` completed with identical extraction rules and a fresh code receipt. Thirty-six input hashes, availability clocks and evidence spans matched. No software tests were run. Code, reports and review packet are hash-receipted.
''')
    checks={'verified_corpus_artifacts':len(manifest['artifacts']),'unique_review_articles':len(review),'all_review_articles_have_primary_coverage':True,'all_directions_unknown':True,'stats':stats}
    write_json(OUT/'delivery_checks.json',checks)
    files=[p for p in OUT.iterdir() if p.is_file()]+[REPORT,Path(__file__).resolve()]
    write_json(OUT/'delivery_manifest.json',{'artifacts':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in files]})
    print(json.dumps(checks,indent=2))

if __name__=='__main__':main()
