"""Validate independent V6 development responses; never score an audit or forecast."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'data/v6/context_development_review_20260927'
LABEL_KEYS = {'semantic_relation':'semantic_labels', 'contract_applicability':'applicability_labels',
              'claim_role':'claim_role_labels', 'settlement_evidence':'settlement_evidence_labels'}
ARTICLE_FIELDS = {'headline','summary'}
CONTRACT_FIELDS = {'contract_question','yes_subtitle'}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def packet_integrity() -> tuple[list[dict],dict]:
    manifest=json.loads((PACKET/'manifest.json').read_text())
    for name,digest in manifest['outputs'].items():
        assert sha(PACKET/name)==digest, f'packet hash mismatch: {name}'
    for name,digest in manifest['inputs'].items():
        assert sha(ROOT/name)==digest, f'input hash mismatch: {name}'
    packet=read_jsonl(PACKET/'semantic_packet.jsonl')
    assert len(packet)==102 and len({r['pair_id'] for r in packet})==102
    return packet,json.loads((PACKET/'spec.json').read_text())

def span_text(pair: dict, field: str) -> str | None:
    if field in ARTICLE_FIELDS | CONTRACT_FIELDS:
        return pair.get(field)
    if field.startswith('contract_rules[') and field.endswith('].text'):
        number=field[len('contract_rules['):-len('].text')]
        if number.isdecimal():
            index=int(number)
            rules=pair.get('contract_rules',[])
            if index<len(rules): return rules[index].get('text')
    return None

def validate_spans(pair: dict, spans: object, article: bool, prefix: str, errors: list[str]) -> None:
    if not isinstance(spans,list):
        errors.append(prefix+': spans must be an array')
        return
    for index,span in enumerate(spans):
        label=f'{prefix}: span {index}'
        if not isinstance(span,dict):
            errors.append(label+' must be an object');continue
        field=span.get('field')
        allowed=field in ARTICLE_FIELDS if article else (field in CONTRACT_FIELDS or isinstance(field,str) and field.startswith('contract_rules['))
        if not allowed:
            errors.append(label+': invalid field');continue
        source=span_text(pair,field)
        start,end,quote=span.get('start'),span.get('end'),span.get('quote')
        if not isinstance(source,str) or not isinstance(start,int) or isinstance(start,bool) or not isinstance(end,int) or isinstance(end,bool) or not isinstance(quote,str):
            errors.append(label+': missing source or invalid offset/quote');continue
        if not (0<=start<end<=len(source)) or source[start:end]!=quote:
            errors.append(label+': quote does not match exact source offsets')

def validate_file(path: Path, packet: list[dict], spec: dict) -> tuple[list[str],str|None]:
    errors=[]
    pairs={r['pair_id']:r for r in packet}
    rows=read_jsonl(path)
    if len(rows)!=len(packet):errors.append(f'{path.name}: expected 102 rows, got {len(rows)}')
    ids=[r.get('pair_id') for r in rows]
    if len(set(ids))!=len(ids):errors.append(f'{path.name}: duplicate pair IDs')
    if set(ids)!=set(pairs):errors.append(f'{path.name}: pair ID set differs from frozen packet')
    reviewer_ids=set()
    for r in rows:
        pid=r.get('pair_id');pair=pairs.get(pid)
        if pair is None:continue
        prefix=f'{path.name}:{pid}'
        reviewer=r.get('reviewer_id')
        if not isinstance(reviewer,str) or not reviewer.strip():errors.append(prefix+': reviewer_id missing')
        else:reviewer_ids.add(reviewer)
        for label,spec_key in LABEL_KEYS.items():
            if r.get(label) not in spec[spec_key]:errors.append(prefix+f': invalid {label}')
        rationale=r.get('rationale')
        if not isinstance(rationale,str) or not rationale.strip():errors.append(prefix+': rationale missing')
        if r.get('semantic_relation')=='unknown' or r.get('contract_applicability')=='unknown':
            reason=r.get('uncertain_reason')
            if not isinstance(reason,str) or not reason.strip():errors.append(prefix+': unknown requires uncertain_reason')
        a=r.get('article_evidence_spans');c=r.get('contract_evidence_spans')
        validate_spans(pair,a,True,prefix+':article',errors)
        validate_spans(pair,c,False,prefix+':contract',errors)
        if r.get('semantic_relation') in {'same_event_update','shared_mechanism_context'} or r.get('contract_applicability') in {'direct_proposition','shared_context_only'}:
            if not a or not c:errors.append(prefix+': positive relation/applicability requires article and contract spans')
    if len(reviewer_ids)>1:errors.append(f'{path.name}: multiple reviewer IDs in one response')
    return errors,next(iter(reviewer_ids)) if len(reviewer_ids)==1 else None

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--check-template',action='store_true')
    parser.add_argument('--reviewer-a',type=Path)
    parser.add_argument('--reviewer-b',type=Path)
    args=parser.parse_args()
    packet,spec=packet_integrity()
    if args.check_template:
        for name in ('reviewer_A_blank.jsonl','reviewer_B_blank.jsonl'):
            rows=read_jsonl(PACKET/name)
            assert [r['pair_id'] for r in rows]==[r['pair_id'] for r in packet]
            assert all(r['reviewer_id'] is None and all(r[k] is None for k in LABEL_KEYS) for r in rows)
        print(json.dumps({'packet_rows':102,'packet_hashes_valid':True,'blank_forms_valid':True}))
        return 0
    if not args.reviewer_a or not args.reviewer_b:parser.error('provide both completed reviewer files or --check-template')
    if args.reviewer_a.resolve()==args.reviewer_b.resolve():parser.error('reviewer files must differ')
    a_errors,a_id=validate_file(args.reviewer_a,packet,spec)
    b_errors,b_id=validate_file(args.reviewer_b,packet,spec)
    errors=a_errors+b_errors
    if a_id and b_id and a_id==b_id:errors.append('reviewer IDs must be distinct')
    report={'valid':not errors,'packet_sha256':sha(PACKET/'semantic_packet.jsonl'),
            'reviewer_a_sha256':sha(args.reviewer_a),'reviewer_b_sha256':sha(args.reviewer_b),
            'reviewer_a_id':a_id,'reviewer_b_id':b_id,'errors':errors}
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0 if not errors else 2

if __name__=='__main__':raise SystemExit(main())
