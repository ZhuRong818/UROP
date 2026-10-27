"""Download only public, revision-pinned NLI artifacts; no research upload."""
import json
from pathlib import Path
from datetime import datetime, timezone
from huggingface_hub import HfApi, snapshot_download
from eventx.tasks.score_v6_evidence_fields import digest


def main():
    root = Path('data/v6/nli_model_20260924')
    root.mkdir(exist_ok=True)
    if (root/'manifest.json').exists():
        raise FileExistsError(root/'manifest.json')
    repo = 'cross-encoder/nli-deberta-v3-small'
    info = HfApi(token=False).model_info(repo)
    license_name = info.card_data.get('license')
    assert license_name == 'apache-2.0', license_name
    receipt = {'repo':repo,'revision':info.sha,'license':license_name,
        'created_at':datetime.now(timezone.utc).isoformat(),
        'historical_eligibility':'uncertified; retrospective development only'}
    receipt_path = root/'download_receipt.json'
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
    else:
        receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
    snapshot_download(repo,revision=receipt['revision'],token=False,local_dir=root/'model',
        allow_patterns=['*.json','*.txt','*.model','*.safetensors','README.md'],
        ignore_patterns=['onnx/*','openvino/*'],max_workers=2)
    files = {str(p.relative_to(root)):digest(p) for p in (root/'model').rglob('*')
        if p.is_file() and '.cache' not in p.parts}
    (root/'manifest.json').write_text(json.dumps({'receipt':receipt,'files':files},indent=2)+'\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
