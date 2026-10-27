from pathlib import Path
import hashlib, json

p=Path("eventx/release/presentation_20261012/rev2")
old_url="https://slidesgpt.com/view/267708b9f2fa"
new_url="https://slidesgpt.com/view/feec53a53350"
for name in ["SPEAKER_SCRIPT.md","DETAILED_EXPLANATION.md"]:
    q=p/name
    q.write_text(q.read_text().replace(old_url,new_url))
d=json.loads((p/"SLIDE_CONTENT.json").read_text())
d["presentation_id"]=""
for slide in d["slides"]:
    slide.pop("force_edit",None)
(p/"SLIDE_CONTENT.json").write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
a=json.loads(Path("data/v5/no_terminal_baseline_diagnostic_20261009/report.json").read_text())
r=json.loads(Path("data/v5/market_learner_screen_20261009/report.json").read_text())["results"]["hgb_7_600"]["folds"]["5"]
gain=100*(r["baseline_metrics"]["log_loss"]-r["metrics"]["log_loss"])/r["baseline_metrics"]["log_loss"]
assert round(gain,2)==1.17
assert round(a["paired_improvement"]["log_loss_percent_reduction"],2)==9.68
receipt=json.loads((p/"DECK_RECEIPT.json").read_text())
assert len(receipt["slides"])==12
assert [s["slidenum"] for s in receipt["slides"]]==list(range(1,13))
assert all(s["talktrack"] for s in d["slides"])
manifest={
 "prepared_at":"2026-10-12","revision":2,"results_through":"2026-10-10",
 "deck_url":new_url,"presentation_id":receipt["presentation_id"],
 "main_slides":9,"backup_slides":3,"planned_seconds":600,"spoken_words":1223,
 "sources":[{"path":q,"sha256":hashlib.sha256(Path(q).read_bytes()).hexdigest()} for q in ["data/v5/no_terminal_baseline_diagnostic_20261009/report.json","data/v5/market_learner_screen_20261009/report.json","eventx/release/v5/OPENED_METHOD_SURVEY_20261009.md","data/v5/opened_news_offset_trial_20261009/report.json","data/v5/method_screen_observed_row_join_20261009/report.json","data/v7/signed_evidence_exploration_20261010/report.json","eventx/release/v7/pilot_20261010/PREPARATION_RESULTS_REV2.md","eventx/release/v5/PROTOCOL_V1_1.md","eventx/release/v4/protocol.json","eventx/release/paper_a_20261010/TABLES.md","MARKET_NEWS_PAPER_A_DRAFT_20261010_REV2.md","eventx/features/v5_market.py","eventx/release/literature_baselines_20261010/evidence.json"]],
 "comparison_log_loss_percent_reductions":{"linear_vs_tree":a["paired_improvement"]["log_loss_percent_reduction"],"earlier_tree_vs_selected_hgb":gain},
 "research_evaluation_performed":False,"protected_outcome_payloads_accessed":False,
 "review":"All 12 slide previews inspected individually. Theme receipt lists 11 unchanged images; backup 11 retains its distinct preview style.",
 "runtime":"Connected SlidesGPT; local Artifact Tool and browser-control runtime unavailable",
 "offline_copy":{"embedded_slides":12,"network_dependencies":0,"format":"HTML embedding rendered images and submitted notes","directly_editable_slide_objects":False},
 "local_pptx_export":False,"powerpoint_application_validation":False,
 "outputs":[{"path":str(p/name),"sha256":hashlib.sha256((p/name).read_bytes()).hexdigest()} for name in ["EVENTX_PROGRESS_PRESENTATION.html","SPEAKER_SCRIPT.md","DETAILED_EXPLANATION.md","SLIDE_CONTENT.json","DECK_RECEIPT.json","README.md"]]
}
(p/"MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")
with Path("docs/progress/2026-10.md").open("a") as f:
    f.write("\n### 12 October — presentation revision 2: rationale, aims and baseline gains\n\n- User requested detailed rationale, aims, completed achievements and explanation of improvements over baseline. Reworked the nine-slide main sequence while retaining a 600-second planned duration and three backup slides. Updated spoken script has 1,223 words. Current deliverables are in `eventx/release/presentation_20261012/rev2/`: offline `EVENTX_PROGRESS_PRESENTATION.html`, timed `SPEAKER_SCRIPT.md`, `DETAILED_EXPLANATION.md`, content and receipts.\n- Added the separate selected-booster comparison from canonical `data/v5/market_learner_screen_20261009/report.json`: on 112,616 matched fold-5 rows, earlier tree log loss 0.34888430757451633 versus selected HGB 0.3448163187401466, gain 0.004067988834369707 nats or 1.165999371726069%. This remains separate from the 9.683467% logistic-versus-tree diagnostic on 364,903 rows. Gains are not added. Brier and AP changes, forward-fold consistency and interpretation of probability losses are explained.\n- Rationale emphasizes incremental information beyond a strong market history model. News results remain honestly scoped: exposure-context correction leads the 9,965-row trial, selected news timing trails market HGB on 5,388 matched rows, and zero evaluation coverage prevents interpreting the signed-evidence score difference as news benefit. Completed preparation includes resolution text for 116/120 review pairs; this is not semantic accuracy or historical metadata certification. Bottlenecks remain on slide 9.\n- The connected builder appended the 12 revision slides at positions 14–25 despite `force_edit=true`. Preserved `APPENDED_REVISION_RECEIPT.json` and created a clean revised deck at https://slidesgpt.com/view/feec53a53350 with presentation ID `pres_c5b119b57ca8f9a86972347f16d9f348`. The earlier live deck is superseded. All 12 revised previews downloaded and inspected individually. The theme operation returned 11 unchanged preview URLs and omitted backup slide 11; its original, separately styled preview remains in the offline export.\n- Browser-control runtime could not start. Unauthenticated online-page read redirects to service sign-in. Created a self-contained HTML presentation embedding all 12 rendered images and notes, with keyboard navigation, notes and full-screen controls. It has no network dependencies; the slide images are not directly editable. No local PPTX export or PowerPoint application inspection is claimed. Exact slide content/notes remain in JSON.\n- Source hashes and aggregate arithmetic checks are in `rev2/MANIFEST.json`. No software tests, forecast fitting/evaluation, new collection, protected outcome payload access, model promotion, reviewer relabeling, external messages to people or frozen research artifact changes occurred.\n")
print(json.dumps({"slides":12,"main_seconds":600,"script_words":1223,"baseline_gains_round_correctly":True,"manifest_saved":True,"progress_appended":True}))

