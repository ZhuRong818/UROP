"""Freeze approved finite frames, then draw once; no review or outcome evaluation."""
import json
import math
import platform
import random
import secrets
from datetime import datetime, timezone
from pathlib import Path
from eventx.tasks.validate_v6_boundary_submissions import read, sha, write

OUT = Path("data/v6/bounded_audit_20260917")


def main():
    if OUT.exists():
        raise FileExistsError("Existing freeze/draw must never be replaced or redrawn")
    inputs = {}
    for directory in ("retained_boundary_review_20260916", "hybrid_development_reviews_20260916",
                      "hybrid_audit_20260916", "local_models_20260916"):
        path = Path("data/v6") / directory / "manifest.json"
        m = json.loads(path.read_text())
        for name, digest in m.get("outputs", {}).items():
            assert sha(path.parent / name) == digest, name
        inputs[str(path)] = sha(path)
    for name in ("V6_BOUNDED_AUDIT_AMENDMENT.md", "BOUNDED_AUDIT_ADOPTION_20260917.md"):
        path = Path("eventx/release/v6") / name
        inputs[str(path)] = sha(path)
    def load(path):
        inputs[str(path)] = sha(path)
        return read(path)
    root = Path("data/v6")
    frames = {kind: load(root / "retained_boundary_review_20260916" / f"{kind}_second_review_packet.jsonl")
              for kind in ("family", "story")}
    assert len(frames["family"]) == 551 and len(frames["story"]) == 433
    dev = load(root / "hybrid_development_reviews_20260916/packet.jsonl")
    index = {(r["article"]["article_id"], r["contract"]["contract_id"]): r for r in dev}
    assert len(index) == len(dev) == 2063
    assert len({k[0] for k in index}) == 200
    pool = load(root / "hybrid_audit_20260916/scored_candidate_pool.jsonl")
    best = {}
    for r in pool:
        if r["split"] != "development":
            continue
        assert math.isfinite(r["crossencoder_logit"])
        key = (r["article_id"], r["contract_id"])
        if key not in index:
            continue
        rank = (-r["crossencoder_logit"], r["contract_id"])
        if r["article_id"] not in best or rank < best[r["article_id"]][0]:
            best[r["article_id"]] = (rank, index[key])
    frames["relevance"] = [v[1] for v in best.values()]
    assert 0 < len(best) <= 200
    # Unmodified blank templates establish no local returned labels in these files.
    # Does not purport to prove absence of offline annotation.
    for name in ("reviewer_A_responses.jsonl", "reviewer_B_responses.jsonl"):
        path = root / "hybrid_development_reviews_20260916" / name
        rows = load(path)
        assert all(r["reviewer_id"] is None and r["labels"]["relevance"] is None for r in rows)
    for kind, rows in frames.items():
        key = "pair_id" if kind == "relevance" else "review_id"
        frames[kind] = sorted(rows, key=lambda r: r[key])
        assert len({r[key] for r in rows}) == len(rows)
    sizes = {"family": 74, "story": 72, "relevance": min(40, len(best))}
    OUT.mkdir()  # Any subsequent failure requires recovery, never another draw.
    for kind, rows in frames.items():
        write(OUT / f"{kind}_frame.jsonl", rows)
    freeze = {"created_at": datetime.now(timezone.utc).isoformat(), "inputs": inputs,
              "frames": {k: {"N": len(v), "n": sizes[k], "sha256": sha(OUT / f"{k}_frame.jsonl")}
                         for k, v in frames.items()}, "alpha": 0.05 / 3,
              "error_tolerances": {"family": 0.05, "story": 0.05, "relevance": 0.1},
              "code_sha256": sha(Path(__file__)), "known_local_relevance_templates_blank": True,
              "offline_label_exposure_verified": False}
    (OUT / "frame_freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
    seed = secrets.randbits(256)
    (OUT / "draw_receipt.json").write_text(json.dumps({"seed": seed,
        "created_at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
        "algorithm": "random.Random(seed).sample; endpoint order family,story,relevance; sorted stable IDs",
        "frame_freeze_sha256": sha(OUT / "frame_freeze.json")}, indent=2) + "\n")
    rng = random.Random(seed)
    sample_ids = {}
    for kind in ("family", "story", "relevance"):
        rows = rng.sample(frames[kind], sizes[kind])
        write(OUT / f"{kind}_review_packet.jsonl", rows)
        key = "pair_id" if kind == "relevance" else "review_id"
        sample_ids[kind] = [r[key] for r in rows]
        if kind == "relevance":
            answers = [{"pair_id": r["pair_id"], "reviewer_id": None,
                        "labels": {"relevance": None, "outcome_applicability": None,
                                   "evidence_spans": [], "identity_problem": None}} for r in rows]
            for label in ("A", "B"):
                write(OUT / f"relevance_reviewer_{label}_responses.jsonl", answers)
    report = {"status": "frozen_sample_awaiting_reviews", "populations": {k: len(v) for k,v in frames.items()},
              "sample_sizes": sizes, "relevance_output_coverage": len(best) / 200,
              "distinct_cases": sum(sizes.values()), "ordinary_new_judgments": sizes["family"] + sizes["story"] + 2*sizes["relevance"],
              "max_judgments_with_adjudication": 2*sum(sizes.values()) + sizes["relevance"],
              "sample_ids": sample_ids, "outcomes_accessed": False, "audit_evaluated": False}
    (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (OUT / "manifest.json").write_text(json.dumps({"outputs": {p.name: sha(p) for p in OUT.iterdir()}}, indent=2) + "\n")
    print(json.dumps({k:v for k,v in report.items() if k != "sample_ids"}, indent=2))


if __name__ == "__main__":
    main()
