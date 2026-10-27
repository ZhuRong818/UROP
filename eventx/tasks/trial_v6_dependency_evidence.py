"""Isolated dependency-parser development trial with full runtime/model hashes."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import spacy
import en_core_web_sm
from eventx.v6.dependency_evidence import extract
from eventx.v6.structured_evidence import validate_spans


def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return [json.loads(s) for s in p.read_text().splitlines()]


def main():
    base = Path('data/v6/evidence_binding_comparison_20260921')
    old = Path('data/v6/structured_evidence_trial_20260924')
    for root in (base, old):
        m = json.loads((root/'manifest.json').read_text())
        for n,h in m['inputs'].items(): assert digest(Path(n)) == h
        for n,h in m['outputs'].items(): assert digest(root/n) == h
    assert spacy.__version__ == '3.8.7'
    nlp = en_core_web_sm.load()
    assert nlp.meta['version'] == '3.8.0'
    out = Path('data/v6/dependency_evidence_trial_20260924'); out.mkdir(exist_ok=False)
    model_root = Path(en_core_web_sm.__file__).parent
    provenance = {'spacy': spacy.__version__, 'model_meta': nlp.meta,
                  'model_source': 'https://github.com/explosion/spacy-models/releases/tag/en_core_web_sm-3.8.0',
                  'historical_availability': 'not_certified; retrospective development only',
                  'model_hashes': {str(p.relative_to(model_root)): digest(p) for p in model_root.rglob('*') if p.is_file() and '__pycache__' not in str(p)},
                  'packages': sorted(f'{d.metadata["Name"]}=={d.version}' for d in importlib.metadata.distributions())}
    (out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    synthetic, opened = [], []
    for r in read(base/'synthetic_scores.jsonl'):
        a = {'headline': r['text'], 'summary': ''}; e=extract(a,nlp); validate_spans(e,a)
        synthetic.append({'scenario':r['scenario'],'variant':r['variant'],'structured':e})
    for a in read(base/'opened_inventory.jsonl'):
        e=extract(a,nlp); validate_spans(e,a)
        opened.append({'article_id':a['article_id'],'structured':e})
    tests = [
        ('passive', 'Copper was purchased by a pension fund.'),
        ('postposed', 'Copper will rise, says analyst.'),
        ('contraction', 'It will not matter. It won’t matter.'),
        ('nominal', 'The company celebrates design wins.'),
        ('forecast', 'The economist expects copper to appreciate.'),
    ]
    regression=[]
    for name,text in tests:
        a={'headline':text};e=extract(a,nlp);validate_spans(e,a)
        regression.append({'name':name,'text':text,'structured':e})
    c=regression[0]['structured']['claims'][0]
    checks={'passive_actor':c['actor']['value']=='a pension fund', 'passive_object':c['object']['value']=='Copper',
            'postposed_speaker':any(c['speaker']['value']=='analyst' for c in regression[1]['structured']['claims']),
            'no_contraction_win':not any(c['predicate']['value'].lower()=='won' for c in regression[2]['structured']['claims']),
            'no_nominal_win':not any(c['predicate']['value'].lower()=='wins' for c in regression[3]['structured']['claims']),
            'forecast_status':any(c['epistemic_status']['value']=='forecast' for c in regression[4]['structured']['claims'])}
    def counts(rr):return {'documents':len(rr),'documents_with_predicate':sum(bool(r['structured']['claims']) for r in rr), 'predicate_candidates':sum(len(r['structured']['claims']) for r in rr)}
    report={'synthetic':counts(synthetic),'opened':counts(opened),'regression_checks':checks,
            'admissions':0,'scope':'coverage and synthetic field checks only; no relevance accuracy'}
    for name,rr in [('synthetic',synthetic),('opened',opened),('regression',regression)]:
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rr))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    inputs=[Path(__file__),Path('eventx/v6/dependency_evidence.py'),Path('eventx/v6/structured_evidence.py'),Path('eventx/v6/clean_speech.py'),base/'manifest.json',old/'manifest.json']
    (out/'manifest.json').write_text(json.dumps({'inputs':{str(p):digest(p) for p in inputs},'outputs':{p.name:digest(p) for p in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
