"""Bounded, label-blind V6 source-run and nominal opening-clock probe."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import httpx

from eventx.settings import ApiSettings, REPO_ROOT


OUT = REPO_ROOT / "data/v6/scoped_source_evidence_20260927"
INPUTS = [
    "data/v6/source_role_diagnostic_20260926/typed_pairs.jsonl",
    "data/v6/context_development_review_20260927/provider_scope.json",
    "data/v3_historical/primary/label_blind_inputs/news.jsonl",
    "data/v5/provenance_recovery_20260908/v6_queue_polymarket_00_20260921.jsonl",
    "data/v5/provenance_recovery_20260908/v6_queue_kalshi_01_20260921.jsonl",
    "data/v5/topic_coverage_triage_20260914/news_run_inventory.jsonl",
    "eventx/tasks/probe_v6_scoped_source_evidence_20260927.py",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def rows(path: Path):
    with path.open() as stream:
        for line in stream:
            yield json.loads(line)


def clock(value: str | None):
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def prepare():
    if OUT.exists():
        raise FileExistsError(OUT)
    spec = {
        "version": "v6-scoped-source-evidence-v0.1-20260927",
        "scope": "nine fixed opened-development articles, 15 markets, and the existing 54 heuristic union pairs",
        "source_requests": "one authenticated GET /catalog/lineage/run/{run_id} per distinct fixed article run; no article/market/outcome fetch",
        "clock_comparison": "published_at and available_at against recovered start and end; Polymarket dates remain nominal",
        "interpretation": "diagnostic only; lineage summary is not a complete-feed receipt and no pair becomes admissible",
        "protected_access": False,
    }
    OUT.mkdir(parents=True)
    dump(OUT / "spec.json", spec)
    dump(OUT / "receipt.json", {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "written_before_requests_or_analysis": True,
        "spec_sha256": sha(OUT / "spec.json"),
        "inputs": {name: sha(REPO_ROOT / name) for name in INPUTS},
    })


def run():
    receipt = json.loads((OUT / "receipt.json").read_text())
    if {name: sha(REPO_ROOT / name) for name in INPUTS} != receipt["inputs"]:
        raise ValueError("input hash changed")
    if sha(OUT / "spec.json") != receipt["spec_sha256"]:
        raise ValueError("spec hash changed")
    if (OUT / "report.json").exists():
        raise FileExistsError("report already exists")

    scope = json.loads((REPO_ROOT / INPUTS[1]).read_text())
    article_ids = {str(a["article_id"]) for a in scope["articles"]}
    contract_ids = {c["contract_id"] for c in scope["contracts"]}
    articles = {}
    local_run_counts = Counter()
    for row in rows(REPO_ROOT / INPUTS[2]):
        if str(row["id"]) in article_ids:
            articles[str(row["id"])] = row
        if row.get("source_run_id") in {a["source_run_id"] for a in scope["articles"]}:
            local_run_counts[row["source_run_id"]] += 1
    if set(articles) != article_ids:
        raise ValueError("missing scoped article")

    markets = {}
    for name in INPUTS[3:5]:
        for row in rows(REPO_ROOT / name):
            cid = ("polymarket:contract:" + row["condition_id"] if "condition_id" in row
                   else "kalshi:contract:" + row["ticker"])
            if cid in contract_ids:
                if cid in markets:
                    raise ValueError("duplicate market")
                markets[cid] = row
    if set(markets) != contract_ids:
        raise ValueError(f"missing scoped markets: {sorted(contract_ids - set(markets))}")

    pairs = [r for r in rows(REPO_ROOT / INPUTS[0])
             if r["old_status"] != "abstain" or r["new_status"] != "abstain"]
    if len(pairs) != 54:
        raise ValueError(f"unexpected pair count {len(pairs)}")
    pair_results = []
    for pair in pairs:
        article = articles[pair["article_id"]]
        market = markets[pair["contract_id"]]
        available, published = clock(article["available_at"]), clock(article["published_at"])
        start = clock(market.get("open_time") or market.get("start_date"))
        end = clock(market.get("close_time") or market.get("end_date"))
        if available != clock(pair["article_clock"]):
            raise ValueError("article clock mismatch")
        pair_results.append({
            "article_id": pair["article_id"], "contract_id": pair["contract_id"],
            "venue": pair["venue"], "provisional_group": pair["provisional_group"],
            "run_status": pair["article_source_run_status"],
            "published_at": article["published_at"], "available_at": article["available_at"],
            "start_field": "open_time" if pair["venue"] == "kalshi" else "start_date",
            "start": start.isoformat() if start else None,
            "end_field": "close_time" if pair["venue"] == "kalshi" else "end_date",
            "end": end.isoformat() if end else None,
            "publication_within_nominal_bounds": bool(start and end and start <= published < end),
            "availability_within_nominal_bounds": bool(start and end and start <= available < end),
            "availability_before_start": bool(start and available < start),
            "availability_at_or_after_end": bool(end and available >= end),
            "published_before_available": published < available,
            "publication_to_availability_minutes": round((available - published).total_seconds() / 60, 3),
            "old_status": pair["old_status"], "new_status": pair["new_status"],
            "training_admissible": False,
        })
    with (OUT / "pair_clocks.jsonl").open("w") as stream:
        for row in pair_results:
            stream.write(json.dumps(row, sort_keys=True) + "\n")

    settings = ApiSettings.from_env()
    run_records = []
    with httpx.Client(base_url=settings.base_url, timeout=30, follow_redirects=False,
                      headers={"Authorization": f"Bearer {settings.token}"}) as client:
        for article in scope["articles"]:
            rid = article["source_run_id"]
            rec = {"run_id": rid, "article_id": article["article_id"],
                   "cached_status": article["source_run_status"],
                   "local_export_rows_for_run": local_run_counts[rid],
                   "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}
            try:
                response = client.get(f"/catalog/lineage/run/{rid}")
                rec["http_status"] = response.status_code
                if response.status_code == 200:
                    data = response.json()
                    if data.get("run_id") != rid:
                        raise ValueError("lineage run ID mismatch")
                    allowed = ("run_id", "endpoint_id", "started_at", "ended_at", "status",
                               "rows_inserted", "rows_updated", "rows_failed", "response_schema_hash")
                    rec["lineage"] = {key: data.get(key) for key in allowed}
                    rec["lineage"]["args"] = {k: v for k, v in (data.get("args") or {}).items()
                                                if k in {"from", "to", "n_symbols", "category", "window_days"}}
                    error = str(data.get("error_text") or "")
                    rec["lineage"]["error_category"] = (
                        "abandoned_run_cleanup" if "abandoned" in error.lower()
                        else "other_error_present" if error else "empty")
                    rec["write_counters_complete"] = all(
                        data.get(key) is not None for key in ("rows_inserted", "rows_updated", "rows_failed"))
                rec["full_window_certified"] = False
            except (httpx.HTTPError, ValueError, TypeError) as error:
                rec["error_type"] = type(error).__name__
                rec["full_window_certified"] = False
            run_records.append(rec)
            print(json.dumps({"run": len(run_records), "total": len(scope["articles"]),
                              "http_status": rec.get("http_status"), "error_type": rec.get("error_type")}), flush=True)
    with (OUT / "lineage.jsonl").open("w") as stream:
        for row in run_records:
            stream.write(json.dumps(row, sort_keys=True) + "\n")

    report = {
        "scope_articles": len(article_ids), "scope_contracts": len(contract_ids),
        "heuristic_union_pairs": len(pair_results),
        "pairs_publication_within_nominal_bounds": sum(r["publication_within_nominal_bounds"] for r in pair_results),
        "pairs_availability_within_nominal_bounds": sum(r["availability_within_nominal_bounds"] for r in pair_results),
        "pairs_availability_before_start": sum(r["availability_before_start"] for r in pair_results),
        "pairs_availability_at_or_after_end": sum(r["availability_at_or_after_end"] for r in pair_results),
        "pairs_published_before_available": sum(r["published_before_available"] for r in pair_results),
        "within_bounds_articles": len({r["article_id"] for r in pair_results if r["availability_within_nominal_bounds"]}),
        "within_bounds_contracts": len({r["contract_id"] for r in pair_results if r["availability_within_nominal_bounds"]}),
        "within_bounds_provisional_groups": len({r["provisional_group"] for r in pair_results if r["availability_within_nominal_bounds"]}),
        "lineage_http_200": sum(r.get("http_status") == 200 for r in run_records),
        "lineage_statuses": dict(Counter(r.get("lineage", {}).get("status", "unavailable") for r in run_records)),
        "lineage_missing_write_counters": sum(r.get("http_status") == 200 and not r.get("write_counters_complete") for r in run_records),
        "full_window_certified_runs": 0,
        "predictive_admissions": 0,
        "interpretation": "nominal clock and run-summary evidence only; no actual trading-status, feed-completeness, link-validity or independent-episode certificate",
    }
    dump(OUT / "report.json", report)
    dump(OUT / "manifest.json", {"inputs": receipt["inputs"], "outputs": {
        name: sha(OUT / name) for name in ("spec.json", "receipt.json", "pair_clocks.jsonl", "lineage.jsonl", "report.json")}})
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    {"prepare": prepare, "run": run}[sys.argv[1]]()
