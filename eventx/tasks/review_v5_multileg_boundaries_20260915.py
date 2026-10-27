"""Inventory unresolved multi-leg identities and record explicit adjacent decisions."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT/'data/v5/topic_coverage_triage_20260914/topic_review_queue.jsonl'
PRIOR = ROOT/'data/v5/family_review_batch_20260915/candidate_components.json'
OUT = ROOT/'data/v5/multileg_boundary_review_20260915'

def main():
    rows = [json.loads(x) for x in QUEUE.read_text().splitlines()]
    graph = json.loads(PRIOR.read_text())
    membership = {n:i for i,g in enumerate(graph) for n in g}
    multi = [r for r in rows if 'multi_leg_dependency' in r.get('flags', [])]
    unresolved = []
    for r in multi:
        # These are display fragments, NOT resolved legs or an authoritative parser.
        fragments = re.split(r',\s*(?=(?:yes|no)\s)', r['question'], flags=re.I)
        unresolved.append({'market_id':r['market_id'], 'candidate_event_id':r['candidate_family_id'],
            'question':r['question'], 'display_fragments':fragments,
            'underlying_market_ids':None, 'decision':'unresolved',
            'reason':'Projected review queue lacks underlying contract IDs and dated per-leg resolution semantics',
            'required_evidence':['underlying market ID per leg','YES/NO polarity per leg',
                                 'event date/version','conjunction and cancellation rules'],
            'final_boundary_approved':False})
    assert len(multi) == 397
    scope_re = re.compile(r'Bass|Pratt|Raman|Cepeda|Espriella|Brunson|Wembanyama|New York|San Antonio',re.I)
    hits = [r['market_id'] for r in multi if scope_re.search(r['question'])]
    nextseason = [r for r in rows if r['candidate_family_id']=='kalshi:event:KXNBA-27']
    assert len(nextseason)==22 and all('2027' in r['question'] for r in nextseason)
    attendance = [r for r in rows if r['candidate_family_id']=='polymarket:event:531028']
    assert len(attendance)==1
    decisions = [
        {'left':'kalshi:event:KXNBA-26', 'right':'kalshi:event:KXNBA-27',
         'decision':'retain_distinct_event_identity_not_independence_certificate',
         'reason':'Explicit 2026 versus 2027 championship questions refer to different annual events; shared team names do not prove same settlement event.',
         'unresolved':'Cross-season team/roster dependence and shared-news exposure still need split/embargo treatment.',
         'evidence_market_ids':[r['market_id'] for r in nextseason],
         'final_boundary_approved':False},
        {'left':'kalshi:event:KXNBA-26', 'right':'polymarket:event:531028',
         'decision':'unresolved', 'reason':'Attendance question omits year and game/date; same phrase does not establish exact event or resolution window.',
         'evidence':attendance[0]['question'], 'final_boundary_approved':False}]
    assert membership['kalshi:event:KXNBA-26'] != membership['kalshi:event:KXNBA-27']
    statuses = []
    flagged_nodes = {r['candidate_event_id'] for r in unresolved}
    for g in graph:
        statuses.append({'component_id':'provisional-'+hashlib.sha256('|'.join(g).encode()).hexdigest()[:16],
            'candidate_event_ids':g, 'has_unresolved_multileg':bool(set(g)&flagged_nodes),
            'final_boundary_approved':False, 'v5_cohort_eligible':False,
            'eligibility_reason':'Not admitted: family/source/inference gates remain unresolved; not a permanent exclusion'})
    report = {'multileg_contracts_screened':len(multi),
        'multileg_prefix_counts':dict(Counter(r['market_id'].split('-')[0] for r in multi)),
        'underlying_id_mappings_resolved':0, 'unresolved_multileg_records':len(unresolved),
        'lexical_hits_to_prior_three_scopes':len(hits),
        'lexical_zero_does_not_prove_no_bridge':True,
        'adjacent_contracts_reviewed':len(nextseason)+len(attendance),
        'retained_distinct_event_pairs':1, 'unresolved_adjacent_pairs':1,
        'new_must_links':0, 'provisional_components':len(graph),
        'components_with_flagged_multileg':sum(r['has_unresolved_multileg'] for r in statuses),
        'final_approved_families':0,'source_or_inference_gate_waived':False,
        'prices_outcomes_or_holdouts_accessed':False, 'provider_contacted':False}
    OUT.mkdir(exist_ok=False)
    for name,value in [('candidate_components.json',graph),('adjacent_decisions.json',decisions),('report.json',report)]:
        (OUT/name).write_text(json.dumps(value,indent=2)+'\n')
    for name,value in [('unresolved_multileg.jsonl',unresolved),('component_review_status.jsonl',statuses)]:
        (OUT/name).write_text(''.join(json.dumps(r)+'\n' for r in value))
    # No evidence-supported new link: verify the graph really is unchanged.
    assert json.loads((OUT/'candidate_components.json').read_text()) == graph
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT/'manifest.json').write_text(json.dumps({'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [QUEUE,PRIOR,Path(__file__)]},
        'outputs':{p.name:sha(p) for p in OUT.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
