from pathlib import Path
import json, hashlib

p = Path("eventx/release/presentation_20261012")
m = json.loads((p / "MANIFEST.json").read_text())
m.update({
    "presentation_id": "pres_fe4c1b53f21bb8036a83438a524ca186",
    "deck_url": "https://slidesgpt.com/view/267708b9f2fa",
    "review_status": "all_12_previews_inspected_individually; slide_12_wrapping_repaired_and_reinspected",
    "local_pptx_export": False,
    "powerpoint_application_validation": False,
    "outputs": [
        {"path": str(p / name), "sha256": hashlib.sha256((p / name).read_bytes()).hexdigest()}
        for name in ["SPEAKER_SCRIPT.md", "SLIDE_CONTENT.json", "DECK_RECEIPT.json", "SLIDE_12_REPAIR_RECEIPT.json", "README.md"]
    ],
})
for item in m["sources"]:
    assert hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() == item["sha256"], item["path"]
(p / "MANIFEST.json").write_text(json.dumps(m, indent=2) + "\n")
with Path("docs/progress/2026-10.md").open("a") as f:
    f.write("\n### 12 October — ten-minute progress presentation\n\n- User requested slides and scripts for a ten-minute progress presentation, then asked to emphasize convincing results and discuss bottlenecks at the end. Created a nine-slide main talk with a 600-second planned budget and a 1,149-word spoken script, plus three backup slides. Deliverables are in `eventx/release/presentation_20261012/`; live deck is https://slidesgpt.com/view/267708b9f2fa (presentation ID `pres_fe4c1b53f21bb8036a83438a524ca186`).\n- Main narrative uses the canonical exploratory 9.683467% market-model log-loss gain, the 9,965-row context/timing/semantic comparison, and the 5,388-row exact matched comparison. Numeric claims are sourced in slide notes and the script; source hashes are in `MANIFEST.json`. Bottlenecks appear on slide 9, the final main slide: 21 fitting rows and zero evaluation rows with signed evidence, sparse repeated exact links, outstanding human review and dependence-aware confirmation.\n- Related-work comparisons are explicitly task-specific; no cross-paper performance ranking, algorithmic novelty, confirmed news benefit, causal interpretation or trading-profitability claim is made. The frozen V4 contrast remains B3 versus B0 with its original September 6–October 30 window; it does not confirm every later selected model.\n- The local Artifact Tool runtime was unavailable, so the connected SlidesGPT builder created the deck. All 12 returned previews were downloaded and inspected individually. Crowded backup-slide text was shortened and re-rendered in the same deck, with a repair receipt retained. Local content/notes, deck receipt, script and source manifest are saved. No local PPTX or application validation is claimed.\n- This was artifact preparation from existing aggregate evidence. No software tests, data collection, model fitting, research evaluation, protected outcome payload access, external messages to people, reviewer relabeling or frozen-file mutation occurred. Research next actions and scientific integrity decisions remain unchanged.\n")
print("Saved presentation manifest and appended October progress entry.")

