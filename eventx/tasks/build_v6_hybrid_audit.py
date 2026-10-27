"""Local neural retrieval + reranking and PROVISIONAL separate audit reservation.

No gold labels, forecast labels, prices or outcomes are loaded. Holdout below means
association annotation reservation, NOT a prediction-market outcome holdout.
"""
import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import hashlib
import importlib.metadata
import json
from pathlib import Path
import random
import tempfile
from collections import Counter
import numpy as np
from eventx.v6.contracts import review_text, utc
from eventx.v6.retrieval import BM25

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "data/v6/contract_link_pilot_20260916"
MODELS = ROOT / "data/v6/local_models_20260916"
OUTPUT = ROOT / "data/v6/hybrid_audit_20260916"

def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def read(path):
    return [json.loads(line) for line in path.open()]

def write(path, records):
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True) + "\n")

def main():
    import torch
    from sentence_transformers import SentenceTransformer, CrossEncoder
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    old = json.loads((PILOT / "manifest.json").read_text())
    for path, expected in old["outputs"].items():
        if sha(PILOT / path) != expected:
            raise ValueError("Pilot hash mismatch")
    model_manifest = json.loads((MODELS / "manifest.json").read_text())
    for model in model_manifest["models"]:
        for name, expected in model["files"].items():
            if sha(ROOT / model["path"] / name) != expected:
                raise ValueError("Model hash mismatch")
    torch.set_num_threads(4)
    torch.manual_seed(20260916)
    encoder = SentenceTransformer(str(MODELS / "encoder"), device="cpu", local_files_only=True,
                                  model_kwargs={"attn_implementation":"eager"})
    reranker = CrossEncoder(str(MODELS / "reranker"), device="cpu", max_length=384,
                           local_files_only=True, model_kwargs={"attn_implementation":"eager"})
    encoder.double()
    reranker.model.bfloat16()
    smoke = reranker.predict([("What is the capital of France?", "Paris is the capital of France.")],
                             activation_fn=torch.nn.Identity())
    if not np.isfinite(smoke).all():
        raise ValueError("Reranker fails non-research numerical smoke test")
    cards = [c for c in read(PILOT / "contract_cards.jsonl") if c["scope"] == "single_event_candidate_unverified"]
    texts = [review_text(c) for c in cards]
    articles = read(PILOT / "articles.jsonl")
    packet = read(PILOT / "development_review_packet.jsonl")
    dev_groups = {p["contract"]["provisional_split_group"] for p in packet}
    dev_events = {e for p in packet for e in p["contract"]["event_ids"]}
    reserved_indexes = [i for i,c in enumerate(cards) if c["provisional_split_group"] not in dev_groups
                        and not set(c["event_ids"]) & dev_events]
    if len(reserved_indexes) < 60:
        raise ValueError("Insufficient family-disjoint reservation")
    print(f"Encoding {len(cards)} cards; {len(reserved_indexes)} reserved candidates", flush=True)
    vectors = encoder.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
    if not np.isfinite(vectors).all():
        raise ValueError("Nonfinite contract embeddings")
    article_text = lambda a: "\n".join(a.get(k) or "" for k in ("headline", "summary"))
    dev_vectors = encoder.encode([article_text(a) for a in articles], normalize_embeddings=True,
                                batch_size=32, show_progress_bar=False)
    if not np.isfinite(dev_vectors).all():
        raise ValueError("Nonfinite development embeddings")
    # Hash/ID whitelist from the opened source inventory; candidate article IDs
    # are drawn before any relevance annotation. No body or future news is used.
    news_index = ROOT / "data/v5/source_readiness_20260908/news_provenance_staging.jsonl"
    news_path = ROOT / "data/v3_historical/primary/label_blind_inputs/news.jsonl"
    dev_ids = {a["article_id"] for a in articles}
    index = [r for r in read(news_index) if r["clock_consistent"] and r["article_id"] not in dev_ids]
    rng = random.Random(20260917)
    selected = {r["source_line"]: r for r in rng.sample(sorted(index,key=lambda r:r["article_id"]), 500)}
    extra = []
    with news_path.open() as f:
        for line, raw in enumerate(f, 1):
            if line not in selected:
                continue
            r, p = json.loads(raw), selected[line]
            content = {k:r.get(k) for k in ("headline", "summary")}
            if str(r["id"]) != p["article_id"] or hashlib.sha256(json.dumps(content,sort_keys=True).encode()).hexdigest() != p["content_sha256"]:
                raise ValueError("News source identity/hash mismatch")
            if not utc("2026-05-17T00:00:00Z") <= utc(p["source_clock_available_at"]) < utc("2026-07-22T00:00:00Z"):
                raise ValueError("Outside discovery")
            extra.append({"article_id":p["article_id"], **content,
                "source_clock_available_at":p["source_clock_available_at"],
                "published_at":r["published_at"], "publisher":r.get("publisher"),
                "content_sha256":p["content_sha256"], "source_line":line})
    extra.sort(key=lambda a:hashlib.sha256(a["article_id"].encode()).hexdigest())
    ev = encoder.encode([article_text(a) for a in extra], normalize_embeddings=True,
                        batch_size=32, show_progress_bar=False)
    if not np.isfinite(ev).all():
        raise ValueError("Nonfinite reserved embeddings")
    # Conservative proxy ONLY: semantic story separation must still be reviewed.
    similarities = ev @ dev_vectors.T
    dev_hashes = {a["content_sha256"] for a in articles}
    acceptable = [i for i,a in enumerate(extra) if float(similarities[i].max()) < .8
                  and a["content_sha256"] not in dev_hashes]
    chosen = acceptable[:100]
    if len(chosen) != 100:
        raise ValueError("Insufficient story-screened articles; do not relax threshold")
    reserve_articles = [extra[i] for i in chosen]
    reserve_vectors = ev[chosen]
    development_indexes = [i for i,c in enumerate(cards) if c["provisional_split_group"] in dev_groups
                           or set(c["event_ids"]) & dev_events]
    bm25 = BM25([texts[i] for i in development_indexes])
    reserved_bm25 = BM25([texts[i] for i in reserved_indexes])
    pools, shortlist, ledger, review = [], [], [], []
    dense_only = 0
    for split, aa, av in [("development", articles, dev_vectors),
                          ("reserved_audit_pending_certification", reserve_articles, reserve_vectors)]:
        allowed = development_indexes if split == "development" else reserved_indexes
        searcher = bm25 if split == "development" else reserved_bm25
        local_vectors = vectors[allowed]
        for number, (a, v) in enumerate(zip(aa, av)):
            lexical = {allowed[i]:float(s) for i,s in searcher.search(article_text(a),50)}
            sims = local_vectors @ v
            nearest = np.argsort(-sims,kind="stable")[:50]
            dense = {allowed[int(i)]:float(sims[i]) for i in nearest}
            union = sorted(set(lexical)|set(dense))
            dense_only += len(set(dense)-set(lexical))
            scores = reranker.predict([(texts[i],article_text(a)) for i in union],
                batch_size=32, show_progress_bar=False, activation_fn=torch.nn.Identity())
            if not np.isfinite(scores).all():
                raise ValueError("Nonfinite reranker output")
            ordered = sorted(zip(union,map(float,scores)),key=lambda t:(-t[1],t[0]))
            for rank,(i,score) in enumerate(ordered,1):
                pools.append({"split":split,"article_id":a["article_id"],"contract_id":cards[i]["contract_id"],
                    "bm25":lexical.get(i),"dense_cosine":dense.get(i),"crossencoder_logit":score,"rank":rank})
            if split == "development":
                shortlist.extend({"article_id":a["article_id"],"contract_id":cards[i]["contract_id"],
                    "rank":rank,"crossencoder_logit":s} for rank,(i,s) in enumerate(ordered[:5],1))
            else:
                outside = sorted(set(allowed)-set(union))
                picked = [(i,"reranked_top5",None) for i,_ in ordered[:5]]
                picked.append((rng.choice(outside),"random_outside_union",1/len(outside)))
                for i,stratum,prob in picked:
                    identity = hashlib.sha256((a["article_id"]+"|"+cards[i]["contract_id"]).encode()).hexdigest()[:24]
                    review.append({"pair_id":identity,"article":a,"contract":cards[i],"reviewer_id":None,
                        "labels":{"relevance":None,"outcome_applicability":None,"evidence_spans":[],"identity_problem":None}})
                    ledger.append({"pair_id":identity,"stratum":stratum,"conditional_random_probability":prob,
                        "overall_inclusion_probability":None,"reason":"story-screened audit reservation; not population-weighted"})
            if number % 25 == 0:
                print(split,number,"articles ranked",flush=True)
    review_groups={p["contract"]["provisional_split_group"] for p in review}
    review_events={e for p in review for e in p["contract"]["event_ids"]}
    assert not dev_groups & review_groups and not dev_events & review_events
    assert not dev_ids & {a["article_id"] for a in reserve_articles}
    stage=Path(tempfile.mkdtemp(prefix=".hybrid-audit-",dir=OUTPUT.parent))
    rng.shuffle(review)
    for name,rr in [("scored_candidate_pool",pools),("development_top5",shortlist),
                    ("reserved_review_packet",review),("reserved_selection_ledger",ledger),
                    ("reserved_articles",reserve_articles)]:
        write(stage/f"{name}.jsonl",rr)
    for suffix in ("A","B"):
        write(stage/f"reviewer_{suffix}_responses.jsonl",[{k:p[k] for k in ("pair_id","labels","reviewer_id")} for p in review])
    report={"status":"retrieval_executed_annotation_reservation_not_certified",
        "development_articles":len(articles),"development_top5_pairs":len(shortlist),
        "reserved_articles":len(reserve_articles),"reserved_pairs":len(review),
        "candidate_pool_pairs":len(pools),"dense_only_candidates":dense_only,
        "development_review_groups":len(dev_groups),"reserved_review_groups":len(review_groups),
        "event_overlap":len(dev_events&review_events),"provisional_group_overlap":len(dev_groups&review_groups),
        "max_reserved_to_development_article_cosine":float(similarities[chosen].max()),
        "story_screen_threshold":.8,"story_independence_certified":False,
        "human_labels":0,"predictive_fits":0,"heldout_evaluation_permitted":False,
        "model_training_cutoff_certified":False,"metadata_pit_admission":False,
        "encoder_max_tokens":encoder.max_seq_length,"reranker_max_tokens":384,
        "encoder_dtype":"float64", "reranker_dtype":"bfloat16", "attention_implementation":"eager",
        "source_scope":"opened May17-Jul22; retrospective linking only",
        "package_versions":{p:importlib.metadata.version(p) for p in
                            ["torch","transformers","sentence-transformers","numpy"]}}
    (stage/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    manifest={"inputs":{str(p.relative_to(ROOT)):sha(p) for p in [PILOT/"manifest.json",MODELS/"manifest.json",news_index,news_path]},
        "code":{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},
        "outputs":{p.name:sha(p) for p in stage.iterdir()},"research_freeze":False}
    (stage/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    stage.rename(OUTPUT)
    print(json.dumps(report,indent=2))

if __name__ == "__main__":
    main()
