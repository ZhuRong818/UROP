"""Verify and manifest a metadata-only reassessment release."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/v5/design_reassessment_20260915'
REC=ROOT/'data/v5/provenance_recovery_20260908'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert not (OUT/'manifest.json').exists(), 'Publish a new version instead of overwriting.'
    inputs=set()
    complete=failed=0
    for receipt in sorted(REC.glob('reassessment_20260915_*.json')):
        if receipt.name.endswith('_payload.json'):continue
        record=json.loads(receipt.read_text());inputs.add(receipt)
        if record['status']=='complete':
            complete+=1
            data=ROOT/record['data_path'];assert sha(data)==record['data_sha256']
            inputs.add(data)
            if 'rows' in record:
                rows=[json.loads(s) for s in data.read_text().splitlines() if s.strip()]
                assert len(rows)==record['rows']
        else:failed+=1
    assert (complete,failed)==(7,3)
    report=json.loads((OUT/'report.json').read_text())
    assert report['recovered_rule_text']['rows']==43
    assert report['recovered_rule_text']['ingested_after_listed_close']==41
    assert not report['outcomes_accessed'] and not report['models_fitted']
    # Verify source graph/packet releases were preserved during reassessment.
    preserved=0
    for folder in ['data/v5/reviewed_pair_graph_20260915','data/v5/unresolved_pair_enrichment_20260915']:
        manifest=ROOT/folder/'manifest.json';inputs.add(manifest)
        m=json.loads(manifest.read_text())
        for name,digest in m['outputs'].items():
            assert sha(ROOT/folder/name)==digest,name
            preserved+=1
    inputs.update(ROOT/p for p in ['eventx/release/v5/PROTOCOL_V1_1.md',
        'eventx/features/v2_1_association.py','eventx/features/v4_news.py',
        'eventx/v5_corrected/point_in_time.py','eventx/v5_corrected/offset.py',
        'eventx/tasks/reconcile_v5_embedded_families_20260915.py',
        'data/v5/topic_coverage_triage_20260914/topic_review_queue.jsonl'])
    inputs.update(ROOT/'eventx/tasks'/name for name in [
        'prepare_v5_reassessment_probes_20260915.py',
        'prepare_v5_reassessment_news_retry_20260915.py',
        'prepare_v5_reassessment_rule_text_20260915.py',
        'summarize_v5_reassessment_20260915.py','finalize_v5_reassessment_20260916.py'])
    outputs={str(p.relative_to(ROOT)):sha(p) for p in OUT.rglob('*') if p.is_file()}
    proposal=ROOT/'eventx/release/v5/EXPERIMENT_REDESIGN_PROPOSAL_20260915.md'
    outputs[str(proposal.relative_to(ROOT))]=sha(proposal)
    verification={'successful_authenticated_requests':complete,'failed_authenticated_requests':failed,
                  'preserved_graph_and_packet_output_hashes':preserved,'receipt_counts_and_hashes_pass':True,
                  'proposal_adopted':False,'new_model_fits':0}
    (OUT/'manifest.json').write_text(json.dumps({'inputs':{str(p.relative_to(ROOT)):sha(p) for p in sorted(inputs)},
        'outputs':outputs,'verification':verification},indent=2)+'\n')
    print(json.dumps(verification,indent=2))
if __name__=='__main__':main()
