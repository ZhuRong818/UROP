"""Validate and compare two separate agent relevance reviews without outcomes."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import json,shutil
from eventx.tasks.run_v5_residual_feasibility import REPO_ROOT,sha256_file,read_jsonl
from eventx.tasks.diagnose_v7_signed_evidence_coverage_20261012 import write_json,write_jsonl

OUT=REPO_ROOT/'data/v7/event_relevance_review_20261015'
TEMP=Path('/private/tmp/eventx_blind_review_20261015')
RELEVANCE={'exact_predicate','material_context','shared_background','irrelevant','insufficient'}
ROLE={'reported_measurement','official_statement','attributed_forecast','market_expectations','analysis_or_recap','investment_commentary','calendar_preview','mixed','insufficient'}
RISKS={'explicit_past_background','market_odds_repetition','possible_recap','none_identified'}

def main():
    if (OUT/'comparison.json').exists():raise SystemExit('Preserve completed comparison')
    receipt=json.loads((OUT/'pre_review_receipt.json').read_text())
    packets={};responses={};validation={}
    for label in ['A','B']:
        path=OUT/f'packet_{label}.jsonl'
        if sha256_file(path)!=receipt['packets'][label]:raise RuntimeError('Packet changed')
        rows=list(read_jsonl(path));packet={r['pair_id']:r for r in rows};packets[label]=packet
        src=TEMP/label/'completed.jsonl';notes=TEMP/label/'review_notes.md'
        dest=OUT/f'reviewer_{label}_completed.jsonl'
        if dest.exists():raise RuntimeError('Preserve original submission')
        shutil.copyfile(src,dest)
        if notes.exists():shutil.copyfile(notes,OUT/f'reviewer_{label}_notes.md')
        result=list(read_jsonl(dest));errors=[];seen=set();quotes=0
        for row in result:
            pair=row.get('pair_id');record=packet.get(pair)
            if pair in seen:errors.append([pair,'duplicate pair'])
            seen.add(pair)
            if record is None:errors.append([pair,'unknown pair']);continue
            if row.get('article_id')!=record['article_id']:errors.append([pair,'article ID mismatch'])
            if row.get('reviewer_id')!=f'Agent_{label}_20261015' or row.get('reviewer_kind')!='assistant':errors.append([pair,'reviewer provenance'])
            if row.get('relevance') not in RELEVANCE:errors.append([pair,'relevance enum'])
            if row.get('article_role') not in ROLE:errors.append([pair,'role enum'])
            if row.get('novelty')!='unknown':errors.append([pair,'unjustified novelty claim'])
            if row.get('repetition_risk') not in RISKS:errors.append([pair,'repetition enum'])
            if not row.get('rationale') or not isinstance(row.get('contract_ambiguities'),list):errors.append([pair,'missing rationale/ambiguities'])
            direction=row.get('exact_direction')
            if row.get('relevance')!='exact_predicate' and direction is not None:errors.append([pair,'signed nonexact evidence'])
            if row.get('relevance')=='exact_predicate' and direction not in (-1,1):errors.append([pair,'exact missing direction'])
            ev=row.get('evidence')
            if not isinstance(ev,list) or not ev:errors.append([pair,'no quoted evidence']);continue
            for item in ev:
                field=item.get('field');quote=item.get('quote')
                if field not in ('headline','summary') or not quote or quote not in record.get(field,''):errors.append([pair,'nonmatching evidence quotation'])
                else:quotes+=1
            ep=row.get('episode_evidence')
            if row.get('episode_hypothesis') is not None and (not ep or (ep not in record['headline'] and ep not in record['summary'])):errors.append([pair,'nonmatching episode evidence'])
        if seen!=set(packet):errors.append(['coverage','missing/extra IDs'])
        validation[label]={'rows':len(result),'unique_pairs':len(seen),'matching_evidence_quotes':quotes,'errors':errors,'submitted_sha256':sha256_file(dest)}
        responses[label]={r['pair_id']:r for r in result}
    write_json(OUT/'validation.json',validation)
    if any(v['errors'] for v in validation.values()):raise RuntimeError('Submission validation failed, originals preserved; inspect errors')
    if set(packets['A'])!=set(packets['B']):raise RuntimeError('Review packets differ in pair membership')
    a,b=responses['A'],responses['B'];packet=packets['A'];records=[]
    confusion=Counter();disagreements=[];agreed=[]
    for pair,p in sorted(packet.items()):
        ra,rb=a[pair],b[pair];agreement=ra['relevance']==rb['relevance'];confusion[(ra['relevance'],rb['relevance'])]+=1
        both_context=all(r['relevance'] in ('material_context','exact_predicate') for r in (ra,rb))
        rec={'pair_id':pair,'article_id':p['article_id'],'market_id':p['contract']['market_id'],'headline':p['headline'],'question':p['contract']['question'],'reviewer_A_relevance':ra['relevance'],'reviewer_B_relevance':rb['relevance'],'relevance_agrees':agreement,'both_material_or_exact':both_context,'reviewer_A':ra,'reviewer_B':rb}
        records.append(rec)
        if not agreement:disagreements.append(rec)
        if both_context:agreed.append(rec)
    comparison={'status':'two_assistant_reviews_complete','created_at':datetime.now(timezone.utc).isoformat(),'pairs':len(records),'articles':len({r['article_id'] for r in records}),'reviewer_relevance_counts':{k:dict(Counter(r['relevance'] for r in v.values())) for k,v in responses.items()},'pair_relevance_agreement':sum(r['relevance_agrees'] for r in records),'pair_relevance_disagreements':len(disagreements),'article_role_agreement':sum(a[k]['article_role']==b[k]['article_role'] for k in a),'confusion':[{'A':x,'B':y,'pairs':n} for (x,y),n in sorted(confusion.items())],'both_material_or_exact_pairs':len(agreed),'both_material_or_exact_articles':len({r['article_id'] for r in agreed}),'both_exact_pairs':sum(a[k]['relevance']==b[k]['relevance']=='exact_predicate' for k in a),'human_review_gate_satisfied':False,'episode_independence_certified':False,'judgments_used_outcomes':False,'root_prior_aggregate_exposure':True,'limits':['Separate fresh-context agents with common model family, not independent humans.','Agreement is not semantic accuracy, novelty or source certification.','Selected 32-article sample is not representative retrieval precision/recall.','Outcome-hidden review cannot establish forecasting improvement.']}
    write_jsonl(OUT/'pair_comparison.jsonl',records);write_jsonl(OUT/'disagreements.jsonl',disagreements);write_jsonl(OUT/'agreed_context_pairs.jsonl',agreed);write_json(OUT/'comparison.json',comparison)
    write_json(OUT/'comparison_manifest.json',{'artifacts':[{'path':str(p.relative_to(REPO_ROOT)),'sha256':sha256_file(p)} for p in list(OUT.iterdir())+[Path(__file__)] if p.is_file()]})
    print(json.dumps(comparison,indent=2))

if __name__=='__main__':main()
