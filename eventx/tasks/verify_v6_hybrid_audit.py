"""Check released association artifacts without reading forecast outcomes."""
import hashlib
import json
import math
from pathlib import Path

def main():
    root=Path("data/v6/hybrid_audit_20260916")
    manifest=json.loads((root/"manifest.json").read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for name,expected in manifest["outputs"].items():
        assert sha(root/name)==expected, name
    for section in ("inputs","code"):
        for name,expected in manifest[section].items():
            assert sha(Path(name))==expected,name
    read=lambda p:[json.loads(x) for x in p.open()]
    packet=read(root/"reserved_review_packet.jsonl")
    dev=read(Path("data/v6/contract_link_pilot_20260916/development_review_packet.jsonl"))
    assert len(packet)==600 and len({r["pair_id"] for r in packet})==600
    for key in ("provisional_split_group",):
        assert not {r["contract"][key] for r in packet}&{r["contract"][key] for r in dev}
    assert not {e for r in packet for e in r["contract"]["event_ids"]}&{e for r in dev for e in r["contract"]["event_ids"]}
    assert not {r["article"]["article_id"] for r in packet}&{r["article"]["article_id"] for r in dev}
    for r in packet:
        assert r["reviewer_id"] is None and r["labels"]["relevance"] is None
        assert "crossencoder_logit" not in r and "stratum" not in r
        assert r["contract"]["training_admissible"] is False
    for name in ("reviewer_A_responses.jsonl","reviewer_B_responses.jsonl"):
        rr=read(root/name)
        assert {r["pair_id"] for r in rr}=={r["pair_id"] for r in packet}
        assert all(r["reviewer_id"] is None and r["labels"]["relevance"] is None for r in rr)
    scores=read(root/"scored_candidate_pool.jsonl")
    assert all(math.isfinite(r["crossencoder_logit"]) for r in scores)
    assert len({(r["split"],r["article_id"],r["contract_id"]) for r in scores})==len(scores)
    print(json.dumps({"status":"pass","pairs":len(packet),"scores":len(scores),
                      "human_validation_complete":False,"independence_certified":False}))

if __name__ == "__main__":main()
