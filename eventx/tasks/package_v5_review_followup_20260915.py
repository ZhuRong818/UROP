"""Package source recovery, a topic addendum and a blinded second-review packet."""
import hashlib
import json
from pathlib import Path

from eventx.tasks.certify_v5_family_graph import components

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/v5/review_followup_20260915'
REC=ROOT/'data/v5/provenance_recovery_20260908'
FIRST=ROOT/'data/v5/topic_first_review_20260914/first_review.jsonl'
QUEUE=ROOT/'data/v5/recovery_summary_20260910/candidate_family_queue.jsonl'
BEL='0x3ceb5b631318be5000758200590efe2b308a581d6787c3e7bc050bfd8f627627'
ATTEMPTS=['may19_runs_20260915','belgium_identity_20260915','missing_subtitles_20260915',
          'coverage_runs_retry_20260915','coverage_gap_retry_20260915',
          'raw_identity_20260915','intended_feed_runs_20260915']


def readrows(p):
    with p.open() as f:
        return [json.loads(l) for l in f]


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError('Do not overwrite review evidence')
    inputs=[FIRST,QUEUE,Path(__file__)]
    receipts=[]
    for name in ATTEMPTS:
        p=REC/(name+'.json'); inputs.append(p)
        r=json.loads(p.read_text()); receipts.append(r)
        if r['status']=='complete':
            p=ROOT/r['data_path']; inputs.append(p)
            assert sha(p)==r['data_sha256']
    belgium=readrows(REC/'belgium_identity_20260915.jsonl')
    assert len(belgium)==1 and belgium[0]['condition_id']==BEL
    assert belgium[0]['embedded_event_slug']=='fifwc-bel-egy-2026-06-15'
    addendum={'market_id':BEL,'reviewer':'Codex first-review addendum 2026-09-15',
        'topic':'sports','reason':'Recovered Belgium vs. Egypt event and fifwc fixture slug',
        'evidence':belgium[0],'historical_metadata_certified':False,
        'topic_final_approved':False,'supersedes_only':'unresolved first-review topic; prior artifact retained'}
    first=readrows(FIRST)
    packet=[]
    for r in first:
        # Deliberately exclude suggested and first-review labels/rationales/flags.
        packet.append({'market_id':r['market_id'],'venue':r['venue'],
            'question':r['question'],'yes_sub_title':r.get('yes_sub_title'),
            'no_sub_title':r.get('no_sub_title'),
            'event_title':belgium[0]['embedded_event_title'] if r['market_id']==BEL else None,
            'event_slug':belgium[0]['embedded_event_slug'] if r['market_id']==BEL else None,
            'reviewer':None,'topic':None,'rationale':None,'confidence':None,
            'insufficient_context':None})
    assert len(packet)==30
    assert all('suggested_topic' not in r and 'reviewer_1_topic' not in r for r in packet)
    missing=readrows(REC/'missing_subtitles_20260915.jsonl')
    raw=readrows(REC/'raw_identity_20260915.jsonl')
    assert len(missing)==15 and {r['ticker'] for r in missing}=={r['ticker'] for r in raw}
    unresolved=[r['ticker'] for r in missing if not r['yes_sub_title']]
    runrows=readrows(REC/'intended_feed_runs_20260915.jsonl')
    day19=[r for r in runrows if r['run_day']=='2026-05-19']
    # Extend only an explicit same-election dependency, never certify boundaries.
    oldpath=ROOT/'data/v5/family_certification_20260910/candidate_components.json'
    inputs.append(oldpath)
    old=json.loads(oldpath.read_text())
    nodes=[n for group in old for n in group]
    edge=('kalshi:event:KXGOVCA-26','kalshi:event:KXCAGOVPRIMARY1ST-26JUN02-1ST')
    q=readrows(QUEUE)
    identities=[{k:r[k] for k in ['market_id','question','candidate_family_id']}
                for r in q if r['candidate_family_id'] in edge]
    assert all(n in nodes for n in edge)
    assert identities and all('California' in r['question'] for r in identities)
    prior_edges=[(group[0],n) for group in old for n in group[1:]]
    new=components(nodes,prior_edges+[edge])
    family={'edge':edge,'reviewer':'Codex source-semantic review 2026-09-15',
        'reason':'California governorship 2026 general-election contracts depend on same 2026 primary; extend existing primary/general scope',
        'identities':identities,'final_boundary_approved':False,
        'remaining':'Other election/multi-leg/cross-venue boundaries and exact historical metadata'}
    report={'status':'source_recovery_and_review_preparation_complete_not_admitted',
        'requests':len(receipts),'successful_requests':sum(r['status']=='complete' for r in receipts),
        'failed_requests':sum(r['status']!='complete' for r in receipts),
        'belgium_topic_context_recovered':True,
        'first_review_assigned_after_addendum':30,'independent_second_reviews':0,
        'second_review_packet_rows':len(packet),'final_topics_approved':0,
        'missing_subtitles_requested':15,'missing_subtitles_returned':len(missing),
        'missing_subtitles_still_null':len(unresolved),
        'intended_feed_run_groups_on_may19':len(day19),
        'coverage_interpretation':'No retained starts on May19 for eight specified article feeds; schedules, overlapping runs and retries not certified',
        'old_provisional_components':len(old),'new_provisional_components':len(new),
        'new_reviewed_dependency_edges':1,'final_families_approved':0,
        'new_labels_read':False,'models_fitted':0,'protected_holdouts_touched':False}
    OUT.mkdir(parents=True)
    for name,obj in [('report.json',report),('belgium_first_review_addendum.json',addendum),
        ('family_dependency_addendum.json',family),('candidate_components.json',new),
        ('unresolved_identity_list.json',unresolved)]:
        (OUT/name).write_text(json.dumps(obj,indent=2)+'\n')
    # Only this directory should be given to the second reviewer.
    blind=OUT/'second_reviewer'; blind.mkdir()
    (blind/'packet.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in packet))
    (blind/'INSTRUCTIONS.md').write_text('''# Independent topic review

Review only packet.jsonl and these instructions. Do not inspect first-review or
automatic suggestions, price outcomes or performance reports. Fill reviewer,
topic, rationale, confidence and insufficient_context for each row. Use null topic
when evidence is insufficient. An independent person must supply these decisions;
a repeated pass by the first reviewer is not independent.

Allowed topics: politics_public_policy (elections/government/geopolitics),
macroeconomics (economic indicators and central-bank policy),
corporate_traditional_financial (company activity, earnings, equities, indices and
commodity-price outcomes), crypto (crypto assets/protocol-specific outcomes),
sports (matches, tournament performance, player/roster events and esports),
other_ambiguous (other subjects or unresolved boundaries).

Classify the actual contract outcome rather than incidental named entities.
Record cross-topic ambiguity. Cached metadata is context for review, not certified
historical availability. Do not mark family independence or source completeness.
Return all 30 rows. No deadline or agreement target is imposed.
''')
    (OUT/'manifest.json').write_text(json.dumps({'inputs':{str(p.relative_to(ROOT)):sha(p) for p in inputs},
        'outputs':{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
