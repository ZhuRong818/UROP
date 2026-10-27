"""Validate two real responses without adjudicating or creating semantic gold."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/v7/macro_pilot_20261010'
SUP=ROOT/'data/v7/macro_metadata_20261010'
ENUMS={
    'applicability':{'exact_predicate','material_context','topic_only','incompatible','unknown'},
    'role':{'official_measurement_or_action','attributed_reporting','opinion_or_forecast','market_odds_reporting','mixed','unknown'},
    'direction':{'yes','no','ambiguous','not_applicable','unknown'},
    'novelty':{'new_in_supplied_context','repeat_in_supplied_context','update_in_supplied_context','unknown'},
    'market_odds_content':{'yes','no','mixed','unknown'}}


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(p):return [json.loads(x) for x in p.open()]


def span_ok(s, fields):
    f=s.get('field');a=s.get('start');b=s.get('end');t=s.get('text')
    return (f in fields and isinstance(a,int) and isinstance(b,int) and not isinstance(a,bool)
            and not isinstance(b,bool) and 0<=a<b<=len(fields[f] or '') and isinstance(t,str)
            and (fields[f] or '')[a:b]==t)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reviewer-a',type=Path,required=True)
    ap.add_argument('--reviewer-b',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    out=args.output.resolve()
    if not out.is_relative_to(ROOT/'data/v7') or out.exists():
        raise ValueError('Use a fresh output directory under data/v7')
    for folder,name in [(BASE,'manifest.json'),(SUP,'supplement_manifest.json')]:
        m=json.loads((folder/name).read_text())
        for f,h in m['outputs'].items():
            if sha(folder/f)!=h:raise ValueError('Review input changed: '+f)
    packet={r['pair_id']:r for r in read(SUP/'packet_with_rules.jsonl')}
    errors=[];answers=[];identities=[]
    for label,path in [('A',args.reviewer_a),('B',args.reviewer_b)]:
        rows=read(path);ids=[r.get('pair_id') for r in rows]
        if len(ids)!=len(packet) or len(set(ids))!=len(ids) or set(ids)!=set(packet):
            errors.append(label+': ID coverage/uniqueness failure')
        reviewers={r.get('reviewer_id') for r in rows}
        if len(reviewers)!=1 or not next(iter(reviewers),None):errors.append(label+': reviewer identity missing or mixed')
        identities.append(reviewers)
        mapped={}
        for r in rows:
            pid=r.get('pair_id');p=packet.get(pid)
            if p is None:continue
            prefix=label+': '+pid+': '
            if r.get('reviewer_kind')!='human' or r.get('independent_of_other_reviewer') is not True or r.get('outcome_blind') is not True:
                errors.append(prefix+'human independence/blinding attestation absent')
            if r.get('prior_exposure') not in {'none','some','unknown'}:errors.append(prefix+'prior exposure not recorded')
            for field,allowed in ENUMS.items():
                if r.get(field) not in allowed:errors.append(prefix+'invalid '+field)
            if r.get('public_surprise')!='unknown':errors.append(prefix+'no prior supplied for measured surprise')
            if not isinstance(r.get('episode_key'),str) or not r['episode_key'].strip():errors.append(prefix+'episode identity/unknown missing')
            if not isinstance(r.get('rationale'),str) or not r['rationale'].strip():errors.append(prefix+'rationale missing')
            fields={k:p['article'].get(k) for k in ('headline','summary')}
            cfields={k:p['contract'].get(k) for k in ('question','yes_subtitle')}
            cfields.update({x['field']:x['text'] for x in p['rules']})
            for s in r.get('evidence_spans',[]):
                if not span_ok(s,fields):errors.append(prefix+'invalid article span')
            for s in r.get('contract_spans',[]):
                if not span_ok(s,cfields):errors.append(prefix+'invalid contract span')
            prior={x['article_id']:x for x in p['earlier_reports']}
            for s in r.get('prior_evidence_spans',[]):
                a=prior.get(s.get('article_id'))
                if a is None or not span_ok(s,{k:a.get(k) for k in ('headline','summary')}):errors.append(prefix+'invalid prior span')
            if r.get('applicability') in {'exact_predicate','material_context'} or r.get('direction') in {'yes','no'}:
                if not r.get('evidence_spans') or not r.get('contract_spans'):errors.append(prefix+'material/directional label needs both article and contract evidence')
            if r.get('novelty') in {'repeat_in_supplied_context','update_in_supplied_context'} and not r.get('prior_evidence_spans'):
                errors.append(prefix+'repeat/update needs earlier evidence')
            if r.get('duplicate_of') is not None and r['duplicate_of'] not in prior:errors.append(prefix+'duplicate references unsupplied article')
            mapped[pid]=r
        answers.append(mapped)
    if identities[0]&identities[1]:errors.append('Reviewers must have distinct IDs')
    out.mkdir(parents=True)
    for label,path in [('A',args.reviewer_a),('B',args.reviewer_b)]:
        (out/('reviewer_'+label+'_submitted.jsonl')).write_bytes(path.read_bytes())
    disagreements=[];agreement={}
    if not errors:
        fields=[*ENUMS,'episode_key','duplicate_of']
        agreement={field:{'agree':sum(answers[0][p][field]==answers[1][p][field] for p in packet),'total':len(packet)} for field in fields}
        disagreements=[{'pair_id':p,'fields':[f for f in fields if answers[0][p][f]!=answers[1][p][f]],
                        'reviewer_A':answers[0][p],'reviewer_B':answers[1][p]} for p in packet
                       if any(answers[0][p][f]!=answers[1][p][f] for f in fields)]
        (out/'adjudication_packet.jsonl').write_text(''.join(json.dumps({**r,'adjudicator_id':None,'final_decision':None,'reason':None})+'\n' for r in disagreements))
    report={'received_at':datetime.now(timezone.utc).isoformat(),'status':'invalid_or_incomplete' if errors else 'two_reviews_structurally_valid_pending_adjudication',
        'errors':errors,'field_agreement':agreement,'disagreement_pairs':len(disagreements),
        'reviewer_independence':'user_attested_not_independently_verified','semantic_accuracy_estimated':False,
        'admitted_predictive_rows':0,'source_hashes':{str(p):sha(p) for p in [args.reviewer_a,args.reviewer_b,SUP/'packet_with_rules.jsonl']}}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('errors','source_hashes')},indent=2))
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
