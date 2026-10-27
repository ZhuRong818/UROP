"""Trace opened signed-evidence coverage without fitting or reading outcome fields.

All interval, extraction and cohort rules remain those of the original trial.
Coverage outside its held group is a descriptive diagnostic, not a new evaluation.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np

from eventx.tasks.prepare_v4_discovery_news_quality import NEWS, EVENT_DTYPE, load_documents
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE, FOLDS
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE
from eventx.tasks.run_v5_residual_feasibility import (
    REPO_ROOT, EVENTS, OOF, MARKETS, START_US, EVENT_MANIFEST, OOF_MANIFEST,
    EXAMPLES, EXAMPLES_MANIFEST, read_jsonl, sha256_file,
)
from eventx.tasks.run_v7_signed_evidence_exploration_20261010 import aggregate_features
from eventx.v7.signed_evidence_v02 import extract_signed_evidence

MINUTE_US = 60_000_000
WINDOW = 30 * MINUTE_US
OLD = REPO_ROOT / "data/v7/signed_evidence_exploration_20261010"
OUT = REPO_ROOT / "data/v7/signed_evidence_coverage_diagnostic_20261012"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def write_jsonl(path, rows):
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def utc(t):
    return datetime.fromtimestamp(int(t) / 1_000_000, timezone.utc).isoformat()


def groups(rows, field):
    result = {}
    for key in np.unique(rows[field]):
        result[int(key)] = np.flatnonzero(rows[field] == key)
    return result


def window_rows(times, event_time):
    # Equivalent to event_time in (decision_time - 30m, decision_time].
    lo = np.searchsorted(times, event_time, side="left")
    hi = np.searchsorted(times, event_time + WINDOW, side="left")
    return int(lo), int(hi)


def main():
    if OUT.exists():
        raise SystemExit("Preserve existing output; use another diagnostic version")
    verified = {}
    for manifest_path in (OLD / "manifest.json", OLD / "contract.json",
                          EVENT_MANIFEST, OOF_MANIFEST, EXAMPLES_MANIFEST):
        manifest = json.loads(manifest_path.read_text())
        for entry in manifest.get("artifacts", []) + manifest.get("inputs", []):
            path = REPO_ROOT / entry["path"]
            if entry["path"] not in verified:
                digest = sha256_file(path)
                if digest != entry["sha256"]:
                    raise RuntimeError(f"Hash mismatch: {entry['path']}")
                verified[entry["path"]] = digest
    print(f"Verified {len(verified)} locked input/artifact hashes", flush=True)
    # Copy only key fields. Outcome/prediction/features fields are never accessed.
    raw_oof = np.memmap(OOF, mode="r", dtype=OOF_DTYPE)
    oof = np.empty(len(raw_oof), dtype=[("market", "<u4"), ("minute", "<i4"), ("fold", "u1")])
    for field in oof.dtype.names:
        oof[field] = raw_oof[field]
    del raw_oof
    raw_examples = np.memmap(EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE)
    examples = np.empty(len(raw_examples), dtype=[("market", "<u4"), ("minute", "<i4"), ("group", "u1")])
    for field in examples.dtype.names:
        examples[field] = raw_examples[field]
    del raw_examples
    events = np.memmap(EVENTS, mode="r", dtype=EVENT_DTYPE)
    markets = list(read_jsonl(MARKETS))
    documents, document_stats = load_documents()
    market_lookup = {int(m["market_index"]): m for m in markets}
    if list(sorted(market_lookup)) != list(range(len(markets))):
        raise RuntimeError("Invalid market index")
    if np.any(events["market"][1:] < events["market"][:-1]):
        raise RuntimeError("Events are not market sorted")
    ebym = groups(events, "market")
    for idx in ebym.values():
        if np.any(np.diff(events["timestamp_us"][idx]) < 0):
            raise RuntimeError("Within-market events are not chronological")
    if int(events["document"].max()) >= len(documents):
        raise RuntimeError("Document index out of bounds")
    clock_mismatches = sum(int(e["timestamp_us"]) != int(round(documents[int(e["document"])]["available_at"].timestamp()*1e6)) for e in events)
    if clock_mismatches:
        raise RuntimeError("Source document/event clocks differ")
    print(f"Loaded {len(documents)} documents, {len(events)} associations; clocks match", flush=True)
    signed = np.zeros((len(events), 3), dtype=np.float32)
    extraction = Counter()
    records = []
    cache = {}
    for i, e in enumerate(events):
        market, document = int(e["market"]), int(e["document"])
        key = (document, market)
        result = cache.get(key)
        if result is None:
            doc = documents[document]
            summary = doc["text"][len(doc["headline"]):].strip() if doc["text"].startswith(doc["headline"]) else doc["text"]
            result = extract_signed_evidence(doc["headline"], summary, market_lookup[market]["question"])
            cache[key] = result
        extraction[(result.applicability, result.reason)] += 1
        if result.applicability != "exact" or not result.direction:
            continue
        value = result.direction * result.confidence
        signed[i] = (value, value if result.claim_type == "forecast" else 0,
                     value if result.claim_type in ("observed_action", "observed_measurement") else 0)
        doc, m = documents[document], market_lookup[market]
        records.append({"event_index": i, "document_index": document, "article_id": doc["doc_id"],
                        "market_index": market, "market_id": m["market_id"], "venue": m["venue"],
                        "market_group": m["market_group"], "headline": doc["headline"],
                        "question": m["question"], "available_at": utc(e["timestamp_us"]),
                        "published_at": doc["published_at"].isoformat(),
                        "lag_minutes": (doc["available_at"]-doc["published_at"]).total_seconds()/60,
                        "automatic": result.to_dict(), "folds": {}})
    print(f"Extracted {len(records)} automatic exact signed associations", flush=True)
    all_examples_by_market = groups(examples, "market")
    all_oof_by_market = groups(oof, "market")
    row_traces, summaries = [], {}
    for fold, held_group, start_min, end_min in FOLDS:
        selected = np.flatnonzero(oof["fold"] == fold)
        control, feature = aggregate_features(oof, events, selected, signed)
        exposed = control[:, 0] > 0
        covered = feature[:, 1] > 0
        if not np.array_equal(covered, np.any(feature != 0, axis=1)):
            raise RuntimeError("Presence checks disagree")
        if np.any(covered & ~exposed):
            raise RuntimeError("Exposure gate removed signed evidence")
        fold_by_market = groups(oof[selected], "market")
        fold_rows = {m: selected[idx][np.argsort(oof["minute"][selected[idx]])] for m, idx in fold_by_market.items()}
        start, end = START_US+start_min*MINUTE_US, START_US+end_min*MINUTE_US
        reasons, flags, touched, all_group_touched = Counter(), Counter(), set(), set()
        temporal_records, group_records, retained = [], [], []
        for record in records:
            market = record["market_index"]
            t = int(events["timestamp_us"][record["event_index"]])
            overlaps = t < end and t+WINDOW > start
            group_ok = int(record["market_group"]) == held_group
            idx = fold_rows.get(market, np.empty(0, dtype=int))
            times = START_US + oof["minute"][idx].astype(np.int64)*MINUTE_US
            lo, hi = window_rows(times, t)
            hits = idx[lo:hi]
            touched.update(int(r) for r in hits)
            no_oof_ever = market not in all_oof_by_market
            for name, condition in {"outside_fold_clock_window": not overlaps,
                                    "different_held_market_group": not group_ok,
                                    "market_has_no_oof_rows_in_any_fold": no_oof_ever,
                                    "market_has_no_rows_in_this_fold": not len(idx),
                                    "no_decision_in_30m_window": not len(hits)}.items():
                flags[name] += int(condition)
            if not overlaps:
                reason = "outside_fold_clock_window"
            elif not group_ok:
                reason = "different_held_market_group"
            elif not len(idx):
                reason = "no_eligible_oof_rows_for_matching_market_group"
            elif not len(hits):
                reason = "no_eligible_decision_in_30m_window"
            else:
                reason = "reaches_signed_features"
                retained.append(record)
            reasons[reason] += 1
            if overlaps:
                temporal_records.append(record)
                if group_ok:
                    group_records.append(record)
            # Existing eligible example keys, all groups, same historical dates.
            exidx = all_examples_by_market.get(market, np.empty(0, dtype=int))
            exidx = exidx[(examples["minute"][exidx] >= start_min) & (examples["minute"][exidx] < end_min)]
            exidx = exidx[np.argsort(examples["minute"][exidx])]
            extimes = START_US+examples["minute"][exidx].astype(np.int64)*MINUTE_US
            exlo, exhi = window_rows(extimes, t)
            all_group_touched.update(int(r) for r in exidx[exlo:exhi])
            after = int(np.searchsorted(times, t, side="left"))
            first_after = int(times[after]) if after < len(times) else None
            last_before = int(times[after-1]) if after else None
            record["folds"][str(fold)] = {"exclusive_reason": reason,
                "clock_window_overlaps_fold": overlaps, "held_group_matches": group_ok,
                "market_oof_rows": len(idx), "matched_rows": len(hits),
                "all_groups_existing_example_rows_in_window": exhi-exlo,
                "first_oof_decision_at_or_after_arrival": utc(first_after) if first_after is not None else None,
                "minutes_to_first_oof_decision": (first_after-t)/MINUTE_US if first_after is not None else None,
                "last_oof_decision_before_arrival": utc(last_before) if last_before is not None else None}
        if touched != set(int(r) for r in selected[covered]):
            raise RuntimeError("Independent event-to-row trace differs from original aggregator")
        for pos in np.flatnonzero(covered):
            index = int(selected[pos])
            t, m = START_US+int(oof["minute"][index])*MINUTE_US, int(oof["market"][index])
            source = [r for r in records if r["market_index"] == m
                      and t-WINDOW < int(events["timestamp_us"][r["event_index"]]) <= t]
            row_traces.append({"oof_index": index, "fold": fold, "market_index": m,
                               "decision_at": utc(t), "event_indices": [r["event_index"] for r in source],
                               "article_ids": [r["article_id"] for r in source],
                               "signed_features": feature[pos].tolist()})
        def count(rs):
            return {"associations": len(rs), "articles": len({r["article_id"] for r in rs}),
                    "markets": len({r["market_index"] for r in rs})}
        summaries[str(fold)] = {"start_inclusive": utc(start), "end_exclusive": utc(end),
            "held_market_group": held_group, "all_oof_rows": len(selected),
            "news_exposed_rows": int(exposed.sum()), "signed_rows": int(covered.sum()),
            "signed_articles": len({r["article_id"] for r in retained}),
            "signed_markets": len({r["market_index"] for r in retained}),
            "funnel": {"all_signed": count(records), "window_overlaps_dates": count(temporal_records),
                       "also_matches_held_market_group": count(group_records), "reaches_rows": count(retained)},
            "exclusive_reasons_in_clock_then_group_then_row_order": dict(reasons),
            "overlapping_flags_not_additive": dict(flags),
            "all_groups_existing_eligible_examples_with_signed_evidence": len(all_group_touched),
            "signed_presence_vs_any_nonzero_equal": True, "exposure_gate_removed_signed_rows": 0}
        print(f"Fold {fold}: {dict(reasons)}; signed rows {covered.sum()}", flush=True)
    previous = json.loads((OLD / "report.json").read_text())["comparison"]
    for field, actual in {"automatic_exact_signed_event_associations": len(records),
                          "training_rows_with_signed_evidence": summaries["4"]["signed_rows"],
                          "evaluation_rows_with_signed_evidence": summaries["5"]["signed_rows"],
                          "training_rows_identical_between_arms": summaries["4"]["news_exposed_rows"],
                          "evaluation_rows_identical_between_arms": summaries["5"]["news_exposed_rows"]}.items():
        if previous[field] != actual:
            raise RuntimeError(f"Original trial reproduction failed: {field}")
    duplicate_keys = len(records)-len({(r["document_index"], r["market_index"], r["available_at"]) for r in records})
    lag = np.asarray([r["lag_minutes"] for r in records])
    article_lag = {r["article_id"]: r["lag_minutes"] for r in records}
    report = {"status": "complete", "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Opened development key/text-only diagnosis; no fits or outcome-field reads",
        "documents": document_stats, "association_rows": len(events),
        "automatic_exact_signed": {"associations": len(records),
            "articles": len(article_lag), "markets": len({r["market_index"] for r in records}),
            "duplicate_document_market_clock_keys": duplicate_keys,
            "by_venue": dict(Counter(r["venue"] for r in records)),
            "by_market_group": dict(Counter(str(r["market_group"]) for r in records)),
            "by_direction": dict(Counter(str(r["automatic"]["direction"]) for r in records)),
            "by_claim_type": dict(Counter(r["automatic"]["claim_type"] for r in records)),
            "availability_min": min(r["available_at"] for r in records),
            "availability_max": max(r["available_at"] for r in records),
            "article_lag_minutes_quantiles": {str(q): float(np.quantile(list(article_lag.values()), q)) for q in (0,.5,.9,1)},
            "articles_lag_over_30m": sum(v > 30 for v in article_lag.values()),
            "association_lag_over_30m": int((lag > 30).sum())},
        "extractor_partition": [{"applicability": key[0], "reason": key[1], "associations": value}
                                for key, value in sorted(extraction.items())],
        "folds": summaries,
        "checks": {"all_source_event_availability_clocks_match": clock_mismatches == 0,
            "original_1559_21_0_and_4577_5388_reproduced": True,
            "event_trace_equals_original_feature_aggregator_all_folds": True,
            "locked_hashes_verified": len(verified), "outcome_fields_accessed": False,
            "models_fit": 0, "protected_holdouts_accessed": False},
        "limits": ["Automatic exact labels are unvalidated heuristics, not semantic gold.",
                   "Article arrivals are not independently verified information episodes or surprises.",
                   "No-eligible-row reasons do not establish stale trade versus missing upstream support.",
                   "All-group example coverage is descriptive; not a replacement split or evaluation.",
                   "Availability lag diagnoses delay, not when public information first became known."]}
    OUT.mkdir(parents=True)
    write_json(OUT / "report.json", report)
    write_jsonl(OUT / "signed_association_trace.jsonl", records)
    write_jsonl(OUT / "covered_row_trace.jsonl", row_traces)
    write_json(OUT / "input_receipt.json", {"verified_locked_files": verified,
        "fields_read_from_oof": list(oof.dtype.names), "fields_read_from_examples": list(examples.dtype.names),
        "original_rule": "available_at in (decision_time-30 minutes, decision_time]",
        "no_model_refit": True, "no_outcome_field_access": True})
    artifacts = [OUT / n for n in ("report.json", "signed_association_trace.jsonl", "covered_row_trace.jsonl", "input_receipt.json")]
    artifacts.append(Path(__file__).resolve())
    write_json(OUT / "manifest.json", {"artifacts": [{"path": str(p.relative_to(REPO_ROOT)), "sha256": sha256_file(p)} for p in artifacts]})
    print(json.dumps(report["automatic_exact_signed"], indent=2), flush=True)


if __name__ == "__main__":
    main()
