"""Freeze the opened-development disagreement packet for one assistant adjudication."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from eventx.settings import REPO_ROOT
from eventx.tasks.validate_v6_context_development_review_20260927 import packet_integrity

OUT = REPO_ROOT / "data/v6/relaxed_adjudication_20260927"
INPUTS = [
    "data/v6/context_development_review_20260927/manifest.json",
    "data/v6/context_development_review_20260927/semantic_packet.jsonl",
    "data/v6/relaxed_review_intake_20260927_v2/manifest.json",
    "eventx/v6/reviewer1.jsonl",
    "eventx/v6/reviewer2.jsonl",
    "eventx/tasks/prepare_v6_relaxed_adjudication_20260927.py",
]
FIELDS = ("relaxed_relation", "relaxed_applicability", "directional_evidence", "retrospective_development_use")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def dump(path, obj):
    path.write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n")


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    packet, _ = packet_integrity()
    case = {r["pair_id"]: r for r in packet}
    a, b = [{r["pair_id"]: r for r in rows(REPO_ROOT / n)} for n in INPUTS[3:5]]
    if set(case) != set(a) or set(case) != set(b):
        raise ValueError("review pair IDs differ from frozen packet")
    OUT.mkdir(parents=True)
    spec = {
        "version": "v6-relaxed-development-adjudication-v0.1-20260927",
        "scope": "exactly the 39 opened-development pairs with any disagreement across four submitted relaxed fields",
        "adjudicator": "Codex assistant, one pass; output is assistant adjudication, not a third human label",
        "source": "only frozen semantic packet and two user-attested human submitted answers; no source clocks, prices, outcomes, protected or reserved data",
        "relation_rules": {
            "same_episode_or_series": "article explicitly describes the same underlying event, episode or measured series as the contract; shared proper nouns alone do not suffice",
            "shared_mechanism_context": "article states an action, measurement or forecast with a plausible mechanism tied to the contract subject but does not directly update its episode/series",
            "generic_topic_only": "shared subject or topic without an explicit relevant mechanism or predicate",
            "incompatible": "wrong entity, actor, market type, stage or episode",
        },
        "applicability_rules": {
            "material_predicate_evidence": "text materially addresses the contract's measured variable or event predicate, though it may omit threshold/deadline; it is not settlement evidence",
            "shared_context_only": "relevant mechanism or context but no material claim about the measured predicate itself",
            "not_applicable": "no grounded applicability to the specified contract, including wrong actor/episode/type",
        },
        "direction_rules": "supports_yes/no only for an explicit favorable/adverse direction on the contract predicate; otherwise mixed_or_neutral; no inference from outcome or later price",
        "use_rules": "usable if supplied fields justify the limited relaxed judgment, including clear exclusions; limited if missing/ambiguous fields materially constrain it",
        "decision_rule": "Choose one of the two submitted labels per disputed field when evidence supports it; otherwise null with unresolved status and reason. Preserve agreed fields. Cite a concrete article and contract span or explain missing evidence. No automatic merge.",
        "role": "development sensitivity only; do not call this original-rubric gold, independent audit, source certificate or predictive admission",
    }
    dump(OUT / "spec.json", spec)
    dump(OUT / "receipt.json", {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "written_before_disagreement_inspection": True,
        "inputs": {name: sha(REPO_ROOT / name) for name in INPUTS},
        "spec_sha256": sha(OUT / "spec.json"),
    })
    disagreement = []
    for pid in sorted(case):
        diffs = [f for f in FIELDS if a[pid][f] != b[pid][f]]
        if not diffs:
            continue
        disagreement.append({"pair_id": pid, "article_id": case[pid]["article_id"],
                             "contract_id": case[pid]["contract_id"],
                             "headline": case[pid]["headline"], "summary": case[pid]["summary"],
                             "contract_question": case[pid]["contract_question"],
                             "yes_subtitle": case[pid]["yes_subtitle"],
                             "contract_rules": case[pid]["contract_rules"],
                             "disputed_fields": diffs,
                             "reviewer_1": {k: a[pid].get(k) for k in FIELDS + ("rationale", "article_evidence_spans", "contract_evidence_spans")},
                             "reviewer_2": {k: b[pid].get(k) for k in FIELDS + ("rationale", "article_evidence_spans", "contract_evidence_spans")}})
    if len(disagreement) != 39:
        raise ValueError("unexpected disagreement count")
    with (OUT / "disagreement_packet.jsonl").open("w") as stream:
        for row in disagreement:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    dump(OUT / "packet_report.json", {"pairs": len(disagreement),
                                       "disputed_field_counts": dict(Counter(f for r in disagreement for f in r["disputed_fields"])),
                                       "status": "ready_for_one_pass_assistant_adjudication"})
    dump(OUT / "packet_manifest.json", {"inputs": json.loads((OUT / "receipt.json").read_text())["inputs"],
                                        "outputs": {name: sha(OUT / name) for name in ("spec.json", "receipt.json", "disagreement_packet.jsonl", "packet_report.json")}})
    print(json.dumps({"pairs": len(disagreement), "packet_sha256": sha(OUT / "disagreement_packet.jsonl")}))


if __name__ == "__main__":
    main()
