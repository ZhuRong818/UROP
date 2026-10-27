"""Publish assistant semantic inspection and key-only coverage interpretation."""
from collections import Counter
from datetime import datetime
import json

import numpy as np

from eventx.tasks.run_v5_residual_feasibility import REPO_ROOT, MARKETS, read_jsonl, sha256_file
from eventx.tasks.prepare_v4_discovery_news_quality import NEWS
from eventx.tasks.diagnose_v7_signed_evidence_coverage_20261012 import OUT, write_json, write_jsonl


FINDINGS = {
    "197135093": ("unbound_action_and_unparsed_bucket", "lower courts",
        "The extractor treats 'lower courts' as a rate-cut verb through its article-wide lower* regex. The supplied text reports Lisa Cook's legal case, not a 50+ bp July rate cut. Its basis-point parser also fails to parse the contract's 50+ bucket."),
    "201331696": ("unparsed_bucket_and_unbound_reference_period", "Fed rate cut odds",
        "Generic rate-cut odds do not supply a July 50+ bp implication. The contract's 50+ bucket produces an empty basis-point list, which the extractor accepts as having no required bucket."),
    "199965294": ("missing_exact_count_and_period_binding", "Fed has cut its target rate to 3.75%",
        "A past cut/rate level does not identify exactly one or exactly two cuts in calendar 2026. The extractor gives YES to both mutually exclusive annual count buckets without extracting a count or binding the period."),
    "211002653": ("unbound_action", "futures traders cut risk",
        "The subject of 'cut' is futures traders and the object is risk. A separate 'Fed' mention causes the extractor to label a Fed rate cut and support the exactly-one-cut contract."),
    "202999082": ("negation_and_count_binding", "Fed rate cut bets ease",
        "Easing rate-cut bets is not evidence fixing exactly two annual cuts. The extractor ignores the modifier 'ease' and the contract count, returning positive exact direction."),
}


def main():
    target = OUT / "coverage_interpretation.json"
    if target.exists():
        raise SystemExit("Preserve existing interpretation")
    manifest = json.loads((OUT / "manifest.json").read_text())
    for entry in manifest["artifacts"]:
        if sha256_file(REPO_ROOT / entry["path"]) != entry["sha256"]:
            raise RuntimeError("Diagnostic manifest mismatch")
    records = list(read_jsonl(OUT / "signed_association_trace.jsonl"))
    report = json.loads((OUT / "report.json").read_text())
    markets = {r["market_id"]: r for r in read_jsonl(MARKETS)}
    covered = [r for r in records if r["folds"]["4"]["exclusive_reason"] == "reaches_signed_features"]
    articles = {}
    for raw in read_jsonl(NEWS):
        article_id = str(raw["id"])
        if article_id not in FINDINGS:
            continue
        required = next(r["available_at"] for r in covered if r["article_id"] == article_id)
        if datetime.fromisoformat(raw["available_at"].replace("Z", "+00:00")) == datetime.fromisoformat(required):
            articles[article_id] = {"headline": raw.get("headline"), "summary": raw.get("summary"),
                                    "available_at": raw["available_at"]}
    inspection = []
    for record in covered:
        article_id = record["article_id"]
        category, evidence, finding = FINDINGS[article_id]
        article = articles[article_id]
        if evidence.lower() not in " ".join(str(article.get(k) or "") for k in ("headline", "summary")).lower():
            raise RuntimeError("Inspection evidence span absent from supplied article")
        inspection.append({"event_index": record["event_index"], "article_id": article_id,
            "article": article, "market_id": record["market_id"], "question": record["question"],
            "matched_training_rows": record["folds"]["4"]["matched_rows"],
            "automatic": record["automatic"], "inspection_kind": "assistant_development_diagnostic_not_gold",
            "supplied_span": evidence, "failure_category": category, "finding": finding,
            "explicit_exact_contract_implication_supported_by_supplied_text": False})
    absent = [r for r in records if r["folds"]["5"]["exclusive_reason"] == "no_eligible_oof_rows_for_matching_market_group"]
    gap = [r for r in records if r["folds"]["5"]["exclusive_reason"] == "no_eligible_decision_in_30m_window"]
    finite = [r["folds"]["5"]["minutes_to_first_oof_decision"] for r in gap
              if r["folds"]["5"]["minutes_to_first_oof_decision"] is not None]
    beyond_terminal = sum(datetime.fromisoformat(r["available_at"]) > datetime.fromisoformat(markets[r["market_id"]]["terminal_time"].replace("Z", "+00:00")) for r in absent)
    beyond_last_trade = sum(datetime.fromisoformat(r["available_at"]) > datetime.fromisoformat(markets[r["market_id"]]["last_trade_ts"].replace("Z", "+00:00")) for r in absent)
    examples = {}
    for fold in ("4", "5"):
        hits = [r for r in records if r["folds"][fold]["all_groups_existing_example_rows_in_window"]]
        examples[fold] = {"associations_reaching_any_group_existing_example": len(hits),
            "articles": len({r["article_id"] for r in hits}), "markets": len({r["market_id"] for r in hits}),
            "unique_rows": report["folds"][fold]["all_groups_existing_eligible_examples_with_signed_evidence"],
            "not_a_new_model_evaluation": True}
    interpreted = {"training_semantic_inspection": {"associations": len(inspection),
        "articles": len(articles), "covered_rows": sum(r["matched_training_rows"] for r in inspection),
        "all_signs_positive": all(r["automatic"]["direction"] == 1 for r in inspection),
        "explicit_exact_implication_supported_pairs_under_assistant_inspection": 0,
        "not_independent_accuracy_or_formal_adjudication": True},
        "evaluation_no_market_rows": {"associations": len(absent), "markets": len({r["market_id"] for r in absent}),
            "after_cached_terminal_time": beyond_terminal, "after_last_observed_trade": beyond_last_trade,
            "historical_active_status_certified": False},
        "evaluation_no_30m_row": {"associations": len(gap), "markets": len({r["market_id"] for r in gap}),
            "has_later_decision": len(finite), "no_later_decision_in_fold": len(gap)-len(finite),
            "next_decision_gap_min_minutes": min(finite), "next_decision_gap_median_minutes": float(np.median(finite)),
            "next_decision_gap_max_minutes": max(finite)},
        "any_group_example_coverage": examples,
        "extractor_by_applicability": dict(Counter({kind: sum(r["associations"] for r in report["extractor_partition"] if r["applicability"] == kind) for kind in ("exact", "material", "none")})),
        "interpretation": "Sparse overlap of clock, held market group and eligible decision rows explains zero evaluation coverage. Article-wide regex binding, unsupported buckets and counts also compromise the few training hits. Availability delays are large but do not alone establish causation of missing rows."}
    write_jsonl(OUT / "semantic_inspection.jsonl", inspection)
    write_json(target, interpreted)
    write_json(OUT / "interpretation_manifest.json", {"artifacts": [{"path": str(p.relative_to(REPO_ROOT)), "sha256": sha256_file(p)} for p in (target, OUT / "semantic_inspection.jsonl", REPO_ROOT / "eventx/tasks/interpret_v7_signed_evidence_coverage_20261012.py")]})
    print(json.dumps(interpreted, indent=2))


if __name__ == "__main__":
    main()
