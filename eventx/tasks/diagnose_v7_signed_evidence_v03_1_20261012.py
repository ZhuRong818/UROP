"""Compare v0.3.1 predicate/coverage decisions on previously opened text and keys.

No software test suite, outcome field, forecast fit or holdout is used.
"""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np

from eventx.tasks.diagnose_v7_signed_evidence_coverage_20261012 import (
    OUT as PREVIOUS, groups, utc, window_rows, write_json, write_jsonl,
)
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE, load_documents
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE, FOLDS
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE
from eventx.tasks.run_v5_residual_feasibility import REPO_ROOT, OOF, EVENTS, EXAMPLES, MARKETS, START_US, read_jsonl, sha256_file
from eventx.tasks.run_v7_signed_evidence_exploration_20261010 import aggregate_features
from eventx.v7.signed_evidence_v03_1 import extract_signed_evidence

OUT = REPO_ROOT / "data/v7/signed_evidence_v03_1_development_20261012"
MINUTE_US = 60_000_000
WINDOW = 30*MINUTE_US


def main():
    if OUT.exists():
        raise SystemExit("Preserve existing output; use a new diagnostic version")
    receipt = json.loads((PREVIOUS / "input_receipt.json").read_text())
    verified = dict(receipt["verified_locked_files"])
    for entry in json.loads((PREVIOUS / "publication_manifest.json").read_text())["artifacts"]:
        verified[entry["path"]] = entry["sha256"]
    for path, digest in verified.items():
        if sha256_file(REPO_ROOT / path) != digest:
            raise RuntimeError(f"Locked input changed: {path}")
    OUT.mkdir(parents=True)
    sources = (Path(__file__).resolve(), REPO_ROOT / "eventx/v7/signed_evidence_v03_1.py")
    contract = {"created_at": datetime.now(timezone.utc).isoformat(), "role": "opened development extraction/coverage diagnostic",
        "inputs": [{"path": p, "sha256": digest} for p, digest in sorted(verified.items())],
        "new_code": [{"path": str(p.relative_to(REPO_ROOT)), "sha256": sha256_file(p)} for p in sources],
        "policy": {"extractor_version": "0.3.1", "availability_year_anchor": "Explicit month or this-year expressions only; never infer a missing month.",
                   "signed_admission": "exact with nonzero direction", "window": "(decision_at-30m, decision_at]",
                   "no_clock_group_or_eligibility_changes": True, "software_tests_run": False, "forecast_fits": 0}}
    write_json(OUT / "contract.json", contract)
    print(f"Verified {len(verified)} hashes; v0.3.1 code receipted before corpus processing", flush=True)
    raw = np.memmap(OOF, mode="r", dtype=OOF_DTYPE)
    oof = np.empty(len(raw), dtype=[("market", "<u4"), ("minute", "<i4"), ("fold", "u1")])
    for name in oof.dtype.names:
        oof[name] = raw[name]
    del raw
    raw = np.memmap(EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE)
    examples = np.empty(len(raw), dtype=[("market", "<u4"), ("minute", "<i4"), ("group", "u1")])
    for name in examples.dtype.names:
        examples[name] = raw[name]
    del raw
    events = np.memmap(EVENTS, mode="r", dtype=EVENT_DTYPE)
    markets = {int(m["market_index"]): m for m in read_jsonl(MARKETS)}
    docs, docstats = load_documents()
    old = {r["event_index"]: r for r in read_jsonl(PREVIOUS / "signed_association_trace.jsonl")}
    signed = np.zeros((len(events), 3), dtype=np.float32)
    classifications, changes, exact, old_replay = Counter(), Counter(), [], []
    cache, exact_indices = {}, set()
    for index, e in enumerate(events):
        market, document = int(e["market"]), int(e["document"])
        key = document, market
        doc = docs[document]
        summary = doc["text"][len(doc["headline"]):].strip() if doc["text"].startswith(doc["headline"]) else doc["text"]
        result = cache.get(key)
        if result is None:
            result = extract_signed_evidence(doc["headline"], summary, markets[market]["question"], available_at=doc["available_at"])
            cache[key] = result
        classifications[(result.applicability, result.reason)] += 1
        if index in old:
            changes[result.reason if result.direction == 0 else "retained_exact_direction"] += 1
            old_replay.append({"event_index": index, "article_id": doc["doc_id"], "market_id": markets[market]["market_id"],
                               "previous": old[index]["automatic"], "v03": result.to_dict()})
        if result.applicability != "exact" or not result.direction:
            continue
        exact_indices.add(index)
        value = result.direction*result.confidence
        signed[index] = (value, value if result.claim_type == "forecast" else 0,
                         value if result.claim_type in ("observed_action", "observed_measurement") else 0)
        source = "\n".join(s for s in (doc["headline"], summary) if s)
        if any(source[c.evidence_start:c.evidence_end] != c.evidence_span for c in result.bound_claims):
            raise RuntimeError("Evidence span does not reproduce source substring")
        exact.append({"event_index": index, "article_id": doc["doc_id"], "market_index": market,
                      "market_id": markets[market]["market_id"], "question": markets[market]["question"],
                      "market_group": markets[market]["market_group"], "available_at": doc["available_at"].isoformat(),
                      "source_text": source, "v03": result.to_dict(), "folds": {}})
    print(f"v0.3.1 exact associations: {len(exact)}; previous retained: {len(exact_indices & set(old))}", flush=True)
    folds, row_traces = {}, []
    example_groups = groups(examples, "market")
    for fold, held_group, start_min, end_min in FOLDS:
        selected = np.flatnonzero(oof["fold"] == fold)
        control, features = aggregate_features(oof, events, selected, signed)
        covered, exposed = features[:, 1] > 0, control[:, 0] > 0
        if np.any(covered & ~exposed):
            raise RuntimeError("Signed evidence lost by exposure gate")
        by_market = {m: selected[idx][np.argsort(oof["minute"][selected[idx]])] for m, idx in groups(oof[selected], "market").items()}
        start, end = START_US+start_min*MINUTE_US, START_US+end_min*MINUTE_US
        reasons, touched, all_groups, contributing = Counter(), set(), set(), []
        for record in exact:
            index, market = record["event_index"], record["market_index"]
            t = int(events["timestamp_us"][index])
            idx = by_market.get(market, np.empty(0, dtype=int))
            times = START_US+oof["minute"][idx].astype(np.int64)*MINUTE_US
            lo, hi = window_rows(times, t)
            hits = idx[lo:hi]
            touched.update(int(x) for x in hits)
            reason = "outside_fold_clock_window" if not (t < end and t+WINDOW > start) else "different_held_market_group" if record["market_group"] != held_group else "no_eligible_oof_market_rows" if not len(idx) else "no_eligible_decision_in_30m_window" if not len(hits) else "reaches_signed_features"
            reasons[reason] += 1
            if len(hits):
                contributing.append(record)
            exidx = example_groups.get(market, np.empty(0, dtype=int))
            exidx = exidx[(examples["minute"][exidx] >= start_min) & (examples["minute"][exidx] < end_min)]
            exidx = exidx[np.argsort(examples["minute"][exidx])]
            exlo, exhi = window_rows(START_US+examples["minute"][exidx].astype(np.int64)*MINUTE_US, t)
            all_groups.update(int(x) for x in exidx[exlo:exhi])
            record["folds"][str(fold)] = {"exclusive_reason": reason, "matched_rows": len(hits),
                                        "all_groups_existing_example_rows": exhi-exlo}
        if touched != set(int(x) for x in selected[covered]):
            raise RuntimeError("Event-to-row trace and original aggregator disagree")
        for pos in np.flatnonzero(covered):
            row_traces.append({"oof_index": int(selected[pos]), "fold": fold,
                "market_index": int(oof["market"][selected[pos]]), "decision_at": utc(START_US+int(oof["minute"][selected[pos]])*MINUTE_US),
                "signed_features": features[pos].tolist()})
        folds[str(fold)] = {"news_exposed_rows": int(exposed.sum()), "signed_rows": int(covered.sum()),
                           "articles": len({r["article_id"] for r in contributing}), "markets": len({r["market_index"] for r in contributing}),
                           "exclusive_association_reasons": dict(reasons), "all_groups_existing_example_signed_rows": len(all_groups)}
        print(f"Fold {fold}: {covered.sum()} signed rows", flush=True)
    replay = []
    for record in read_jsonl(PREVIOUS / "semantic_inspection.jsonl"):
        article = record["article"]
        result = extract_signed_evidence(article["headline"], article["summary"], record["question"], available_at=article["available_at"])
        replay.append({"event_index": record["event_index"], "article_id": record["article_id"], "question": record["question"],
                       "previous_covered_rows": record["matched_training_rows"], "v03": result.to_dict()})
    report = {"status": "complete", "scope": "opened development extraction/coverage diagnostic; no forecasting metrics",
        "documents": docstats, "associations_processed": len(events),
        "v02_exact_associations": len(old), "v03_exact_associations": len(exact),
        "v03_exact_articles": len({r["article_id"] for r in exact}), "v03_exact_markets": len({r["market_index"] for r in exact}),
        "old_exact_retained": len(exact_indices & set(old)), "old_exact_removed": len(set(old)-exact_indices),
        "new_exact_added": len(exact_indices-set(old)), "old_exact_decision_changes": dict(changes),
        "partition": [{"applicability": a, "reason": b, "associations": n} for (a,b), n in sorted(classifications.items())],
        "known_six_previous_fitting_links": {"pairs": len(replay), "still_signed": sum(r["v03"]["direction"] != 0 for r in replay),
            "previous_covered_rows": sum(r["previous_covered_rows"] for r in replay), "assistant_debugging_set_not_accuracy_estimate": True},
        "folds": folds, "checks": {"locked_hashes_verified": len(verified), "positive_evidence_spans_match": True,
            "event_to_row_trace_equals_aggregator": True, "outcome_fields_read": False,
            "protected_payloads_read": False, "forecast_models_fit": 0, "software_tests_run": False},
        "limits": ["Grammar repair is not independently reviewed semantic accuracy.", "Availability-year anchoring is explicit and not historical source certification.",
                   "Coverage uses the unchanged legacy retrieval, groups, eligibility and 30m window.", "No predictive lift or episode independence is established."]}
    write_json(OUT / "report.json", report)
    write_jsonl(OUT / "exact_association_trace.jsonl", exact)
    write_jsonl(OUT / "previous_exact_decisions.jsonl", old_replay)
    write_jsonl(OUT / "known_fitting_link_replay.jsonl", replay)
    write_jsonl(OUT / "covered_row_trace.jsonl", row_traces)
    for p, receipt_entry in zip(sources, contract["new_code"]):
        if sha256_file(p) != receipt_entry["sha256"]:
            raise RuntimeError("Code changed during corpus diagnostic")
    paths = sorted(p for p in OUT.iterdir() if p.is_file())+list(sources)
    write_json(OUT / "manifest.json", {"artifacts": [{"path": str(p.relative_to(REPO_ROOT)), "sha256": sha256_file(p)} for p in paths]})
    print(json.dumps({k: report[k] for k in ("v03_exact_associations", "v03_exact_articles", "v03_exact_markets", "old_exact_removed", "new_exact_added", "known_six_previous_fitting_links")}, indent=2))


if __name__ == "__main__":
    main()
