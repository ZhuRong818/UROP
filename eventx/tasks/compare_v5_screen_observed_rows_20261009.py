"""Join opened market and news screens on exact market-minute validation rows."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from eventx.tasks.audit_v5_algorithms import block_interval
from eventx.tasks.run_v5_residual_feasibility import (
    FUTURE, REPO_ROOT, metric, point_loss, sha256_file, verify_manifest,
)

PARENT = REPO_ROOT / "data/v5/algorithm_audit_20260907"
MARKET = REPO_ROOT / "data/v5/market_learner_screen_20261009"
NEWS = REPO_ROOT / "data/v5/observed_news_method_screen_20261009"
EXPOSURE = REPO_ROOT / "data/v5/opened_news_offset_trial_20261009"
OUT = REPO_ROOT / "data/v5/method_screen_observed_row_join_20261009"


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def main() -> None:
    if OUT.exists():
        raise SystemExit("Preserve existing joined diagnostic; create a new version")
    for path in (FUTURE / "consumption_receipt.json", FUTURE / "examples/examples.bin",
                 FUTURE / "evaluation/result.json"):
        if path.exists():
            raise SystemExit("Protected V4 artifact exists; refusing opened-data join")
    for directory in (PARENT, MARKET, NEWS, EXPOSURE):
        verify_manifest(directory / "manifest.json")
    OUT.mkdir(parents=True)
    source_paths = (PARENT / "predictions.npz", MARKET / "predictions.npz",
                    NEWS / "predictions.npz", NEWS / "report.json",
                    EXPOSURE / "predictions.npz")
    contract = {
        "role": "opened-development exact market-minute cross-screen diagnostic",
        "selection": "uses fold4 selections from existing screens; no new fit or selection",
        "join": "exact (market, minute) keys; market-only keys are invalid because markets repeat across decision times",
        "inputs": [{"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256_file(path)}
                   for path in source_paths],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(OUT / "contract.json", contract)
    with np.load(PARENT / "predictions.npz", allow_pickle=False) as parent, \
         np.load(MARKET / "predictions.npz", allow_pickle=False) as market_scores, \
         np.load(NEWS / "predictions.npz", allow_pickle=False) as news_scores, \
         np.load(EXPOSURE / "predictions.npz", allow_pickle=False) as exposure:
        news_report = json.loads((NEWS / "report.json").read_text())
        context_key = news_report["selected_on_fold4"]["context"]["key"]
        news_key = news_report["selected_on_fold4"]["news"]["key"]
        folds = {}
        for fold in (4, 5):
            all_mask = parent["fold"] == fold
            observed_mask = exposure["fold"] == fold
            observed_keys = list(zip(exposure["market"][observed_mask].tolist(),
                                     exposure["minute"][observed_mask].tolist()))
            if len(set(observed_keys)) != len(observed_keys):
                raise RuntimeError("Duplicate observed market-minute keys")
            key_set = set(observed_keys)
            chosen = np.fromiter(
                ((int(market), int(minute)) in key_set for market, minute in
                 zip(parent["market"][all_mask], parent["minute"][all_mask])),
                dtype=bool, count=int(all_mask.sum()),
            )
            if not np.array_equal(parent["market"][all_mask][chosen],
                                  exposure["market"][observed_mask]) or not np.array_equal(
                                  parent["minute"][all_mask][chosen],
                                  exposure["minute"][observed_mask]):
                raise RuntimeError("Exact market-minute join failed")
            if not np.array_equal(parent["label"][all_mask][chosen],
                                  news_scores[f"label{fold}"]):
                raise RuntimeError("News-screen labels disagree")
            if not np.array_equal(parent["market"][all_mask][chosen],
                                  news_scores[f"market{fold}"]):
                raise RuntimeError("News-screen market order disagrees")
            y = parent["label"][all_mask][chosen]
            old = parent["tree_no_terminal"][all_mask][chosen]
            stronger = market_scores[f"hgb_7_600__fold{fold}"][chosen]
            context = news_scores[f"{context_key}__fold{fold}"]
            news = news_scores[f"{news_key}__fold{fold}"]
            folds[str(fold)] = {
                "rows": len(y),
                "markets": int(np.unique(parent["market"][all_mask][chosen]).size),
                "metrics": {"frozen_tree": metric(y, old), "selected_market_hgb": metric(y, stronger),
                            "selected_context": metric(y, context), "selected_news": metric(y, news)},
                "log_loss_improvements": {
                    "market_hgb_vs_frozen_tree": float(point_loss(y, old).mean()-point_loss(y, stronger).mean()),
                    "selected_news_vs_market_hgb": float(point_loss(y, stronger).mean()-point_loss(y, news).mean()),
                    "selected_news_vs_selected_context": float(point_loss(y, context).mean()-point_loss(y, news).mean()),
                },
            }
            if fold == 5:
                folds[str(fold)]["selected_news_vs_market_hgb_market_cluster"] = block_interval(
                    {"market": parent["market"][all_mask][chosen]},
                    point_loss(y, stronger)-point_loss(y, news))
    report = {"status": "complete", "fold4_selected_context": context_key,
              "fold4_selected_news": news_key, "folds": folds,
              "protected_outcomes_read": False, "new_fit": False,
              "candidate_promotion": False}
    write_json(OUT / "report.json", report)
    artifacts = [OUT / "contract.json", OUT / "report.json", Path(__file__)]
    write_json(OUT / "manifest.json", {"artifacts": [
        {"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256_file(path)} for path in artifacts
    ]})
    print(json.dumps({"status": "complete", "folds": {key: {
        "rows": value["rows"], "log_loss_improvements": value["log_loss_improvements"]
    } for key, value in folds.items()}}, indent=2))


if __name__ == "__main__":
    main()
