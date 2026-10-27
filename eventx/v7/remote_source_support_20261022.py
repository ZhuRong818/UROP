"""Portable fixed-input checks for a separately frozen source-only deployment."""
import hashlib,json
from datetime import datetime,timezone
from eventx.settings import REPO_ROOT
PROTECTED=REPO_ROOT/'eventx/release/v7/market_capture_20261018/protected_ids.json'
FIXED={'eventx/release/v7/market_capture_20261018/protected_ids.json': '5621facc8dda87e167e7662a91ffa18ef31cffc1b1c72ebdddcb36429db5698b', 'data/v5/market_condition_tuning_20261012/selected_model.joblib': 'd5d5a8c12fd999674f687c712e14f3a4406e7ab5ec34774baf1828f644f73a3c', 'eventx/release/v7/remote_source_pilot_20261022/sample.jsonl': 'eaaa4892a96ba6600ab96eecf3171251e2fff225c4770e984e62973b33373173'}
def now():return datetime.now(timezone.utc)
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def verify_fixed_inputs():
    for p,h in FIXED.items():
        if sha(REPO_ROOT/p)!=h:raise RuntimeError('Remote fixed input mismatch: '+p)
    return len(FIXED)
