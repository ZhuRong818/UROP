"""Run historical, exploratory EventX v4 novelty and diffusion analyses.

This task uses only the already-opened discovery interval. It never reads the future
v4 confirmatory collection and cannot modify the frozen protocol or model bundle.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterator

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from eventx.settings import REPO_ROOT
from eventx.tasks.build_v4_discovery_examples import EXAMPLE_DTYPE, FEATURE_NAMES
from eventx.tasks.evaluate_v4_confirmatory import two_level_bootstrap
from eventx.tasks.prepare_v3_1_historical_development_arrays import sha256_file
from eventx.tasks.prepare_v4_discovery_news_quality import EVENT_DTYPE
from eventx.tasks.run_v4_discovery_models import FOLDS, OOF_DTYPE


EXAMPLES = REPO_ROOT / "data/v4/discovery/examples/examples.bin"
EXAMPLES_MANIFEST = REPO_ROOT / "data/v4/discovery/examples/manifest.json"
OOF = REPO_ROOT / "data/v4/discovery/models/oof_predictions.bin"
MODEL_MANIFEST = REPO_ROOT / "data/v4/discovery/models/manifest.json"
EVENTS = REPO_ROOT / "data/v4/discovery/prepared/news_quality_events.bin"
MARKETS = REPO_ROOT / "data/v3_1_historical/primary/development/prepared/market_index.jsonl"
CONFIRMATORY_ROOT = REPO_ROOT / "data/v4/confirmatory"
OUTPUT = REPO_ROOT / "data/v4/exploratory/novelty_diffusion"
REPORT = OUTPUT / "report.json"
NESTED_CSV = OUTPUT / "nested_comparisons.csv"
GROUP_CSV = OUTPUT / "exposure_groups.csv"
CATEGORY_CSV = OUTPUT / "category_results.csv"
NESTED_FIGURE = OUTPUT / "nested_logloss_contributions.svg"
NOVELTY_FIGURE = OUTPUT / "novelty_quantiles.svg"
SUMMARY = OUTPUT / "SUMMARY.md"
MANIFEST = OUTPUT / "manifest.json"
BOOTSTRAP_SAMPLES = 2000
BOOTSTRAP_SEED = 611


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def atomic_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot write empty table: {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def verify_manifest(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for artifact in manifest.get("artifacts", []):
        target = REPO_ROOT / str(artifact["path"])
        if not target.is_file() or sha256_file(target) != str(artifact["sha256"]):
            raise RuntimeError(f"hash-lock failure: {target}")


def loss(labels: np.ndarray, scores: np.ndarray) -> np.ndarray:
    labels = np.asarray(labels, dtype=np.float64)
    scores = np.clip(np.asarray(scores, dtype=np.float64), 1e-7, 1.0 - 1e-7)
    return -labels * np.log(scores) - (1.0 - labels) * np.log(1.0 - scores)


def comparison(labels: np.ndarray, baseline: np.ndarray, candidate: np.ndarray) -> dict[str, Any]:
    labels = np.asarray(labels, dtype=np.uint8)
    baseline = np.asarray(baseline, dtype=np.float64)
    candidate = np.asarray(candidate, dtype=np.float64)
    positives = int(labels.sum())
    both = len(np.unique(labels)) == 2
    return {
        "rows": len(labels),
        "positives": positives,
        "prevalence": float(labels.mean()),
        "log_loss_improvement": float(np.mean(loss(labels, baseline) - loss(labels, candidate))),
        "brier_improvement": float(np.mean(np.square(labels - baseline) - np.square(labels - candidate))),
        "delta_average_precision": (
            float(average_precision_score(labels, candidate) - average_precision_score(labels, baseline))
            if positives else None
        ),
        "delta_roc_auc": (
            float(roc_auc_score(labels, candidate) - roc_auc_score(labels, baseline))
            if both else None
        ),
    }


def reconstruct_oof_indices(examples: np.ndarray, oof: np.ndarray) -> np.ndarray:
    selected = []
    for fold, held_group, validation_start, validation_end in FOLDS:
        indices = np.flatnonzero(
            (examples["minute"] >= validation_start)
            & (examples["minute"] < validation_end)
            & (examples["group"] == held_group)
        )
        fold_rows = oof[oof["fold"] == fold]
        if len(indices) != len(fold_rows):
            raise RuntimeError(f"fold {fold} discovery feature/OOF row count mismatch")
        if not np.array_equal(examples["market"][indices], fold_rows["market"]):
            raise RuntimeError(f"fold {fold} market alignment mismatch")
        if not np.array_equal(examples["minute"][indices], fold_rows["minute"]):
            raise RuntimeError(f"fold {fold} time alignment mismatch")
        if not np.array_equal(examples["label"][indices], fold_rows["label"]):
            raise RuntimeError(f"fold {fold} label alignment mismatch")
        selected.append(indices)
    return np.concatenate(selected)


def subset_record(
    name: str,
    mask: np.ndarray,
    labels: np.ndarray,
    oof: np.ndarray,
    novelty_ratio: np.ndarray,
    features: np.ndarray,
) -> dict[str, Any]:
    if not np.any(mask):
        return {"group": name, "rows": 0}
    values = {
        "group": name,
        "rows": int(mask.sum()),
        "markets": int(len(np.unique(oof["market"][mask]))),
        "positives": int(labels[mask].sum()),
        "prevalence": float(labels[mask].mean()),
        "mean_relevance_mass_1440m": float(features[mask, 18].mean()),
        "mean_novelty_ratio_1440m": float(novelty_ratio[mask].mean()),
        "mean_distinct_publishers_1440m": float(features[mask, 24].mean()),
        "mean_cross_publisher_reports_1440m": float(features[mask, 27].mean()),
        "mean_prediction_b0": float(np.mean(oof["b0"][mask])),
        "mean_prediction_b1": float(np.mean(oof["b1"][mask])),
        "mean_prediction_b2": float(np.mean(oof["b2"][mask])),
        "mean_prediction_b3": float(np.mean(oof["b3"][mask])),
    }
    for label, baseline, candidate in (
        ("b2_vs_b1", "b1", "b2"),
        ("b3_vs_b2", "b2", "b3"),
        ("b3_vs_b0", "b0", "b3"),
    ):
        result = comparison(labels[mask], oof[baseline][mask], oof[candidate][mask])
        values[f"{label}_log_loss_improvement"] = result["log_loss_improvement"]
        values[f"{label}_brier_improvement"] = result["brier_improvement"]
    return values


def svg_bar(path: Path, labels: list[str], values: list[float], title: str, y_label: str) -> None:
    width, height = 920, 560
    left, right, top, bottom = 110, 40, 80, 110
    plot_w, plot_h = width - left - right, height - top - bottom
    low = min(0.0, min(values))
    high = max(0.0, max(values))
    pad = max((high - low) * 0.15, 0.0002)
    low, high = low - pad, high + pad
    y = lambda value: top + (high - value) / (high - low) * plot_h
    zero = y(0.0)
    bar_w = plot_w / len(values) * 0.55
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="35" text-anchor="middle" font-family="Arial" font-size="24" font-weight="bold">{title}</text>',
        f'<line x1="{left}" y1="{zero:.2f}" x2="{width-right}" y2="{zero:.2f}" stroke="#222" stroke-width="1.5"/>',
        f'<text x="24" y="{height/2}" transform="rotate(-90 24 {height/2})" text-anchor="middle" font-family="Arial" font-size="15">{y_label}</text>',
    ]
    for index, (label, value) in enumerate(zip(labels, values)):
        center = left + (index + 0.5) * plot_w / len(values)
        value_y = y(value)
        rect_y, rect_h = min(zero, value_y), abs(zero - value_y)
        color = "#2c7fb8" if value >= 0 else "#d95f0e"
        elements.extend([
            f'<rect x="{center-bar_w/2:.2f}" y="{rect_y:.2f}" width="{bar_w:.2f}" height="{max(rect_h, 1):.2f}" fill="{color}"/>',
            f'<text x="{center:.2f}" y="{height-bottom+32}" text-anchor="middle" font-family="Arial" font-size="15">{label}</text>',
            f'<text x="{center:.2f}" y="{value_y + (-10 if value >= 0 else 22):.2f}" text-anchor="middle" font-family="Arial" font-size="14">{value:.6f}</text>',
        ])
    elements.append(f'<text x="{width/2}" y="{height-24}" text-anchor="middle" font-family="Arial" font-size="12" fill="#555">Positive values favour the added feature family; historical exploratory analysis.</text>')
    elements.append("</svg>")
    path.write_text("\n".join(elements) + "\n", encoding="utf-8")


def main() -> None:
    if any(path.exists() for path in (REPORT, NESTED_CSV, GROUP_CSV, CATEGORY_CSV, NESTED_FIGURE, NOVELTY_FIGURE, SUMMARY, MANIFEST)):
        raise SystemExit("v4 exploratory novelty/diffusion artifacts already exist")
    forbidden = (
        CONFIRMATORY_ROOT / "consumption_receipt.json",
        CONFIRMATORY_ROOT / "examples/examples.bin",
        CONFIRMATORY_ROOT / "evaluation/result.json",
    )
    if any(path.exists() for path in forbidden):
        raise SystemExit("exploratory analysis refused after future holdout consumption")
    verify_manifest(EXAMPLES_MANIFEST)
    verify_manifest(MODEL_MANIFEST)
    example_count = EXAMPLES.stat().st_size // EXAMPLE_DTYPE.itemsize
    oof_count = OOF.stat().st_size // OOF_DTYPE.itemsize
    event_count = EVENTS.stat().st_size // EVENT_DTYPE.itemsize
    examples = np.memmap(EXAMPLES, mode="r", dtype=EXAMPLE_DTYPE, shape=(example_count,))
    oof = np.memmap(OOF, mode="r", dtype=OOF_DTYPE, shape=(oof_count,))
    events = np.memmap(EVENTS, mode="r", dtype=EVENT_DTYPE, shape=(event_count,))
    indices = reconstruct_oof_indices(examples, oof)
    features = np.asarray(examples["features"][indices], dtype=np.float32)
    labels = np.asarray(oof["label"], dtype=np.uint8)
    if list(FEATURE_NAMES[16:]) != [
        "news_relevance_mass_60m", "news_relevance_mass_360m", "news_relevance_mass_1440m",
        "news_novel_relevance_mass_60m", "news_novel_relevance_mass_360m", "news_novel_relevance_mass_1440m",
        "news_distinct_publishers_60m", "news_distinct_publishers_360m", "news_distinct_publishers_1440m",
        "news_cross_publisher_reports_60m", "news_cross_publisher_reports_360m", "news_cross_publisher_reports_1440m",
    ]:
        raise RuntimeError("unexpected v4 quality-feature order")

    nested_specs = (
        ("news_volume_B1_minus_B0", "b0", "b1"),
        ("relevance_novelty_B2_minus_B1", "b1", "b2"),
        ("publisher_diffusion_B3_minus_B2", "b2", "b3"),
        ("all_news_B3_minus_B0", "b0", "b3"),
    )
    nested_rows = []
    bootstraps = {}
    for offset, (name, baseline, candidate) in enumerate(nested_specs):
        row = {"contrast": name, "baseline": baseline, "candidate": candidate, **comparison(labels, oof[baseline], oof[candidate])}
        nested_rows.append(row)
        improvement = loss(labels, oof[baseline]) - loss(labels, oof[candidate])
        bootstrap = two_level_bootstrap(
            np.asarray(oof["market"]),
            np.asarray(oof["minute"]),
            improvement,
            samples=BOOTSTRAP_SAMPLES,
            seed=BOOTSTRAP_SEED + offset,
        )
        bootstrap["estimand"] = f"mean per-row log-loss improvement {baseline.upper()} minus {candidate.upper()}"
        bootstraps[name] = bootstrap

    relevance = np.asarray(features[:, 18], dtype=np.float64)
    novel_relevance = np.asarray(features[:, 21], dtype=np.float64)
    novelty_ratio = np.divide(novel_relevance, relevance, out=np.zeros_like(relevance), where=relevance > 0)
    any_news = features[:, 14] > 0
    relevance_exposed = relevance > 0
    diffusion_exposed = features[:, 27] > 0
    group_rows = [
        subset_record("no_associated_news_1440m", ~any_news, labels, oof, novelty_ratio, features),
        subset_record("associated_news_1440m", any_news, labels, oof, novelty_ratio, features),
        subset_record("relevance_exposed_1440m", relevance_exposed, labels, oof, novelty_ratio, features),
        subset_record("no_cross_publisher_diffusion_1440m", ~diffusion_exposed, labels, oof, novelty_ratio, features),
        subset_record("cross_publisher_diffusion_1440m", diffusion_exposed, labels, oof, novelty_ratio, features),
    ]
    exposed_values = novelty_ratio[relevance_exposed]
    edges = np.quantile(exposed_values, (0.0, 0.25, 0.5, 0.75, 1.0)) if len(exposed_values) else np.zeros(5)
    novelty_rows = []
    if len(exposed_values):
        bins = np.searchsorted(edges[1:-1], novelty_ratio, side="right")
        for number in range(4):
            mask = relevance_exposed & (bins == number)
            record = subset_record(f"novelty_q{number + 1}", mask, labels, oof, novelty_ratio, features)
            record["lower_edge"] = float(edges[number])
            record["upper_edge"] = float(edges[number + 1])
            novelty_rows.append(record)
    group_rows.extend(novelty_rows)

    markets = list(read_jsonl(MARKETS))
    category_by_market = np.asarray([str(row["category"]) for row in markets], dtype=object)
    venue_by_market = np.asarray([str(row["venue"]) for row in markets], dtype=object)
    row_categories = category_by_market[np.asarray(oof["market"], dtype=np.int64)]
    row_venues = venue_by_market[np.asarray(oof["market"], dtype=np.int64)]
    category_rows = []
    for dimension, values in (("category", row_categories), ("venue", row_venues)):
        for value in sorted(set(values.tolist())):
            mask = values == value
            record = subset_record(f"{dimension}:{value}", mask, labels, oof, novelty_ratio, features)
            record = {"dimension": dimension, "value": value, **{key: val for key, val in record.items() if key != "group"}}
            record["news_exposure_rate_1440m"] = float(any_news[mask].mean())
            record["diffusion_exposure_rate_1440m"] = float(diffusion_exposed[mask].mean())
            category_rows.append(record)

    event_novelty = np.asarray(events["novelty"], dtype=np.float64)
    event_relevance = np.asarray(events["relevance"], dtype=np.float64)
    event_summary = {
        "events": len(events),
        "markets": int(len(np.unique(events["market"]))),
        "relevance_quantiles": {str(q): float(np.quantile(event_relevance, q)) for q in (0, 0.1, 0.25, 0.5, 0.75, 0.9, 1)},
        "novelty_quantiles": {str(q): float(np.quantile(event_novelty, q)) for q in (0, 0.1, 0.25, 0.5, 0.75, 0.9, 1)},
        "cross_publisher_events": int(np.sum(events["diffusion_publishers"] >= 2)),
        "cross_publisher_event_share": float(np.mean(events["diffusion_publishers"] >= 2)),
        "true_social_virality_fields_available": False,
    }

    OUTPUT.mkdir(parents=True, exist_ok=True)
    atomic_csv(NESTED_CSV, nested_rows)
    atomic_csv(GROUP_CSV, group_rows)
    atomic_csv(CATEGORY_CSV, category_rows)
    svg_bar(
        NESTED_FIGURE,
        ["Volume", "Relevance + novelty", "Publisher diffusion"],
        [float(row["log_loss_improvement"]) for row in nested_rows[:3]],
        "Historical incremental contribution of news feature families",
        "Mean log-loss improvement (nats/row)",
    )
    svg_bar(
        NOVELTY_FIGURE,
        [f"Q{number + 1}" for number in range(len(novelty_rows))],
        [float(row["b2_vs_b1_log_loss_improvement"]) for row in novelty_rows],
        "Relevance/novelty contribution by novelty exposure quartile",
        "B1 minus B2 log-loss (nats/row)",
    )
    novelty_contrast = nested_rows[1]
    diffusion_contrast = nested_rows[2]
    diffusion_group = next(row for row in group_rows if row["group"] == "cross_publisher_diffusion_1440m")
    SUMMARY.write_text(
        "# EventX v4 historical novelty and diffusion analysis\n\n"
        "Status: **exploratory, completed on previously opened discovery data**. "
        "The untouched future confirmatory holdout was not read.\n\n"
        "## Main findings\n\n"
        f"- Adding relevance and market-relative novelty (B2 versus B1) changed log "
        f"loss by `{novelty_contrast['log_loss_improvement']:.6f}` nats/row. Its "
        f"paired 95% interval was "
        f"`[{bootstraps['relevance_novelty_B2_minus_B1']['ci_95_lower']:.6f}, "
        f"{bootstraps['relevance_novelty_B2_minus_B1']['ci_95_upper']:.6f}]`; this is "
        "compatible with no improvement.\n"
        f"- Adding publisher diversity and cross-publisher diffusion (B3 versus B2) "
        f"changed log loss by `{diffusion_contrast['log_loss_improvement']:.6f}` "
        f"nats/row. Its paired 95% interval was "
        f"`[{bootstraps['publisher_diffusion_B3_minus_B2']['ci_95_lower']:.6f}, "
        f"{bootstraps['publisher_diffusion_B3_minus_B2']['ci_95_upper']:.6f}]`; the "
        "extension was worse.\n"
        f"- Cross-publisher diffusion was present on {diffusion_group['rows']:,} OOF "
        f"rows across {diffusion_group['markets']:,} markets. On these exposed rows, "
        f"B3-versus-B2 log-loss improvement was "
        f"`{diffusion_group['b3_vs_b2_log_loss_improvement']:.6f}`.\n"
        f"- At event level, {event_summary['cross_publisher_events']:,} of "
        f"{event_summary['events']:,} associations "
        f"({100 * event_summary['cross_publisher_event_share']:.2f}%) met the frozen "
        "cross-publisher diffusion definition.\n\n"
        "## Interpretation boundary\n\n"
        "These results concern market-relative semantic novelty and exact-headline "
        "cross-publisher diffusion. They do not measure social virality: Lumid has no "
        "views, shares, reposts, likes, comments, or propagation-network fields in the "
        "validated source. The analysis is post-freeze and exploratory; it cannot "
        "change or rescue the preregistered future v4 confirmation.\n",
        encoding="utf-8",
    )
    report = {
        "protocol_id": "eventx-v4-post-freeze-historical-exploratory-novelty-diffusion-20260903",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "complete",
        "role": "post-freeze exploratory analysis of already-opened historical discovery data",
        "future_confirmatory_data_read": False,
        "changes_to_frozen_v4_protocol_models_or_decision_rule": False,
        "terminology": {
            "novelty": "market-relative semantic novelty in frozen discovery LSA space",
            "diffusion": "exact-headline cross-publisher diffusion",
            "true_social_virality": "unsupported because views, shares, reposts, likes and comments are unavailable",
        },
        "oof_rows": len(oof),
        "oof_markets": int(len(np.unique(oof["market"]))),
        "nested_comparisons": nested_rows,
        "paired_bootstraps": bootstraps,
        "exposure_groups": group_rows,
        "category_and_venue_results": category_rows,
        "event_level_summary": event_summary,
        "artifacts": [relative(path) for path in (NESTED_CSV, GROUP_CSV, CATEGORY_CSV, NESTED_FIGURE, NOVELTY_FIGURE, SUMMARY)],
        "interpretation_policy": "Exploratory associations cannot alter or rescue the frozen future confirmatory result.",
    }
    atomic_json(REPORT, report)
    atomic_json(MANIFEST, {
        "protocol_id": report["protocol_id"],
        "status": report["status"],
        "artifacts": [{"path": relative(path), "sha256": sha256_file(path)} for path in (REPORT, NESTED_CSV, GROUP_CSV, CATEGORY_CSV, NESTED_FIGURE, NOVELTY_FIGURE, SUMMARY, Path(__file__).resolve())],
        "inputs": [{"path": relative(path), "sha256": sha256_file(path)} for path in (EXAMPLES, EXAMPLES_MANIFEST, OOF, MODEL_MANIFEST, EVENTS, MARKETS)],
    })
    print(json.dumps({
        "status": report["status"],
        "future_confirmatory_data_read": False,
        "nested_comparisons": nested_rows,
        "event_level_summary": event_summary,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
