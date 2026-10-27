"""Public local structured-extraction model; revision-pinned, no text upload."""
import json
from pathlib import Path
from datetime import datetime, timezone
from huggingface_hub import HfApi, snapshot_download
from eventx.tasks.score_v6_evidence_fields import digest


def main():
    root = Path('data/v6/span_model_20260925')
    root.mkdir(exist_ok=True)
    if (root/'manifest.json').exists():
        raise FileExistsError(root/'manifest.json')
    repo = 'Qwen/Qwen2.5-0.5B-Instruct'
    receipt = root/'download_receipt.json'
    if not receipt.exists():
        info = HfApi(token=False).model_info(repo)
        assert info.card_data.get('license') == 'apache-2.0'
        receipt.write_text(json.dumps({'repo':repo,'revision':info.sha,'license':'apache-2.0',
            'created_at':datetime.now(timezone.utc).isoformat(),
            'historical_eligibility':'uncertified; retrospective development'},indent=2)+'\n')
    meta = json.loads(receipt.read_text())
    snapshot_download(repo,revision=meta['revision'],token=False,local_dir=root/'model',
        allow_patterns=['*.json','*.txt','*.safetensors','README.md','LICENSE'],max_workers=2)
    files = {str(p.relative_to(root)):digest(p) for p in (root/'model').rglob('*')
        if p.is_file() and '.cache' not in p.parts}
    (root/'manifest.json').write_text(json.dumps({'receipt':meta,'files':files},indent=2)+'\n')
    print(json.dumps(meta))


if __name__ == '__main__':
    main()
