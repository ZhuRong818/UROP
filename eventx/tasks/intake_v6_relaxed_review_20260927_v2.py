"""Inspect submitted relaxed V6 development reviews without admitting labels."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

from eventx.tasks.validate_v6_context_development_review_20260927 import packet_integrity, validate_file
from eventx.settings import REPO_ROOT

SOURCE = REPO_ROOT / "eventx/v6"
PACKET = REPO_ROOT / "data/v6/context_development_review_20260927"
OUT = REPO_ROOT / "data/v6/relaxed_review_intake_20260927_v2"
NAMES = ("reviewer1.jsonl", "reviewer2.jsonl", "reviewed.jsonl")
FIELDS = ("relaxed_relation", "relaxed_applicability", "directional_evidence", "retrospective_development_use")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def prepare() -> None:
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.mkdir(parents=True)
    spec = {
        "scope": "fixed opened-development 102-pair packet; three submitted relaxed review files",
        "checks": ["frozen packet integrity", "pair/identity completeness", "distinct submitted reviewer IDs",
                   "existing-rubric validator error categories", "source-quote offsets including description alias",
                   "merged row consistency with two submissions", "paired agreement by submitted field"],
        "interpretation": "schema and exploratory development intake only; simulated IDs do not establish human review",
        "protected_outcome_access": False,
    }
    dump(OUT / "spec.json", spec)
    input_hashes = {str((SOURCE / name).relative_to(REPO_ROOT)): sha(SOURCE / name) for name in NAMES}
    input_hashes[str((PACKET / "manifest.json").relative_to(REPO_ROOT))] = sha(PACKET / "manifest.json")
    input_hashes[str((PACKET / "semantic_packet.jsonl").relative_to(REPO_ROOT))] = sha(PACKET / "semantic_packet.jsonl")
    input_hashes["eventx/tasks/intake_v6_relaxed_review_20260927_v2.py"] = sha(
        REPO_ROOT / "eventx/tasks/intake_v6_relaxed_review_20260927_v2.py")
    dump(OUT / "receipt.json", {"created_at_utc": datetime.now(timezone.utc).isoformat(),
                                "written_before_validation": True, "spec_sha256": sha(OUT / "spec.json"),
                                "inputs": input_hashes})
    for name in NAMES:
        shutil.copyfile(SOURCE / name, OUT / name)
        if sha(SOURCE / name) != sha(OUT / name):
            raise ValueError("snapshot differs")


def span_ok(pair: dict, span: dict, article: bool) -> tuple[bool, bool]:
    field = span.get("field")
    if article:
        sources = [pair.get(field)] if field in {"headline", "summary"} else []
    elif field in {"contract_question", "yes_subtitle"}:
        sources = [pair.get(field)]
    elif field in {"description", "rules_primary", "rules_secondary"}:
        sources = [rule.get("text") for rule in pair.get("contract_rules", []) if rule.get("field") == field]
    elif isinstance(field, str) and field.startswith("contract_rules[") and field.endswith("].text"):
        try:
            sources = [pair["contract_rules"][int(field[15:-6])]["text"]]
        except (ValueError, IndexError, KeyError):
            sources = []
    else:
        sources = []
    start, end, quote = span.get("start"), span.get("end"), span.get("quote")
    valid = (isinstance(start, int) and not isinstance(start, bool) and isinstance(end, int)
             and not isinstance(end, bool) and isinstance(quote, str)
             and any(isinstance(s, str) and 0 <= start < end <= len(s) and s[start:end] == quote for s in sources))
    return valid, field in {"description", "rules_primary", "rules_secondary"}


def run() -> None:
    receipt = json.loads((OUT / "receipt.json").read_text())
    if sha(OUT / "spec.json") != receipt["spec_sha256"]:
        raise ValueError("spec changed")
    if any(sha(REPO_ROOT / name) != digest for name, digest in receipt["inputs"].items()):
        raise ValueError("input changed")
    if any(sha(OUT / name) != sha(SOURCE / name) for name in NAMES):
        raise ValueError("snapshot changed")
    if (OUT / "report.json").exists():
        raise FileExistsError("report exists")
    packet, frozen_spec = packet_integrity()
    by_pair = {r["pair_id"]: r for r in packet}
    a, b, merged = [rows(OUT / name) for name in NAMES]
    maps = [{r["pair_id"]: r for r in rs} for rs in (a, b, merged)]
    identity_errors = []
    for name, rs, table in zip(NAMES, (a, b, merged), maps):
        if len(rs) != 102 or len(table) != 102 or set(table) != set(by_pair):
            identity_errors.append(name + ": pair IDs/count differ")
        for pid, row in table.items():
            if pid in by_pair and any(row.get(key) != by_pair[pid].get(key) for key in ("article_id", "contract_id")
                                      if key in row):
                identity_errors.append(name + ": identity mismatch " + pid)
    valid_span_counts = Counter()
    invalid_spans = []
    for name, table in zip(NAMES, maps):
        for pid, row in table.items():
            pair = by_pair.get(pid)
            if pair is None:
                continue
            for key, article in (("article_evidence_spans", True), ("contract_evidence_spans", False)):
                spans = row.get(key)
                if not isinstance(spans, list):
                    invalid_spans.append({"file": name, "pair_id": pid, "field": key, "reason": "not_list"})
                    continue
                for span in spans:
                    if not isinstance(span, dict):
                        invalid_spans.append({"file": name, "pair_id": pid, "field": key, "reason": "not_object"})
                        continue
                    okay, alias = span_ok(pair, span, article)
                    valid_span_counts["total"] += 1
                    if alias:
                        valid_span_counts["description_alias"] += 1
                    if not okay:
                        invalid_spans.append({"file": name, "pair_id": pid, "field": span.get("field"),
                                              "reason": "quote_or_offset_mismatch"})
    old_errors = []
    reviewer_ids = []
    for name in NAMES[:2]:
        errors, reviewer_id = validate_file(OUT / name, packet, frozen_spec)
        old_errors.extend(errors)
        reviewer_ids.append(reviewer_id)
    error_types = Counter(e.split(": ")[-1] for e in old_errors)
    disagreement = {field: sum(maps[0][pid].get(field) != maps[1][pid].get(field) for pid in by_pair)
                    for field in FIELDS}
    merged_mismatches = []
    for pid in by_pair:
        m = maps[2][pid]
        for key, index in (("reviewer_1", 0), ("reviewer_2", 1)):
            for field in FIELDS + ("rationale",):
                if m.get(key, {}).get(field) != maps[index][pid].get(field):
                    merged_mismatches.append({"pair_id": pid, "reviewer": key, "field": field})
        for field in FIELDS:
            agreed = maps[0][pid].get(field) == maps[1][pid].get(field)
            expected = "agreed" if agreed else "conservative_merge"
            if m.get("field_merge_status", {}).get(field) != expected:
                merged_mismatches.append({"pair_id": pid, "merge_status": field})
            if m.get(field) not in {maps[0][pid].get(field), maps[1][pid].get(field)}:
                merged_mismatches.append({"pair_id": pid, "merged_value": field})
    distributions = {name: {field: dict(Counter(row.get(field) for row in rs)) for field in FIELDS}
                     for name, rs in zip(NAMES, (a, b, merged))}
    report = {
        "scope": "opened development 102-pair packet",
        "packet_hash_valid": True,
        "source_sha256": {name: sha(OUT / name) for name in NAMES},
        "rows": {name: len(rs) for name, rs in zip(NAMES, (a, b, merged))},
        "reviewer_ids": reviewer_ids,
        "identity_errors": identity_errors,
        "span_count": valid_span_counts["total"],
        "description_alias_spans": valid_span_counts["description_alias"],
        "invalid_spans": invalid_spans,
        "existing_rubric_validator_errors": len(old_errors),
        "existing_rubric_validator_error_types": dict(error_types),
        "pairwise_disagreement": disagreement,
        "pairs_with_any_disagreement": sum(any(maps[0][pid].get(field) != maps[1][pid].get(field) for field in FIELDS)
                                           for pid in by_pair),
        "merged_mismatches": merged_mismatches,
        "distributions": distributions,
        "original_rubric_valid": False,
        "human_review_verified": False,
        "predictive_admissions": 0,
        "interpretation": "separate submitted files exist but identify themselves as simulated relaxed reviews; different schema from presampled rubric; development sensitivity only",
    }
    dump(OUT / "report.json", report)
    dump(OUT / "manifest.json", {"inputs": receipt["inputs"], "outputs": {
        name: sha(OUT / name) for name in ("spec.json", "receipt.json", *NAMES, "report.json")}})
    print(json.dumps({key: report[key] for key in ("rows", "reviewer_ids", "identity_errors", "span_count",
                                                 "description_alias_spans", "invalid_spans",
                                                 "existing_rubric_validator_errors", "pairwise_disagreement",
                                                 "pairs_with_any_disagreement", "merged_mismatches")}, indent=2))


if __name__ == "__main__":
    {"prepare": prepare, "run": run}[sys.argv[1]]()
