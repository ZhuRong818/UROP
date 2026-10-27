"""Fixed development NLI probe, not a calibrated resolver or independent audit."""
import json
from pathlib import Path
from datetime import datetime, timezone
import importlib.metadata
from eventx.tasks.score_v6_evidence_fields import digest

# Explicit assistant references, fixed before inference; one model, no threshold search.
CASES = [
 ('partitive', 'The fund sold some of its copper holdings.',
  'The fund sold copper.', 'The fund sold silver.'),
 ('notification', 'The director notified the company of his resignation.',
  'The company received a notification about the resignation.', 'The company resigned.'),
 ('organization', 'Bank of America purchased bonds.',
  'Bank of America bought bonds.', 'America purchased Bank.'),
 ('source', 'Copper will rise, says analyst Maria Chen.',
  'Maria Chen predicts a rise in copper.', 'Copper is the speaker making a prediction.'),
 ('metaphor', 'History says prices will fall.',
  'The text uses history as an indication that prices will fall.', 'A person named History made a statement.'),
 ('negated_source', 'The analyst did not say copper rose.',
  'The text denies that the analyst said copper rose.', 'The analyst said copper rose.'),
 ('figurative', 'The investor bought time by postponing the meeting.',
  'The investor delayed the meeting.', 'The investor purchased a financial asset.'),
 ('forecast', 'The economist expects copper to appreciate next year.',
  'An economist forecasts higher copper prices next year.', 'Copper has already appreciated next year.'),
]
AMBIGUOUS = [
 ('source_omitted', 'The share order is said to exceed its target.', 'A named company announced that the order exceeded its target.'),
 ('pronoun', 'It purchased silver.', 'The fund purchased silver.'),
]


def decision(p):
    return 'supported_candidate' if p['entailment'] >= .8 and p['entailment'] - max(p['neutral'],p['contradiction']) >= .2 else 'abstain'


def main():
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    root = Path('data/v6/nli_model_20260924')
    manifest = json.loads((root/'manifest.json').read_text())
    for p,h in manifest['files'].items():
        assert digest(root/p) == h
    out = Path('data/v6/nli_binding_trial_20260924')
    out.mkdir(exist_ok=False)
    probes = []
    for name,text,pos,neg in CASES:
        for tag,hyp in [('supported',pos),('unsupported',neg)]:
            probes.append({'case':name,'premise':text,'hypothesis':hyp,'reference':tag})
    for name,text,hyp in AMBIGUOUS:
        probes.append({'case':name,'premise':text,'hypothesis':hyp,'reference':'unsupported'})
    (out/'spec.json').write_text(json.dumps({'probes':probes,'threshold':.8,'margin':.2,
        'references':'assistant-authored development, not blind gold',
        'baseline':'v0.2 abstains from all semantic verification',
        'purpose':'diagnostic only; no automatic entity/link admission'},indent=2)+'\n')
    inputs = [Path(__file__),root/'manifest.json']
    (out/'receipt.json').write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),
        'inputs':{str(p):digest(p) for p in inputs},'spec_sha256':digest(out/'spec.json')},indent=2)+'\n')
    torch.set_num_threads(2)
    torch.manual_seed(0)
    tokenizer = AutoTokenizer.from_pretrained(root/'model',local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(root/'model',local_files_only=True,
        torch_dtype=torch.float32,attn_implementation='eager').eval()
    labels = [str(model.config.id2label[i]).lower() for i in range(3)]
    assert labels == ['contradiction','entailment','neutral'], labels
    results = []
    with torch.no_grad():
        for r in probes:
            features = tokenizer(r['premise'],r['hypothesis'],return_tensors='pt',truncation=False)
            assert features['input_ids'].shape[1] <= 512
            logits = model(**features).logits[0]
            assert torch.isfinite(logits).all(), 'Nonfinite logits; stop, do not select numerical variant from scores'
            p = dict(zip(labels,logits.softmax(-1).tolist()))
            results.append({**r,'probabilities':p,'decision':decision(p)})
    supported = [r for r in results if r['reference']=='supported']
    unsupported = [r for r in results if r['reference']=='unsupported']
    wins = sum(results[2*i]['probabilities']['entailment'] > results[2*i+1]['probabilities']['entailment'] for i in range(len(CASES)))
    report = {'probes':len(results),'supported_references':len(supported),'unsupported_references':len(unsupported),
        'supported_candidates':sum(r['decision']=='supported_candidate' for r in supported),
        'false_support_candidates':sum(r['decision']=='supported_candidate' for r in unsupported),
        'strict_contrast_wins':wins,'contrasts':len(CASES),'predictive_admissions':0,
        'baseline_v02':{'supported_candidates':0,'false_support_candidates':0,'abstentions':len(results)}}
    (out/'results.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in results))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'runtime.json').write_text(json.dumps({'device':'cpu','dtype':'float32','labels':labels,
        'packages':{n:importlib.metadata.version(n) for n in ['torch','transformers','tokenizers'] }},indent=2)+'\n')
    (out/'manifest.json').write_text(json.dumps({'inputs':{str(p):digest(p) for p in inputs},
        'outputs':{p.name:digest(p) for p in out.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
