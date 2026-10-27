"""Fixed, opened-development L0/L1/L2 retrieval and ranking comparison."""
from __future__ import annotations

import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from eventx.v6.clean_speech import clean
from eventx.v6.field_aware import fields, query, hypothesis, top_set

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'data/v6/enriched_rule_comparison_20260921'
ARTICLES = ROOT/'data/v6/expanded_coverage_20260919'
PRIOR = ROOT/'data/v6/field_aware_trial_20260921'
MODELS = ROOT/'data/v6/local_models_20260916'
OUT = ROOT/'data/v6/fixed_pipeline_comparison_20260926'
TOP_K = 5
TOL = 1e-12


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path: Path):
    with path.open() as stream:
        return [json.loads(x) for x in stream if x.strip()]


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


def write_jsonl(path: Path, rows) -> None:
    with path.open('w') as stream:
        for row in rows:
            stream.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n')


def verify_sources() -> None:
    for base in (BASE, ARTICLES, PRIOR):
        manifest = json.loads((base/'manifest.json').read_text())
        for name, expected in manifest.get('outputs', manifest).items():
            assert digest(base/name) == expected, f'changed source: {base/name}'
    manifest = json.loads((MODELS/'manifest.json').read_text())
    for model in manifest['models']:
        for name, expected in model['files'].items():
            assert digest(ROOT/model['path']/name)==expected, f'changed model: {name}'


def input_hashes():
    paths = [Path(__file__), ROOT/'eventx/v6/field_aware.py',
             ROOT/'eventx/v6/clean_speech.py', BASE/'manifest.json', BASE/'cards.jsonl',
             BASE/'scores.jsonl', ARTICLES/'manifest.json', ARTICLES/'articles.jsonl',
             PRIOR/'manifest.json', PRIOR/'ranks.jsonl', MODELS/'manifest.json']
    return {str(p.relative_to(ROOT)):digest(p) for p in paths}


def prepare() -> None:
    assert not OUT.exists(), 'version already exists'
    verify_sources()
    old = read(BASE/'scores.jsonl')
    article_ids = sorted({r['article_id'] for r in old})
    cards = read(BASE/'cards.jsonl')
    assert len(old)==185 and len(article_ids)==70 and len(cards)==134
    assert len({c['contract_id'] for c in cards})==134
    all_articles = {a['article_id']:a for a in read(ARTICLES/'articles.jsonl')}
    assert all(a in all_articles for a in article_ids)
    OUT.mkdir(parents=True)
    model = json.loads((MODELS/'manifest.json').read_text())['models']
    spec = {
        'version':'v6-fixed-L0-L1-L2-v0.1-development-20260926',
        'scope':'70 opened development articles, 134 retrospective enriched cards; no reserved/protected labels or outcomes',
        'legacy_pairs':185,'article_ids':article_ids,
        'card_ids':sorted(c['contract_id'] for c in cards),
        'retrieval':'for each article, union all legacy screened pairs, top 5 positive full-rule TF-IDF pairs, top 5 dense cosine pairs across the same 134 cards; tie by contract ID',
        'tfidf':'shared vocabulary fit to question/subtitle and full-rule versions of all 134 cards; English stop words, 1-2 grams',
        'L0':'full-rule TF-IDF on common union; lexical rank only, no acceptance gate',
        'L1':'question/subtitle TF-IDF on common union, only where unchanged field_aware.hypothesis is non-abstain',
        'L2':'pinned cross-encoder on same typed-supported common union; dense-only additions reported separately from reranking on the base union',
        'base_union':'legacy pairs plus top 5 positive full-rule TF-IDF; expansion adds top 5 dense cosine',
        'top_k':TOP_K,'absolute_tie_tolerance':TOL,
        'encoder_revision':next(x['revision'] for x in model if x['path'].endswith('/encoder')),
        'reranker_revision':next(x['revision'] for x in model if x['path'].endswith('/reranker')),
        'model_runtime':'CPU, four threads; encoder float64, reranker bfloat16/eager, seed 20260926; offline only',
        'outputs':'all pair scores/hypotheses, article-level top sets, candidate-source flags and aggregate counts; no precision/recall without new references',
        'admission':0,'predictive_fits':0,
    }
    write_json(OUT/'spec.json',spec)
    write_json(OUT/'receipt.json',{
        'created_at':datetime.now(timezone.utc).isoformat(),
        'inputs':input_hashes(),'spec_sha256':digest(OUT/'spec.json'),
        'receipt_written_before_inference':True})
    print(json.dumps({'prepared':True,'articles':len(article_ids),'cards':len(cards)}),flush=True)


def top_positive(values, ids, k):
    ordered = sorted(range(len(ids)),key=lambda i:(-float(values[i]),ids[i]))
    return [i for i in ordered if float(values[i])>TOL][:k]


def rank_set(rows, key, allowed=None):
    if allowed is not None:
        rows=[r for r in rows if r['contract_id'] in allowed]
    return top_set(rows,key,tolerance=TOL)


def run() -> None:
    import torch
    from sentence_transformers import SentenceTransformer, CrossEncoder

    assert OUT.exists() and {p.name for p in OUT.iterdir()}=={'spec.json','receipt.json'}
    receipt=json.loads((OUT/'receipt.json').read_text())
    assert receipt['receipt_written_before_inference']
    assert receipt['inputs']==input_hashes()
    assert receipt['spec_sha256']==digest(OUT/'spec.json')
    verify_sources()
    spec=json.loads((OUT/'spec.json').read_text())
    assert spec['top_k']==TOP_K and spec['absolute_tie_tolerance']==TOL
    cards=sorted(read(BASE/'cards.jsonl'),key=lambda c:c['contract_id'])
    card_ids=[c['contract_id'] for c in cards]
    assert card_ids==spec['card_ids']
    old=read(BASE/'scores.jsonl')
    legacy=defaultdict(set)
    for row in old:
        legacy[row['article_id']].add(row['contract_id'])
    all_articles={a['article_id']:a for a in read(ARTICLES/'articles.jsonl')}
    articles=[all_articles[aid] for aid in spec['article_ids']]
    assert len(articles)==70 and len(old)==185
    typed={c['contract_id']:fields(c) for c in cards}
    short=[query(typed[cid]) for cid in card_ids]
    full=[short[i]+'\n'+'\n'.join(e['text'] for e in card['recovered_rule_evidence'])
          for i,card in enumerate(cards)]
    article_text=['\n'.join(clean(a)[0].get(k) or '' for k in ('headline','summary')) for a in articles]
    vectorizer=TfidfVectorizer(stop_words='english',ngram_range=(1,2))
    vectorizer.fit(short+full)
    xs=vectorizer.transform(article_text)
    qmat=vectorizer.transform(short)
    fmat=vectorizer.transform(full)
    qs=(xs@qmat.T).toarray()
    fs=(xs@fmat.T).toarray()
    assert qs.shape==fs.shape==(70,134) and np.isfinite(qs).all() and np.isfinite(fs).all()
    card_ix={cid:i for i,cid in enumerate(card_ids)}
    article_ix={aid:i for i,aid in enumerate(spec['article_ids'])}
    assert all(abs(float(qs[article_ix[r['article_id']],card_ix[r['contract_id']]])-r['question_score'])<1e-10 and abs(float(fs[article_ix[r['article_id']],card_ix[r['contract_id']]])-r['enriched_score'])<1e-10 for r in old), 'legacy TF-IDF score reproduction failed'
    torch.set_num_threads(4)
    torch.manual_seed(20260926)
    encoder=SentenceTransformer(str(MODELS/'encoder'),device='cpu',local_files_only=True,
                                model_kwargs={'attn_implementation':'eager'})
    encoder.double()
    cv=encoder.encode(short,normalize_embeddings=True,batch_size=32,show_progress_bar=False)
    av=encoder.encode(article_text,normalize_embeddings=True,batch_size=32,show_progress_bar=False)
    dense=av@cv.T
    assert dense.shape==(70,134) and np.isfinite(dense).all()
    print('encoded 70 articles and 134 cards',flush=True)
    id_to_ix={cid:i for i,cid in enumerate(card_ids)}
    pair_rows=[]
    union_by_article={}
    for ai,article in enumerate(articles):
        aid=article['article_id']
        lexical={card_ids[i] for i in top_positive(fs[ai],card_ids,TOP_K)}
        dense_top={card_ids[i] for i in sorted(range(len(card_ids)),
                        key=lambda i:(-float(dense[ai,i]),card_ids[i]))[:TOP_K]}
        base=legacy[aid]|lexical
        union=base|dense_top
        union_by_article[aid]=(base,union,dense_top,lexical)
        for cid in sorted(union):
            ci=id_to_ix[cid]
            h=hypothesis(article,typed[cid])
            supported=h['status']!='abstain'
            pair_rows.append({
                'article_id':aid,'contract_id':cid,
                'legacy_pair':cid in legacy[aid],
                'top5_positive_full_rule':cid in lexical,
                'top5_dense':cid in dense_top,
                'dense_only_expansion':cid not in base,
                'l0':float(fs[ai,ci]),
                'l1':float(qs[ai,ci]) if supported else None,
                'l2':None,'dense_cosine':float(dense[ai,ci]),
                'field_hypothesis':h,'predictive_admitted':False,
            })
    eligible=[r for r in pair_rows if r['l1'] is not None]
    reranker=CrossEncoder(str(MODELS/'reranker'),device='cpu',max_length=384,
                          local_files_only=True,model_kwargs={'attn_implementation':'eager'})
    reranker.model.bfloat16()
    rerank_inputs=[(short[id_to_ix[r['contract_id']]],article_text[spec['article_ids'].index(r['article_id'])])
                   for r in eligible]
    if rerank_inputs:
        score=reranker.predict(rerank_inputs,batch_size=16,show_progress_bar=False,
                               activation_fn=torch.nn.Identity())
        assert np.isfinite(score).all()
        for row,value in zip(eligible,score):
            row['l2']=float(value)
    print(f'reranked {len(eligible)} typed hypotheses',flush=True)
    groups=defaultdict(list)
    for row in pair_rows: groups[row['article_id']].append(row)
    article_results=[]
    for aid in spec['article_ids']:
        rows=groups[aid]
        base,union,dense_top,lexical=union_by_article[aid]
        article_results.append({
            'article_id':aid,'legacy_candidates':len(legacy[aid]),
            'base_candidates':len(base),'union_candidates':len(union),
            'dense_only_candidates':len(union-base),
            'base_typed_hypotheses':sum(r['l1'] is not None and r['contract_id'] in base for r in rows),
            'new_dense_typed_hypotheses':sum(r['l1'] is not None and r['contract_id'] not in base for r in rows),
            'l0_top_union':rank_set(rows,'l0'),
            'l1_top_base':rank_set(rows,'l1',base),
            'l1_top_union':rank_set(rows,'l1'),
            'l2_top_base':rank_set(rows,'l2',base),
            'l2_top_union':rank_set(rows,'l2'),
        })
    by_field=Counter(r['field_hypothesis']['status'] for r in pair_rows)
    report={
        'articles':len(articles),'cards':len(cards),'legacy_pairs':len(old),
        'common_union_pairs':len(pair_rows),
        'base_pairs':sum(x['base_candidates'] for x in article_results),
        'dense_only_added_pairs':sum(x['dense_only_candidates'] for x in article_results),
        'typed_hypotheses':len(eligible),'typed_hypotheses_by_status':dict(by_field),
        'articles_with_typed_hypotheses':sum(bool(x['l1_top_union']) for x in article_results),
        'base_articles_with_typed_hypotheses':sum(bool(x['l1_top_base']) for x in article_results),
        'dense_only_typed_hypotheses':sum(x['new_dense_typed_hypotheses'] for x in article_results),
        'articles_newly_with_typed_hypotheses_after_dense':sum(not x['l1_top_base'] and bool(x['l1_top_union']) for x in article_results),
        'reranker_changed_top_on_base':sum(bool(x['l1_top_base']) and x['l1_top_base']!=x['l2_top_base'] for x in article_results),
        'reranker_changed_top_on_union':sum(bool(x['l1_top_union']) and x['l1_top_union']!=x['l2_top_union'] for x in article_results),
        'dense_expansion_changed_l2_top':sum(x['l2_top_base']!=x['l2_top_union'] for x in article_results),
        'l0_tied_top_articles':sum(len(x['l0_top_union'])>1 for x in article_results),
        'predictive_admissions':0,'accuracy_reference_available':False,
        'interpretation':'candidate/hypothesis coverage and ranking differences only; no revised-context human gold or point-in-time certification',
    }
    write_jsonl(OUT/'pairs.jsonl',pair_rows)
    write_jsonl(OUT/'articles.jsonl',article_results)
    write_json(OUT/'report.json',report)
    write_json(OUT/'runtime.json',{
        'packages':{name:importlib.metadata.version(name) for name in
                    ('numpy','scikit-learn','torch','transformers','sentence-transformers')},
        'encoder_revision':spec['encoder_revision'],
        'reranker_revision':spec['reranker_revision'],
        'device':'cpu','encoder_dtype':'float64','reranker_dtype':'bfloat16',
    })
    write_json(OUT/'manifest.json',{'inputs':receipt['inputs'],
        'outputs':{p.name:digest(p) for p in OUT.iterdir() if p.name!='manifest.json'}})
    print(json.dumps(report,indent=2,sort_keys=True),flush=True)

if __name__=='__main__':
    assert len(sys.argv)==2 and sys.argv[1] in ('prepare','run')
    (prepare if sys.argv[1]=='prepare' else run)()
