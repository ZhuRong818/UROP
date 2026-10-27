"""Validate one-pass assistant decisions and summarize V6 relaxed development review."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from eventx.settings import REPO_ROOT

OUT = REPO_ROOT / "data/v6/relaxed_adjudication_20260927"
PACKET = REPO_ROOT / "data/v6/context_development_review_20260927"
SOURCE = REPO_ROOT / "eventx/v6"
FIELDS = ("relaxed_relation", "relaxed_applicability", "directional_evidence", "retrospective_development_use")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def dump(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def stage():
    if (OUT / "decision_receipt.json").exists():
        raise FileExistsError("decision receipt exists")
    if not (OUT / "adjudication_choices.json").exists():
        raise FileNotFoundError("choices must be copied first")
    packet_manifest = json.loads((OUT / "packet_manifest.json").read_text())
    if any(sha(REPO_ROOT / name) != digest for name, digest in packet_manifest["inputs"].items()):
        raise ValueError("packet input hash changed")
    if any(sha(OUT / name) != digest for name, digest in packet_manifest["outputs"].items()):
        raise ValueError("packet output hash changed")
    dump(OUT / "decision_receipt.json", {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "written_before_adjudication_summary": True,
        "packet_manifest_sha256": sha(OUT / "packet_manifest.json"),
        "choices_sha256": sha(OUT / "adjudication_choices.json"),
        "finalizer_sha256": sha(REPO_ROOT / "eventx/tasks/finalize_v6_relaxed_adjudication_20260927.py"),
        "merged_sha256": sha(SOURCE / "reviewed.jsonl"),
        "selection_ledger_sha256": sha(PACKET / "selection_ledger.jsonl"),
    })


def run():
    if (OUT / "report.json").exists():
        raise FileExistsError("adjudication report exists")
    receipt = json.loads((OUT / "decision_receipt.json").read_text())
    if receipt["packet_manifest_sha256"] != sha(OUT / "packet_manifest.json") or receipt["choices_sha256"] != sha(OUT / "adjudication_choices.json") or receipt["finalizer_sha256"] != sha(REPO_ROOT / "eventx/tasks/finalize_v6_relaxed_adjudication_20260927.py") or receipt["merged_sha256"] != sha(SOURCE / "reviewed.jsonl") or receipt["selection_ledger_sha256"] != sha(PACKET / "selection_ledger.jsonl"):
        raise ValueError("decision inputs changed")
    packet_manifest = json.loads((OUT / "packet_manifest.json").read_text())
    if any(sha(REPO_ROOT / name) != digest for name, digest in packet_manifest["inputs"].items()):
        raise ValueError("packet input hash changed")
    if any(sha(OUT / name) != digest for name, digest in packet_manifest["outputs"].items()):
        raise ValueError("packet output hash changed")
    disagree = {r["pair_id"]: r for r in rows(OUT / "disagreement_packet.jsonl")}
    a, b = [{r["pair_id"]: r for r in rows(SOURCE / name)} for name in ("reviewer1.jsonl", "reviewer2.jsonl")]
    if len(disagree) != 39 or set(a) != set(b) or len(a) != 102:
        raise ValueError("review scope changed")
    choices = json.loads((OUT / "adjudication_choices.json").read_text())
    policies = choices["article_policies"]
    overrides = choices["pair_overrides"]
    if set(policies) != {r["article_id"] for r in disagree.values()} or not set(overrides) <= set(disagree):
        raise ValueError("choice scope mismatch")
    decision_rows = []
    final = []
    for pid in sorted(a):
        record = {"pair_id": pid, "reviewer_1_id": a[pid]["reviewer_id"], "reviewer_2_id": b[pid]["reviewer_id"]}
        if pid in disagree:
            d = disagree[pid]
            policy = policies[d["article_id"]]
            override = overrides.get(pid, {})
            prescribed = dict(policy["choices"])
            prescribed.update(override.get("choices", {}))
            if set(prescribed) != set(d["disputed_fields"]):
                raise ValueError("exact disputed field choices required: " + pid)
            for field in FIELDS:
                value = prescribed.get(field, a[pid][field])
                if value not in {a[pid][field], b[pid][field]}:
                    raise ValueError("choice outside submitted values: " + pid + " " + field)
                record[field] = value
            rationale = policy["reason"] + (" " + override["reason"] if override else "")
            article_spans = a[pid]["article_evidence_spans"] or b[pid]["article_evidence_spans"]
            contract_spans = a[pid]["contract_evidence_spans"] or b[pid]["contract_evidence_spans"]
            decision = {
                "pair_id": pid, "article_id": d["article_id"], "contract_id": d["contract_id"],
                "contract_question": d["contract_question"],
                "disputed_fields": d["disputed_fields"],
                "reviewer_1": {field: a[pid][field] for field in FIELDS},
                "reviewer_2": {field: b[pid][field] for field in FIELDS},
                "assistant_choices": prescribed,
                "rationale": rationale,
                "article_evidence_span": article_spans[0],
                "contract_evidence_span": contract_spans[0],
                "adjudicator": "Codex assistant",
                "status": "assistant_adjudicated_development_only",
            }
            decision_rows.append(decision)
            record["status"] = decision["status"]
        else:
            if any(a[pid][field] != b[pid][field] for field in FIELDS):
                raise ValueError("unlisted disagreement: " + pid)
            for field in FIELDS:
                record[field] = a[pid][field]
            record["status"] = "human_reviewer_agreement_development_only"
        final.append(record)
    with (OUT / "assistant_decisions.jsonl").open("w") as stream:
        for row in decision_rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    with (OUT / "development_labels_102.jsonl").open("w") as stream:
        for row in final:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    strata = {r["pair_id"]: r["stratum"] for r in rows(PACKET / "selection_ledger.jsonl")}
    if set(strata) != set(a):
        raise ValueError("stratum IDs changed")
    by_stratum = {}
    for stratum in sorted(set(strata.values())):
        subset = [r for r in final if strata[r["pair_id"]] == stratum]
        by_stratum[stratum] = {"pairs": len(subset),
                               "relation": dict(Counter(r["relaxed_relation"] for r in subset)),
                               "applicability": dict(Counter(r["relaxed_applicability"] for r in subset))}
    original_merge = {r["pair_id"]: r for r in rows(SOURCE / "reviewed.jsonl")}
    changed_from_mechanical = {field: [r["pair_id"] for r in final if r[field] != original_merge[r["pair_id"]][field]]
                               for field in FIELDS}
    report = {
        "packet_pairs": len(a), "reviewer_agreement_pairs": 102 - len(disagree),
        "assistant_adjudicated_pairs": len(decision_rows),
        "unresolved_pairs": 0,
        "field_distribution": {field: dict(Counter(r[field] for r in final)) for field in FIELDS},
        "by_stratum": by_stratum,
        "changed_from_mechanical_merge": changed_from_mechanical,
        "all_decisions_chosen_from_two_submissions": True,
        "adjudicator": "Codex assistant",
        "original_rubric_gold": False,
        "human_third_adjudication": False,
        "full_window_source_certified": False,
        "predictive_admissions": 0,
        "interpretation": "opened-development relaxed sensitivity labels only; agreement and assistant decisions are not a fresh audit, population accuracy estimate, source certificate, or eligible predictive exposure",
    }
    dump(OUT / "report.json", report)
    input_paths = [OUT / "packet_manifest.json", OUT / "adjudication_choices.json", OUT / "decision_receipt.json",
                   REPO_ROOT / "eventx/tasks/finalize_v6_relaxed_adjudication_20260927.py",
                   PACKET / "selection_ledger.jsonl", SOURCE / "reviewed.jsonl"]
    dump(OUT / "manifest.json", {"inputs": {str(p.relative_to(REPO_ROOT)): sha(p) for p in input_paths},
                                 "outputs": {name: sha(OUT / name) for name in ("assistant_decisions.jsonl", "development_labels_102.jsonl", "report.json")}})
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    {"stage": stage, "run": run}[sys.argv[1]]()
