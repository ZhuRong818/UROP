"""Export existing aggregate results for Paper A; never fit or evaluate models."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "eventx/release/paper_a_20261010"
SOURCES = {
    "receipt": "data/v3_1_historical/primary/holdout/holdout_consumption_receipt.json",
    "v3": "data/v3_1_historical/primary/development/selection_result.json",
    "holdout": "data/v3_1_historical/primary/holdout/evaluation_result.json",
    "v4": "data/v4/discovery/models/result.json",
    "v4_protocol": "eventx/release/v4/protocol.json",
    "baseline": "data/v5/no_terminal_baseline_diagnostic_20261009/report.json",
    "offset": "data/v5/opened_news_offset_trial_20261009/report.json",
    "market_screen": "data/v5/market_learner_screen_20261009/report.json",
    "market_contract": "data/v5/market_learner_screen_20261009/contract.json",
    "joined": "data/v5/method_screen_observed_row_join_20261009/report.json",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    # Read consumption evidence before the already published holdout aggregate.
    receipt = json.loads((ROOT / SOURCES["receipt"]).read_text())
    if receipt.get("reruns_permitted") is not False:
        raise RuntimeError("Expected an already consumed, non-rerunnable holdout")
    if OUT.exists():
        raise RuntimeError("Append-only export already exists; create a new version")
    data = {key: json.loads((ROOT / path).read_text()) for key, path in SOURCES.items()}
    if data["holdout"]["news_incremental_model_evaluated_on_holdout"] is not False:
        raise RuntimeError("Historical publication scope differs from expected B0-only result")
    checks = []
    for name in ["market_learner_screen_20261009", "opened_news_offset_trial_20261009"]:
        manifest_path = ROOT / f"data/v5/{name}/manifest.json"
        manifest = json.loads(manifest_path.read_text())
        for item in manifest["artifacts"]:
            if item["path"] in SOURCES.values():
                matches = digest(ROOT / item["path"]) == item["sha256"]
                checks.append({"path": item["path"], "manifest": str(manifest_path.relative_to(ROOT)), "matches": matches})
                if not matches:
                    raise RuntimeError(f"Source manifest mismatch: {item['path']}")
    if data["joined"]["protected_outcomes_read"] or data["joined"]["candidate_promotion"]:
        raise RuntimeError("Expected exploratory, nonpromoted join")

    panels = []

    def panel(name, scope, rows, metrics):
        panels.append({"name": name, "scope": scope, "rows": rows, "metrics": metrics})

    panel("V3.1 development", "prespecified historical development selection", data["v3"]["oof_rows"],
          {k: data["v3"]["aggregate_oof"][k] for k in ["b0", "b1"]})
    panel("V3.1 B0 holdout", "one-shot B0 only; disclosed receipt-order deviation", data["holdout"]["rows"],
          {"b0": data["holdout"]["primary_and_calibration_metrics"]})
    panel("V4 historical discovery", "exploratory; full-discovery semantic fitting", data["v4"]["aggregate_oof"]["b0"]["rows"],
          data["v4"]["aggregate_oof"])
    panel("V5 no-terminal baseline", "opened development; descriptive post-selection diagnostic", data["baseline"]["rows"],
          {k: data["baseline"][k] for k in ["linear_no_terminal", "tree_no_terminal"]})
    panel("V5 fixed-offset corrections", "opened observed-news rows; context/timing/semantic", data["offset"]["validation_rows_observed_news"],
          data["offset"]["metrics"])
    screen = data["market_screen"]["results"]["hgb_7_600"]["folds"]["5"]
    panel("V5 selected market screen, fold 5", "already opened reporting fold; selection used fold 4", screen["metrics"]["rows"],
          {"original_tree": screen["baseline_metrics"], "selected_hgb": screen["metrics"]})
    fold5 = data["joined"]["folds"]["5"]
    panel("V5 matched observed-article subset, fold 5", "exact market/time join; opened and adaptive", fold5["rows"], fold5["metrics"])
    source_records = [{"key": key, "path": path, "sha256": digest(ROOT / path)} for key, path in SOURCES.items()]
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "operation": "aggregate publication export only",
        "source_records": source_records,
        "selected_source_manifest_checks": checks,
        "panels": panels,
        "v3_promotion_gates": data["v3"]["promotion_gates"],
        "v3_brier_interval": data["v3"]["paired_brier_block_bootstrap"],
        "baseline_improvement": data["baseline"]["paired_improvement"],
        "offset_comparisons": data["offset"]["comparisons"],
        "joined_news_vs_market": fold5["selected_news_vs_market_hgb_market_cluster"],
        "v4_status": "pending; no prospective results read or synthesized",
        "new_predictions_fits_bootstrap_or_evaluation": False,
        "raw_labels_predictions_sealed_payloads_read": False,
    }
    OUT.mkdir(parents=True)
    (OUT / "evidence.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    lines = ["# Paper A: aggregate results appendix", "", "Generated from existing aggregate JSON only. Scores are rounded to six decimal places.",
             "Panels describe different samples; comparisons across panels do not estimate a model effect.", ""]
    for p in panels:
        lines += [f"## {p['name']}", "", f"**Evidence status:** {p['scope']}. **Rows:** {p['rows']:,}.", "",
                  "| Model | Log loss | Brier | AP | ROC AUC |", "|---|---:|---:|---:|---:|"]
        for name, metrics in p["metrics"].items():
            scores = [f"{metrics[k]:.6f}" if k in metrics else "—" for k in ["log_loss", "brier", "average_precision", "roc_auc"]]
            lines.append(f"| {name} | " + " | ".join(scores) + " |")
        lines.append("")
    lines += ["## Provenance", "", "Source hashes and full precision are in [evidence.json](evidence.json). Selected report/contract manifest checks are recorded there; this is not certification of every upstream source or payload.", ""]
    (OUT / "TABLES.md").write_text("\n".join(lines))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "none"})
    fig, axes = plt.subplots(1, 3, figsize=(12.8, 5.4))
    groups = [
        ("A. Market model\n364,903 opened rows", ["Logistic", "Boosted tree"],
         [data["baseline"]["linear_no_terminal"]["log_loss"], data["baseline"]["tree_no_terminal"]["log_loss"]]),
        ("B. Fixed-offset trial\n9,965 observed-news rows", ["Market", "Context", "Timing", "Semantic"],
         [data["offset"]["metrics"][k]["log_loss"] for k in ["tree_no_terminal", "context", "timing", "semantic"]]),
        ("C. Matched fold 5\n5,388 observed-article rows", ["Old tree", "New market", "Context", "News timing"],
         [fold5["metrics"][k]["log_loss"] for k in ["frozen_tree", "selected_market_hgb", "selected_context", "selected_news"]]),
    ]
    for ax, (title, labels, values) in zip(axes, groups):
        ax.scatter(range(len(values)), values, color="#225b91", s=45)
        ax.set_xticks(range(len(values)), labels, rotation=25, ha="right")
        for i, value in enumerate(values):
            ax.annotate(f"{value:.6f}", (i, value), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=9)
        spread = max(values) - min(values)
        ax.set_ylim(min(values) - spread * .4, max(values) + spread * .6)
        ax.set_xlim(-.5, len(values) - .5)
        ax.set_title(title, pad=18)
        ax.set_ylabel("Mean log loss (lower is better)")
        ax.grid(axis="y", alpha=.2)
        ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    fig.suptitle("Exploratory comparisons on matched rows within each panel", fontsize=14)
    fig.text(.5, .025, "Different vertical scales and cohorts. Opened data; these point estimates do not establish independent confirmation.", ha="center", fontsize=10)
    fig.subplots_adjust(left=.07, right=.98, top=.77, bottom=.24, wspace=.45)
    for suffix in ["png", "svg", "pdf"]:
        fig.savefig(OUT / f"matched_comparisons.{suffix}", dpi=180)
    plt.close(fig)
    artifacts = [{"path": str(path.relative_to(ROOT)), "sha256": digest(path)} for path in sorted(OUT.iterdir()) if path.is_file()]
    manifest = {"role": "paper evidence export; not research freeze", "sources": source_records, "artifacts": artifacts,
                "exporter": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": digest(Path(__file__))}}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"out": str(OUT.relative_to(ROOT)), "panels": len(panels), "source_files": len(source_records),
                      "manifest_checks": checks, "new_evaluation": False}, indent=2))


if __name__ == "__main__":
    main()
