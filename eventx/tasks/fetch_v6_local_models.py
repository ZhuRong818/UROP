"""Download pinned public model weights; never upload research text."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

def main():
    from huggingface_hub import HfApi, snapshot_download
    root = Path("data/v6/local_models_20260916")
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / "manifest.json"
    if manifest.exists():
        raise FileExistsError(manifest)
    records = []
    for repo, name in [("sentence-transformers/all-MiniLM-L6-v2", "encoder"),
                       ("cross-encoder/ms-marco-MiniLM-L6-v2", "reranker")]:
        info = HfApi(token=False).model_info(repo)
        dest = root / name
        snapshot_download(repo, revision=info.sha, local_dir=dest, token=False,
            allow_patterns=["*.json", "*.txt", "*.safetensors", "README.md"],
            ignore_patterns=["onnx/*", "openvino/*"], max_workers=2)
        files = {str(p.relative_to(dest)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in dest.rglob("*") if p.is_file() and ".cache" not in p.parts}
        records.append({"repo": repo, "revision": info.sha, "path": str(dest),
            "files": files, "historical_model_eligibility": "not_certified",
            "purpose": "retrospective_link_audit_only"})
    manifest.write_text(json.dumps({"created_at": datetime.now(timezone.utc).isoformat(),
        "models": records}, indent=2) + "\n")
    print(json.dumps([{k:r[k] for k in ("repo", "revision", "path")} for r in records]))

if __name__ == "__main__":
    main()
