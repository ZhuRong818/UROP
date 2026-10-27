"""Record Codex's explicit first semantic review of the fixed 30-contract packet."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT/'data/v5/topic_coverage_triage_20260914/review_packet.jsonl'
OUT = ROOT/'data/v5/topic_first_review_20260914'
DECISIONS = [
 ('KXEARNINGSMENTIONJPM-26JUL14-TARI','corporate_traditional_financial','Named word in JPMorgan earnings call'),
 ('KXEARNINGSMENTIONNFLX-26JUL02-COMP','corporate_traditional_financial','Named word in Netflix earnings call'),
 ('KXEARNINGSMENTIONPEP-26JUN29-HEAL','corporate_traditional_financial','Named word in PepsiCo earnings call'),
 ('0x3616e2f2cd616de0614c3c7a0fe1e791c93de320fef017a496b723fcbceefce8','corporate_traditional_financial','Alphabet market-cap rank'),
 ('KXEARNINGSMENTIONMS-26JUL15-PRIV','corporate_traditional_financial','Named phrase in Morgan Stanley earnings call'),
 ('KXXRPMAXMON-XRP-26JUN30-150','crypto','XRP price threshold'),
 ('KXSOLMINMON-SOL-26JUN30-6000','crypto','SOL price threshold'),
 ('0xc6d651e1f7f9fc47f0079c1fba2fc18290cd8a45644f76f73ef7a1ae35f8d65f','crypto','Bitcoin price threshold'),
 ('0x8e7a03cb1970e2ad6533b01892403516b6b3f5b5fa90ed7d104c28b27e40ba00','crypto','Company Bitcoin disposal; crypto-specific outcome, cross-topic flag retained'),
 ('KXWCADS-26JUL19-COIN','corporate_traditional_financial','Corporate advertising decision; crypto company identity does not make this a crypto outcome'),
 ('KXFED-26JUN-T3.50','macroeconomics','Federal funds policy-rate threshold'),
 ('KXECONSTATCPI-26JUN-T-0.2','macroeconomics','CPI print with named numerical bin'),
 ('KXBRENTMON-26JUN3017-T94.99','corporate_traditional_financial','Commodity closing-price threshold, rather than macro indicator release'),
 ('KXU3-26JUL-T4.4','macroeconomics','Unemployment statistic'),
 ('KXDOTPLOT-26JUN-3.5','macroeconomics','Central-bank policy projection'),
 ('KXTOPSONG-26JUL04-CHO','other_ambiguous','Music-chart ranking'),
 ('KXPGATOP20-USO26-SSCH','sports','Named golfer tournament finishing position'),
 ('KXNBATRADE-27FEB12-ADAVIS23','sports','Named basketball player roster transaction'),
 ('0x3ceb5b631318be5000758200590efe2b308a581d6787c3e7bc050bfd8f627627',None,'Belgium win question lacks sport, opponent and event context; fetch full semantics before assignment'),
 ('KXINXMAXMM-30JUN2026-7660','corporate_traditional_financial','SP500 index level threshold'),
 ('KXTRUMPPASSPORT-26-JUL20','politics_public_policy','Government passport issuance policy'),
 ('0xd6591e966aebf061547ef34cdf3494ed318969887c8b7fb53f10ed5d5461a547','politics_public_policy','Colombian presidential election winner'),
 ('KXCAGOVMATCHUP-26JUN-XBECCBIA','politics_public_policy','California primary nominees'),
 ('KXLEAVESTARMER-26SEP01','politics_public_policy','Prime-minister tenure'),
 ('KXMAYORLA-26-AMIL','politics_public_policy','Mayoral election; Adam Miller subtitle is essential'),
 ('KXNBASERIESSPREAD-26NYKSASFIN-NYK3','sports','Basketball series spread'),
 ('KXPGAHOLEINONE-THOC26-1','sports','Golf tournament performance statistic'),
 ('KXWCPRICE-26JULWCSEMI1-2500','other_ambiguous','Event-ticket resale price, not sporting performance; taxonomy-boundary adjudication required'),
 ('0x328583376667b725cc6848dc9b61b205579b1314ecdb4334ea245aec270d2c66','sports','World Cup tournament progression'),
 ('KXLOL-MSI26-TES','sports','Esports competition winner'),
]


def main():
    packet = {r['market_id']:r for l in PACKET.open() if (r:=json.loads(l))}
    assert len(packet)==len(DECISIONS)==30
    assert set(packet)=={i for i,_,_ in DECISIONS}
    rows=[]
    for identity, topic, reason in DECISIONS:
        r=packet[identity]
        rows.append({**r,'reviewer_1':'Codex source-text review 2026-09-14',
            'reviewer_1_topic':topic,'reviewer_1_rationale':reason,
            'changed_from_suggestion':topic is not None and topic!=r['suggested_topic'],
            'reviewer_2':None,'topic_approved':False,'family_verified':False,
            'evidence_scope':'cached question and YES subtitle, not certified historical resolution criteria'})
    OUT.mkdir(exist_ok=False)
    (OUT/'first_review.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    report={'reviewed':len(rows),'first_reviewer_assigned':sum(r['reviewer_1_topic'] is not None for r in rows),
        'changes_from_suggestion':sum(r['changed_from_suggestion'] for r in rows),
        'unresolved':sum(r['reviewer_1_topic'] is None for r in rows),
        'independent_second_reviews':0,'approved_topics':0,
        'not_population_accuracy_estimate':True,'new_outcomes_read':False}
    (OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT/'manifest.json').write_text(json.dumps({'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [PACKET,Path(__file__)]},
        'outputs':{p.name:sha(p) for p in OUT.iterdir()}},indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
