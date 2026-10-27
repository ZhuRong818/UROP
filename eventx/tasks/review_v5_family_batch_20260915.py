"""Append three source-metadata family scopes; never certify unknown boundaries."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from eventx.tasks.certify_v5_family_graph import components, validate_split_certificate

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT/'data/v5/topic_coverage_triage_20260914/topic_review_queue.jsonl'
PRIOR = ROOT/'data/v5/review_followup_20260915/candidate_components.json'
OUT = ROOT/'data/v5/family_review_batch_20260915'

SCOPES = {
    'colombia_presidential_2026': [
        'kalshi:event:KXCOLOMBIAN2RMOV-COLOMBIAPRES26',
        'kalshi:event:KXCOLOMBIAPRES-26', 'polymarket:event:34582', 'polymarket:event:34584'],
    'los_angeles_mayoral_2026': ['kalshi:event:'+k for k in [
        'KXLAMAYOR1R-26','KXLAMAYORADVANCE-26JUN02','KXLAMAYORMATCHUP-26JUN',
        'KXLAMAYORPRIMARYEXACT-26JUN02','KXMAYORLA-26','KXPRATTCONCEDE-27JAN01',
        'KXPRIMARYMOV-MAYORLA2026','KXPRIMARYPLACE-MAYORLA26-2',
        'KXPRIMARYTURNOUT-MAYORLA26','KXRAMANPRATTDIFF-26JUN05',
        'KXVOTEPRIMARY-LAMAYOR1R26KBASKBAS','KXVOTEPRIMARY-LAMAYOR1R26NRAMNRAM',
        'KXVOTEPRIMARY-MAYORLA26SPRA']] + ['polymarket:event:485327','polymarket:event:57111'],
    'basketball_finals_2026': ['kalshi:event:'+k for k in [
        'KXNBA-26','KXNBA3PTALLGAMES-26NYKSASFIN1','KXNBA3PTALLGAMES-26NYKSASFIN2',
        'KXNBAPTSALLGAMES-26NYKSASFIN15','KXNBAPTSALLGAMES-26NYKSASFIN20',
        'KXNBAPTSALLGAMES-26NYKSASFIN25','KXNBASERIES3PMLEADER-26NYKSASFIN',
        'KXNBASERIESASTLEADER-26NYKSASFIN','KXNBASERIESGAMES-26NYKSASFIN',
        'KXNBASERIESGCOMEBACK-26NYKSASFIN','KXNBASERIESOT-26NYKSASFIN',
        'KXNBASERIESPTS-26NYKSASFIN','KXNBASERIESPTSLEADER-26NYKSASFIN',
        'KXNBASERIESREBLEADER-26NYKSASFIN','KXNBASERIESROADWINS-26NYKSASFIN',
        'KXNBASERIESSCORE-26NYKSASFIN','KXNBASERIESSPREAD-26NYKSASFIN']]
        + ['polymarket:event:27830','polymarket:event:375833'],
}
REASONS = {
    'colombia_presidential_2026': 'First round, runoff margin and final winner belong to the same named election across venues; stage dependence, not settlement equivalence.',
    'los_angeles_mayoral_2026': 'Primary counts/order/qualification, concession and final winner share the same election lifecycle across venues; concession is a dependent follow-up, not an equivalent outcome.',
    'basketball_finals_2026': 'Series outcome, length, spread, player statistics and Finals MVP share the named 2026 finals across venues; shared underlying games, not equivalent payouts.',
}

def build(groups, old):
    nodes = [n for c in old for n in c]
    assert len(nodes) == len(set(nodes)) == len(groups)
    assert set(nodes) == set(groups)
    previous = [(c[0], n) for c in old for n in c[1:]]
    edges, evidence = [], []
    for scope, ids in SCOPES.items():
        assert len(ids) == len(set(ids)) and set(ids) <= set(groups)
        identities = [{k:r.get(k) for k in ('market_id','venue','question','yes_sub_title','no_sub_title','candidate_family_id')}
                      for node in ids for r in groups[node]]
        links = [(ids[0], n) for n in ids[1:]]
        edges.extend(links)
        evidence.append({'scope':scope, 'candidate_event_ids':ids, 'must_links':links,
            'identities':identities, 'market_count':len(identities),
            'reviewer':'Codex metadata semantic review 2026-09-15',
            'reason':REASONS[scope], 'review_basis':'Cached questions, named YES subtitles and explicit event IDs',
            'boundary_review_complete':False, 'historical_metadata_certified':False,
            'remaining':'External/adjacent/season and multi-leg bridges; full versioned resolution semantics; independent review'})
    graph = components(nodes, previous+edges)
    mapping = {n:i for i,c in enumerate(graph) for n in c}
    certificate = validate_split_certificate(nodes, previous+edges, mapping, {n:False for n in nodes})
    assert certificate['graph_consistent'] and not certificate['final_family_certified']
    assert all(len({mapping[n] for n in c}) == 1 for c in old)
    assert components(list(reversed(nodes)), list(reversed(previous+edges))) == graph
    # Regression check: every new dependency must reject a split that separates it.
    for a,b in edges:
        bad = dict(mapping); bad[b] = 'intentionally-separated'
        try:
            validate_split_certificate(nodes, previous+edges, bad, {n:False for n in nodes})
        except ValueError:
            pass
        else:
            raise AssertionError('Known dependency incorrectly permitted across split')
    return graph, evidence, certificate, edges

def main():
    groups = defaultdict(list)
    for line in QUEUE.read_text().splitlines():
        row=json.loads(line); groups[row['candidate_family_id']].append(row)
    old=json.loads(PRIOR.read_text())
    graph,evidence,certificate,edges=build(groups,old)
    # Explicit boundary warnings, not certified negative edges or automatic merges.
    flags = [
        {'scope':'basketball_finals_2026', 'candidate_event_ids':['kalshi:event:KXNBA-27','polymarket:event:531028'],
         'reason':'Adjacent 2027 season and Trump attendance at Finals need separate temporal/context review; not automatically independent or merged.'},
        {'scope':'los_angeles_mayoral_2026', 'market_ids':['KXMAYORLA-26-KBAS'],
         'reason':'Named YES subtitle remains missing; family-level lifecycle association does not recover outcome identity.'},
        {'scope':'all', 'reason':'Multi-leg references and shared macro shocks may cross these components; unresolved boundaries block final certification.'}]
    report={'reviewed_scopes':len(evidence), 'reviewed_candidate_events':sum(len(x) for x in SCOPES.values()),
            'markets_in_reviewed_scopes':sum(x['market_count'] for x in evidence),
            'new_recorded_must_links':len(edges), 'prior_components':len(old),
            'updated_components':len(graph), 'final_approved_families':0,
            'graph_checks':certificate, 'rejected_split_tests':len(edges),
            'prior_links_preserved':True, 'order_invariance_passed':True,
            'prices_labels_or_holdouts_read':False, 'provider_contacted':False,
            'source_and_inference_gates_unchanged':True}
    OUT.mkdir(exist_ok=False)
    for name,value in [('reviewed_scopes.json',evidence),('candidate_components.json',graph),
                       ('boundary_flags.json',flags),('report.json',report)]:
        (OUT/name).write_text(json.dumps(value,indent=2)+'\n')
    inputs=[QUEUE,PRIOR,Path(__file__),ROOT/'eventx/tasks/certify_v5_family_graph.py']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT/'manifest.json').write_text(json.dumps({'inputs':{str(p.relative_to(ROOT)):sha(p) for p in inputs},
        'outputs':{p.name:sha(p) for p in OUT.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
