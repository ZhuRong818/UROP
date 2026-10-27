"""Prepare targeted evidence recovery and adjudication without certifying reviews."""
import hashlib
import json
from pathlib import Path

def main():
    source=Path("data/v6/boundary_restored_submission_20260916")
    out=Path("data/v6/boundary_adjudication_20260916")
    if out.exists():raise FileExistsError(out)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    m=json.loads((source/"manifest.json").read_text())
    assert all(sha(source/n)==v for n,v in m["outputs"].items())
    read=lambda p:[json.loads(x) for x in p.open()]
    family=read(source/"family_submission_snapshot.jsonl")
    story=read(source/"story_submission_snapshot.jsonl")
    selected=[r for r in family if r["decision"] in {"must_link","unresolved"}]
    cards={c["contract_id"]:c for r in selected if r["decision"]=="unresolved"
           for field in ("reserved_contracts","development_contracts") for c in r[field]}
    out.mkdir()
    records=[]
    for kind,rr in (("family",selected),("story",[r for r in story if r["decision"]!="distinct_story"])):
        for r in rr:
            records.append({"kind":kind,"review_id":r["review_id"],"submitted_review":r,
                "adjudicator":None,"adjudication_decision":None,"evidence_refs":[],"rationale":None,
                "status":"awaiting_evidence_and_independent_confirmation",
                "not_blind_second_review":True})
    with (out/"adjudication_packet.jsonl").open("w") as f:
        for r in records:f.write(json.dumps(r,sort_keys=True)+"\n")
    ids={v:sorted(c["market_id"] for c in cards.values() if c["venue"]==v) for v in ("kalshi","polymarket")}
    quote=lambda values:",".join("'"+v.replace("'","''")+"'" for v in values)
    kalshi=f"""SELECT ticker, event_ticker, title, yes_sub_title, no_sub_title,
open_time, close_time, expiration_time, ingest_ts, source, source_endpoint, source_run_id,
raw->>'rules_primary' AS rules_primary, raw->>'rules_secondary' AS rules_secondary
FROM prediction_markets.kalshi_markets
WHERE ticker IN ({quote(ids['kalshi'])}) AND ingest_ts < '2026-07-22T00:00:00Z'
ORDER BY ticker, ingest_ts LIMIT 500"""
    poly=f"""SELECT condition_id, question, ingest_ts, source, source_endpoint, source_run_id,
raw->>'description' AS description, raw->>'groupItemTitle' AS contract_subtitle,
raw->>'resolutionSource' AS resolution_source
FROM prediction_markets.polymarket_markets
WHERE condition_id IN ({quote(ids['polymarket'])}) AND ingest_ts < '2026-07-22T00:00:00Z'
ORDER BY condition_id, ingest_ts LIMIT 500"""
    (out/"kalshi_rules.sql").write_text(kalshi+"\n")
    (out/"polymarket_rules.sql").write_text(poly+"\n")
    (out/"selection.json").write_text(json.dumps(ids,indent=2)+"\n")
    report={"family_must_link_confirmation_tasks":40,"family_unresolved_tasks":15,"story_update_tasks":2,
        "adjudication_tasks":len(records),"requested_kalshi_contracts":len(ids["kalshi"]),
        "requested_polymarket_contracts":len(ids["polymarket"]),"existing_rule_cards":sum(bool(c["rule_evidence"]) for c in cards.values()),
        "certified":False,"reviews_adopted":False,"forecast_outcomes_requested":False}
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    (out/"manifest.json").write_text(json.dumps({"inputs":{str(source/"manifest.json"):sha(source/"manifest.json")},
        "code_sha256":sha(Path(__file__)),"outputs":{p.name:sha(p) for p in out.iterdir()}},indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__":main()
