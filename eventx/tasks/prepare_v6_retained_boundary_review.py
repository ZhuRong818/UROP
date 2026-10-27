"""Restrict outstanding boundary reviews to the retained, uncertified preview."""
import json
from pathlib import Path
import tempfile
from eventx.tasks.validate_v6_boundary_submissions import read, sha, write


def main():
    root = Path("data/v6")
    out = root / "retained_boundary_review_20260916"
    if out.exists():
        raise FileExistsError(out)
    inputs = {}
    def load(path):
        inputs[str(path)] = sha(path)
        return read(path)
    for directory in (root / "reviewed_isolation_20260916", root / "boundary_audit_20260916"):
        mp = directory / "manifest.json"
        manifest = json.loads(mp.read_text())
        assert all(sha(directory / n) == h for n, h in manifest["outputs"].items())
        inputs[str(mp)] = sha(mp)
    ids = {r["pair_id"] for r in load(root / "reviewed_isolation_20260916/remaining_NOT_ADMITTED.jsonl")}
    reserved = load(root / "hybrid_audit_20260916/reserved_review_packet.jsonl")
    retained = [r for r in reserved if r["pair_id"] in ids]
    assert len(retained) == len(ids)
    groups = {r["contract"]["provisional_split_group"] for r in retained}
    articles = {r["article"]["article_id"] for r in retained}
    packets = {}
    for kind in ("family", "story"):
        original = load(root / "boundary_audit_20260916" / f"{kind}_review_packet.jsonl")
        previous = {r["review_id"]: r for r in load(root / "boundary_restored_submission_20260916" / f"{kind}_submission_snapshot.jsonl")}
        packets[kind] = [r for r in original if
            (r["reserved_group"] in groups if kind == "family" else r["reserved_article"]["article_id"] in articles)]
        assert all(previous[r["review_id"]]["decision"] ==
                   ("no_direct_link_established" if kind == "family" else "distinct_story") for r in packets[kind])
        assert all(r.get(k) is None for r in packets[kind] for k in ("reviewer", "decision", "rationale"))
    summary = {"retained_preview_pairs": len(retained), "retained_original_groups": len(groups),
               "retained_articles": len(articles),
               "family_second_review_cases": len(packets["family"]),
               "story_second_review_cases": len(packets["story"]),
               "prior_judgments_hidden": True, "selection_is_informative": True,
               "whole_boundary_search_still_required": True, "certified": False,
               "relevance_labels_opened": False, "outcomes_accessed": False}
    stage = Path(tempfile.mkdtemp(prefix=".retained-boundary-", dir=root))
    for kind, rows in packets.items():
        write(stage / f"{kind}_second_review_packet.jsonl", rows)
    (stage / "report.json").write_text(json.dumps(summary, indent=2) + "\n")
    (stage / "manifest.json").write_text(json.dumps({"inputs": inputs,
        "code_sha256": sha(Path(__file__)), "outputs": {p.name: sha(p) for p in stage.iterdir()}}, indent=2) + "\n")
    stage.rename(out)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
