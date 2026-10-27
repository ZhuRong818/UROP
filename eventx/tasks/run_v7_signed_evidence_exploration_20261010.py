"""Inspect the V7 review diagnostic, build an event ledger, and run one opened comparison.

This task reads only opened discovery outcomes. It does not touch the consumed OOT
holdout or the sealed V4 confirmation interval.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit

from eventx.tasks.audit_v5_algorithms import MINUTE_US, block_interval, recent_news
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE, load_documents
from eventx.tasks.run_v4_discovery_models import OOF_DTYPE
from eventx.tasks.run_v5_residual_feasibility import (
    EVENT_MANIFEST, EVENTS, FUTURE, MARKETS, OOF, OOF_MANIFEST, REPO_ROOT,
    START_US, metric, point_loss, read_jsonl, sha256_file, verify_manifest,
)
from eventx.v7.signed_evidence_v02 import extract_signed_evidence

DIAGNOSTIC = REPO_ROOT / "data/v7/macro_review_diagnostic_20261010"
BASELINE = REPO_ROOT / "data/v5/market_learner_screen_20261009"
OUT = REPO_ROOT / "data/v7/signed_evidence_exploration_20261010"
PENALTY = 0.1
REPEAT_ARTICLES = {"63246982": "Repeats the April 3 official jobs release at May 18 availability."}

ARTICLE_FINDINGS = {
    "120127568": "Preview/calendar mention of PCE; no reported PCE value or contract-specific direction.",
    "171511251": "Observed employment report plus general trader expectation; no prediction-market odds and no 50 bp bucket implication.",
    "172985266": "Corporate dividend/stress-test context; lexical Fed overlap is incompatible with the rate predicate.",
    "173603179": "Reported May payroll value binds the >100K predicate, but the article arrived after nominal close.",
    "184027675": "General trader expectation of an unchanged June range; no explicit prediction-market odds; exact links are after close.",
    "185269879": "Dividend-stock commentary with incidental inflation language; no contract-specific claim.",
    "189435511": "Attributed Bank of America rate-path forecast; two timely exact links are one information event.",
    "191355243": "Corporate dividend/buyback/stress-test story; no macro contract predicate.",
    "192168259": "Attributed policy commentary; insufficient to identify a June dissent outcome and after close for that contract.",
    "194294142": "Investment commentary with incidental core-PCE language; topic context only.",
    "199597821": "Observed private-payroll slowdown; policy context without an exact July cut-bucket implication.",
    "203130448": "Payroll-miss headline with insufficient supplied value/period binding; expired May contract and contextual July link.",
    "63246982": "Retrospective repetition of a dated April 3 jobs release, observed on May 18; not a new release event.",
}


def write_json(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    temporary.replace(path)


def fit_offset(x: np.ndarray, y: np.ndarray, baseline: np.ndarray) -> tuple[np.ndarray, dict]:
    mean, scale = x.mean(0), x.std(0)
    scale[scale < 1e-12] = 1.0
    design = np.column_stack((np.ones(len(x)), (x - mean) / scale))
    offset = logit(np.clip(baseline, 1e-7, 1 - 1e-7))

    def objective(beta):
        z = offset + design @ beta
        value = np.mean(np.logaddexp(0, z) - y * z) + PENALTY * np.dot(beta[1:], beta[1:]) / 2
        gradient = design.T @ (expit(z) - y) / len(y)
        gradient[1:] += PENALTY * beta[1:]
        return float(value), gradient

    result = minimize(objective, np.zeros(design.shape[1]), method="L-BFGS-B", jac=True,
                      options={"maxiter": 2000, "gtol": 1e-7, "ftol": 1e-12})
    if not result.success or not np.all(np.isfinite(result.x)):
        raise RuntimeError(f"Offset fit failed: {result.message}")
    return result.x, {"mean": mean.tolist(), "scale": scale.tolist(),
                      "iterations": int(result.nit), "objective": float(result.fun)}


def predict_offset(x, baseline, beta, fit):
    standardized = (x - np.asarray(fit["mean"])) / np.asarray(fit["scale"])
    return expit(logit(np.clip(baseline, 1e-7, 1 - 1e-7)) + beta[0] + standardized @ beta[1:])


def inspect_queue() -> tuple[list[dict], dict]:
    rows = list(read_jsonl(DIAGNOSTIC / "priority_diagnostic_cases.jsonl"))
    out = []
    for row in rows:
        article = row["packet"]["article"]
        contract = row["packet"]["contract"]
        automatic = extract_signed_evidence(article.get("headline"), article.get("summary"), contract.get("question"))
        out.append({
            "pair_id": row["pair_id"], "article_id": str(article["article_id"]),
            "contract_id": contract["contract_id"], "headline": article.get("headline"),
            "question": contract.get("question"), "priority_reasons": row["priority_reasons"],
            "reviewer_A_applicability": row["reviewer_A"]["applicability"],
            "reviewer_B_applicability": row["reviewer_B"]["applicability"],
            "nominal_timing": row["nominal_timing"], "source_context": row["source_context"],
            "article_finding": ARTICLE_FINDINGS[str(article["article_id"])],
            "automatic_v02": automatic.to_dict(),
        })
    exact = [r for r in out if r["reviewer_A_applicability"] == "exact_predicate"
             and r["reviewer_B_applicability"] == "exact_predicate"]
    timely_exact = [r for r in exact if r["nominal_timing"]["full_nominal_landmark_horizon"]
                    and not r["nominal_timing"]["at_or_after_nominal_close"]
                    and not r["nominal_timing"]["before_nominal_open"]]
    summary = {
        "pairs": len(out), "articles": len({r["article_id"] for r in out}),
        "joint_exact_pairs": len(exact), "joint_exact_articles": len({r["article_id"] for r in exact}),
        "nominally_timely_joint_exact_pairs": len(timely_exact),
        "nominally_timely_joint_exact_information_events": len({r["article_id"] for r in timely_exact}),
        "timely_exact_article_ids": sorted({r["article_id"] for r in timely_exact}),
        "source_certified_timely_exact_events": 0,
    }
    return out, summary


def event_ledger() -> tuple[list[dict], dict]:
    cases = list(read_jsonl(DIAGNOSTIC / "comparison_cases.jsonl"))
    material = [r for r in cases if r["reviewer_A"]["applicability"] in ("exact_predicate", "material_context")
                and r["reviewer_B"]["applicability"] in ("exact_predicate", "material_context")]
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in material:
        grouped[str(row["packet"]["article"]["article_id"])].append(row)
    ledger = []
    for article_id, rows in sorted(grouped.items()):
        first = rows[0]
        timely = [r for r in rows if r["nominal_timing"]["full_nominal_landmark_horizon"]
                  and not r["nominal_timing"]["at_or_after_nominal_close"]
                  and not r["nominal_timing"]["before_nominal_open"]]
        ledger.append({
            "information_event_id": f"article-arrival:{article_id}", "article_id": article_id,
            "headline": first["packet"]["article"]["headline"],
            "available_at": first["source_context"]["available_at"],
            "joint_material_or_exact_pairs": len(rows), "nominally_timely_pairs": len(timely),
            "has_nominally_timely_pair": bool(timely),
            "has_metadata_snapshot_not_after_article": any(not r["nominal_timing"]["snapshot_after_article"] for r in timely),
            "retrospective_repeat": article_id in REPEAT_ARTICLES,
            "repeat_note": REPEAT_ARTICLES.get(article_id),
            "run_status": first["source_context"]["run_status"],
            "historical_active_status_verified": all(r["nominal_timing"]["historical_active_status_verified"] for r in rows),
            "first_public_time": first["source_context"]["first_public_time"],
            "source_admitted": first["source_context"]["source_admitted"],
            "distinct_contracts": sorted({r["packet"]["contract"]["contract_id"] for r in rows}),
        })
    timely = [r for r in ledger if r["has_nominally_timely_pair"]]
    candidates = [r for r in timely if not r["retrospective_repeat"]]
    summary = {
        "joint_material_or_exact_pairs": len(material), "article_arrivals": len(ledger),
        "nominally_timely_pairs": sum(r["nominally_timely_pairs"] for r in ledger),
        "nominally_timely_article_arrivals": len(timely),
        "candidate_distinct_arrival_events_after_known_repeat_removal": len(candidates),
        "candidate_events_with_metadata_snapshot_not_after_article": sum(r["has_metadata_snapshot_not_after_article"] for r in candidates),
        "source_certified_first_public_events": 0, "historically_active_verified_events": 0,
        "interpretation": "Nine are candidate article-arrival episodes, not nine certified novel public events; first-public provenance and historical active status remain unknown.",
    }
    return ledger, summary


def aggregate_features(oof: np.ndarray, events: np.ndarray, selected: np.ndarray,
                       event_signed: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    base_news = recent_news(oof, events)[selected]
    control = np.zeros((len(selected), 3), dtype=float)
    signed = np.zeros((len(selected), 7), dtype=float)
    position = {int(index): pos for pos, index in enumerate(selected)}
    rows_by_market: dict[int, list[int]] = defaultdict(list)
    for index in selected:
        rows_by_market[int(oof["market"][index])].append(int(index))
    for market, market_rows in rows_by_market.items():
        rows = np.asarray(market_rows, dtype=int)
        a, b = np.searchsorted(events["market"], [market, market + 1])
        ev, ef = events[a:b], event_signed[a:b]
        grid = START_US + oof["minute"][rows].astype(np.int64) * MINUTE_US
        left = np.searchsorted(ev["timestamp_us"], grid - 30 * MINUTE_US, side="right")
        right = np.searchsorted(ev["timestamp_us"], grid, side="right")
        for row_index, lo, hi in zip(rows, left, right):
            pos = position[int(row_index)]
            if hi <= lo:
                continue
            window = ef[lo:hi]
            control[pos] = (np.log1p(hi - lo), base_news[pos, 2] / 30.0,
                            np.log1p(np.unique(ev["publisher"][lo:hi]).size))
            nonzero = np.flatnonzero(window[:, 0])
            if nonzero.size:
                values = window[nonzero]
                signed[pos] = (values[:, 0].sum(), len(values), values[-1, 0],
                               np.sum(values[:, 0] > 0), np.sum(values[:, 0] < 0),
                               values[:, 1].sum(), values[:, 2].sum())
    return control, signed


def run_comparison() -> dict:
    verify_manifest(OOF_MANIFEST); verify_manifest(EVENT_MANIFEST); verify_manifest(BASELINE / "manifest.json")
    oof = np.memmap(OOF, mode="r", dtype=OOF_DTYPE)
    events = np.memmap(EVENTS, mode="r", dtype=EVENT_DTYPE)
    documents, _ = load_documents()
    markets = list(read_jsonl(MARKETS))
    questions = {int(r["market_index"]): r["question"] for r in markets}
    event_signed = np.zeros((len(events), 3), dtype=np.float32)
    cache = {}
    for i, event in enumerate(events):
        key = (int(event["document"]), int(event["market"]))
        result = cache.get(key)
        if result is None:
            doc = documents[key[0]]
            summary = doc["text"][len(doc["headline"]):].strip() if doc["text"].startswith(doc["headline"]) else doc["text"]
            result = extract_signed_evidence(doc["headline"], summary, questions[key[1]])
            cache[key] = result
        if result.applicability == "exact" and result.direction:
            value = result.direction * result.confidence
            event_signed[i, 0] = value
            event_signed[i, 1] = value if result.claim_type == "forecast" else 0
            event_signed[i, 2] = value if result.claim_type in ("observed_measurement", "observed_action") else 0
    selected = np.flatnonzero((oof["fold"] == 4) | (oof["fold"] == 5))
    control, signed = aggregate_features(oof, events, selected, event_signed)
    exposed = control[:, 0] > 0
    with np.load(BASELINE / "predictions.npz", allow_pickle=False) as frozen:
        p4, p5 = frozen["hgb_7_600__fold4"], frozen["hgb_7_600__fold5"]
    baseline = np.concatenate((p4, p5))
    if len(baseline) != len(selected) or not np.array_equal(oof["fold"][selected], np.r_[np.full(len(p4), 4), np.full(len(p5), 5)]):
        raise RuntimeError("Strong-baseline prediction rows do not align with OOF folds 4 and 5")
    train = (oof["fold"][selected] == 4) & exposed
    evaluate = (oof["fold"][selected] == 5) & exposed
    x_control = control
    x_signed = np.column_stack((control, signed))
    beta_c, fit_c = fit_offset(x_control[train], oof["label"][selected][train], baseline[train])
    beta_s, fit_s = fit_offset(x_signed[train], oof["label"][selected][train], baseline[train])
    p_control = predict_offset(x_control[evaluate], baseline[evaluate], beta_c, fit_c)
    p_signed = predict_offset(x_signed[evaluate], baseline[evaluate], beta_s, fit_s)
    labels = oof["label"][selected][evaluate]
    delta = point_loss(labels, p_control) - point_loss(labels, p_signed)
    np.savez_compressed(OUT / "predictions.npz", market=oof["market"][selected][evaluate],
                        minute=oof["minute"][selected][evaluate], label=labels,
                        market_baseline=baseline[evaluate], control=p_control, signed=p_signed)
    return {
        "status": "complete", "train_fold": 4, "evaluation_fold": 5,
        "training_rows_identical_between_arms": int(train.sum()),
        "evaluation_rows_identical_between_arms": int(evaluate.sum()),
        "evaluation_markets": int(np.unique(oof["market"][selected][evaluate]).size),
        "automatic_exact_signed_event_associations": int(np.count_nonzero(event_signed[:, 0])),
        "training_rows_with_signed_evidence": int(np.count_nonzero(np.any(signed[train] != 0, axis=1))),
        "evaluation_rows_with_signed_evidence": int(np.count_nonzero(np.any(signed[evaluate] != 0, axis=1))),
        "metrics": {"strong_market_plus_exposure_timing": metric(labels, p_control),
                    "same_plus_automatic_signed_evidence": metric(labels, p_signed)},
        "signed_vs_control_log_loss": block_interval({"market": oof["market"][selected][evaluate]}, delta),
        "brier_improvement": float(metric(labels, p_control)["brier"] - metric(labels, p_signed)["brier"]),
        "fits": {"control": {"coefficients": beta_c.tolist(), **fit_c},
                 "signed": {"coefficients": beta_s.tolist(), **fit_s}},
        "feature_columns": {"control": ["log1p_30m_count", "latest_age_over_30", "log1p_distinct_publishers"],
                            "signed_added": ["signed_sum", "signed_count", "latest_sign", "yes_count", "no_count", "forecast_signed_sum", "observed_signed_sum"]},
        "claim_limit": "Opened post-selection exploration. It cannot demonstrate forecasting improvement or a reliable surprise signal.",
    }


def main() -> None:
    if OUT.exists():
        raise SystemExit("Preserve existing exploration output; create another version")
    for path in (FUTURE / "consumption_receipt.json", FUTURE / "examples/examples.bin", FUTURE / "evaluation/result.json"):
        if path.exists():
            raise SystemExit("Protected V4 artifact exists; refusing opened-data exploration")
    OUT.mkdir(parents=True)
    contract = {
        "role": "opened-development diagnostic and focused exploratory comparison",
        "created_at": datetime.now(timezone.utc).isoformat(), "l2_penalty": PENALTY,
        "strong_baseline": "selected hgb_7_600 market-only predictions",
        "selection_and_fit": "Baseline previously selected on opened fold 4; offsets fit on exposed fold 4 and compared on identical exposed fold 5 rows.",
        "signed_feature_policy": "Deterministic v0.2 extractor; only exact nonzero directions enter features; never emits surprise.",
        "known_limits": ["opened and post-selection", "assistant review is development evidence only",
                         "historical news completeness and source provenance uncertified",
                         "no independent confirmation or selection-adjusted inference"],
        "inputs": [{"path": str(p.relative_to(REPO_ROOT)), "sha256": sha256_file(p)} for p in
                   (DIAGNOSTIC / "priority_diagnostic_cases.jsonl", DIAGNOSTIC / "comparison_cases.jsonl",
                    OOF, EVENTS, BASELINE / "predictions.npz", Path(__file__).parents[1] / "v7/signed_evidence_v02.py")],
    }
    write_json(OUT / "contract.json", contract)
    inspection, inspection_summary = inspect_queue()
    ledger, ledger_summary = event_ledger()
    write_jsonl(OUT / "diagnostic_inspection.jsonl", inspection)
    write_jsonl(OUT / "event_ledger.jsonl", ledger)
    comparison = run_comparison()
    report = {"status": "complete", "diagnostic": inspection_summary,
              "event_ledger": ledger_summary, "comparison": comparison,
              "protected_outcomes_read": False, "forecasting_improvement_claim": False,
              "reliable_surprise_signal_claim": False}
    write_json(OUT / "report.json", report)
    artifacts = [OUT / name for name in ("contract.json", "diagnostic_inspection.jsonl", "event_ledger.jsonl", "report.json", "predictions.npz")]
    artifacts += [Path(__file__), Path(__file__).parents[1] / "v7/signed_evidence_v02.py"]
    write_json(OUT / "manifest.json", {"artifacts": [{"path": str(p.relative_to(REPO_ROOT)), "sha256": sha256_file(p)} for p in artifacts]})
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
