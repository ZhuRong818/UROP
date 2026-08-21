"""Build an unlabeled-to-reviewer OOT holdout for the frozen EventX cohort.

The artifact contains labels for the guarded evaluator, but this builder never
summarizes, prints, or branches on their values.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from eventx.settings import REPO_ROOT
from eventx.tasks.fetch_oot_holdout import DEFAULT_EXTRACT
from eventx.tasks.freeze_toy import hash_file
from eventx.tasks.toy_slice import (
    label_bars,
    minute_bars,
    parse_ts,
    read_jsonl,
    trade_fields,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the EventX OOT holdout")
    parser.add_argument("--extract", default=DEFAULT_EXTRACT)
    parser.add_argument("--horizon-min", type=int, default=30)
    parser.add_argument("--selected-markets", type=Path)
    args = parser.parse_args()
    root = REPO_ROOT / "data" / args.extract
    fetch_path = root / "fetch_manifest.json"
    trades_path = root / "raw" / "trades_polymarket.jsonl"
    selected_path = (
        args.selected_markets
        or REPO_ROOT / "data" / "v1" / "toy" / "selected_markets.jsonl"
    )
    if not fetch_path.exists() or not trades_path.exists():
        raise SystemExit("Fresh OOT trade snapshot is missing.")
    fetch = json.loads(fetch_path.read_text())
    if hash_file(trades_path)["sha256"] != fetch["artifact"]["sha256"]:
        raise SystemExit("Fresh trade snapshot hash mismatch.")
    selected_rows = list(read_jsonl(selected_path))
    selected = {
        (str(row["market_id"]), str(row["outcome_id"])): row
        for row in selected_rows
    }
    if len(selected) != 20:
        raise SystemExit(f"Expected 20 frozen outcomes, found {len(selected)}.")

    grouped: dict[tuple[str, str], list[tuple[Any, float, float]]] = defaultdict(list)
    for row in read_jsonl(trades_path):
        fields = trade_fields(row, "polymarket")
        if fields is None:
            continue
        timestamp, price, size, outcome_id = fields
        key = (str(row["market_id"]), outcome_id)
        if key in selected:
            grouped[key].append((timestamp, price, size))

    holdout_start = parse_ts(fetch["window"]["holdout_start"])
    holdout_end = parse_ts(fetch["window"]["end"])
    output_dir = root / "holdout"
    bars_path = output_dir / "bars_with_warmup.jsonl"
    labels_path = output_dir / f"labels_{args.horizon_min}m.jsonl"
    manifest_path = output_dir / "build_manifest.json"
    if any(path.exists() for path in (bars_path, labels_path, manifest_path)):
        raise SystemExit(f"Refusing to replace existing holdout under {output_dir}.")
    output_dir.mkdir(parents=True, exist_ok=True)
    bars_tmp = bars_path.with_suffix(".jsonl.tmp")
    labels_tmp = labels_path.with_suffix(".jsonl.tmp")
    total_bars = 0
    total_rows = 0
    eligible_rows = 0
    markets_with_rows: set[str] = set()
    markets_with_eligible_rows: set[str] = set()
    duplicate_keys: set[tuple[str, str, str]] = set()
    seen_keys: set[tuple[str, str, str]] = set()
    market_coverage = []
    with bars_tmp.open("w") as bars_handle, labels_tmp.open("w") as labels_handle:
        for key, metadata in selected.items():
            market_bars = minute_bars(
                "polymarket",
                key[0],
                key[1],
                grouped.get(key, []),
            )
            all_labels = label_bars(
                market_bars,
                args.horizon_min,
                k_sigma=4.0,
                vol_window=240,
                min_trades=3,
                min_notional=100.0,
                market=metadata,
                validation_boundary=holdout_start,
                test_boundary=holdout_start,
            )
            holdout_rows = [
                row
                for row in all_labels
                if row["split"] == "test"
                and holdout_start <= parse_ts(row["ts"]) <= holdout_end
            ]
            for bar in market_bars:
                bars_handle.write(json.dumps(bar, sort_keys=True) + "\n")
            for row in holdout_rows:
                output_key = (
                    str(row["market_id"]),
                    str(row["outcome_id"]),
                    str(row["ts"]),
                )
                if output_key in seen_keys:
                    duplicate_keys.add(output_key)
                seen_keys.add(output_key)
                labels_handle.write(json.dumps(row, sort_keys=True) + "\n")
                if int(row["eligible"]):
                    eligible_rows += 1
                    markets_with_eligible_rows.add(key[0])
            if holdout_rows:
                markets_with_rows.add(key[0])
            total_bars += len(market_bars)
            total_rows += len(holdout_rows)
            market_coverage.append(
                {
                    "market_id": key[0],
                    "question": metadata["question"],
                    "canonical_trade_rows": len(grouped.get(key, [])),
                    "bars_with_warmup": len(market_bars),
                    "holdout_rows": len(holdout_rows),
                    "eligible_holdout_rows": sum(
                        int(row["eligible"]) for row in holdout_rows
                    ),
                    "first_holdout_ts": (
                        holdout_rows[0]["ts"] if holdout_rows else None
                    ),
                    "last_holdout_ts": (
                        holdout_rows[-1]["ts"] if holdout_rows else None
                    ),
                }
            )
    bars_tmp.replace(bars_path)
    labels_tmp.replace(labels_path)
    if duplicate_keys:
        raise SystemExit(f"Duplicate OOT label keys found: {len(duplicate_keys)}.")
    if not eligible_rows:
        raise SystemExit("OOT holdout has no eligible rows.")
    manifest = {
        "status": "oot_holdout_built_labels_uninspected",
        "extract_version": args.extract,
        "dataset_role": "new_out_of_time_confirmatory_holdout",
        "venue": "polymarket",
        "cohort": {
            "path": str(selected_path.resolve().relative_to(REPO_ROOT)),
            "sha256": hash_file(selected_path)["sha256"],
            "outcomes": len(selected),
            "selection_basis": "frozen_before_holdout",
        },
        "window": fetch["window"],
        "label_contract": {
            "horizon_min": args.horizon_min,
            "k_sigma": 4.0,
            "vol_window_bars": 240,
            "min_trades": 3,
            "min_notional": 100.0,
            "feature_information_cutoff": "at_or_before_t",
            "forward_label_only": "t_plus_30m_price",
        },
        "coverage": {
            "bars_with_warmup": total_bars,
            "holdout_rows": total_rows,
            "eligible_holdout_rows": eligible_rows,
            "markets_with_rows": len(markets_with_rows),
            "markets_with_eligible_rows": len(markets_with_eligible_rows),
            "duplicate_output_keys": len(duplicate_keys),
            "market_details": market_coverage,
        },
        "artifacts": {
            "bars_with_warmup": {
                "path": str(bars_path.resolve().relative_to(REPO_ROOT)),
                **hash_file(bars_path),
            },
            "labels": {
                "path": str(labels_path.resolve().relative_to(REPO_ROOT)),
                **hash_file(labels_path),
            },
            "fresh_trades": fetch["artifact"],
        },
        "label_seal": {
            "status": "values_not_summarized_or_inspected",
            "prohibited_before_one_shot_evaluation": [
                "positive count",
                "prevalence",
                "average precision",
                "brier score",
                "candidate comparison",
            ],
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "window": manifest["window"],
                "coverage": manifest["coverage"],
                "artifacts": manifest["artifacts"],
                "label_seal": manifest["label_seal"],
                "manifest": str(manifest_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
