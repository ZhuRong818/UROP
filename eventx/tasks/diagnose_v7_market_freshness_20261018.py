"""Price-source diagnostics from a frozen operational snapshot; no labels/scores."""
import json
import math
from datetime import datetime,timedelta
from eventx.settings import REPO_ROOT
from eventx.tasks.prepare_v7_market_capture_20261018 import BASE,RELEASE,sha,write

def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def main():
 health=BASE/'health/20261018T101247Z';out=BASE/'freshness/20261018T101247Z'
 if out.exists():raise RuntimeError('Preserve version')
 out.mkdir(parents=True)
 h=json.loads((health/'report.json').read_text());clock=dt(h['at'])
 rs=[json.loads(l) for l in (health/'journal_snapshot.jsonl').read_text().splitlines()]
 cohort=[json.loads(l) for l in (RELEASE/'cohort.jsonl').read_text().splitlines()];byid={r['market_id']:r for r in cohort}
 trades={k:{} for k in byid};schema_errors=[];received=[]
 for r in rs:
  if r['kind']!='trades' or r.get('http_status')!=200:continue
  p=BASE/'live/objects'/r['payload_sha256'];rows=json.loads(p.read_text())
  for x in rows:
   try:
    token=str(x['token_id']);price=float(x['price']);size=float(x['size']);ts=dt(x['ts'])
    assert math.isfinite(price) and math.isfinite(size) and 0<=price<=1 and size>=0 and ts<=clock
    assert token in [byid[r['market_id']]['yes_asset_id'],byid[r['market_id']]['no_asset_id']]
   except Exception:schema_errors.append({'market_id':r['market_id'],'payload_sha256':r['payload_sha256']});continue
   if token!=byid[r['market_id']]['yes_asset_id']:continue
   # Key preserves distinct fills; raw repeats across overlapping polls are not new trades.
   key=(str(x.get('trade_id')),token,x['ts'],str(x['price']),str(x['size']),str(x.get('side')))
   trades[r['market_id']].setdefault(key,x)
 rows=[]
 for k,r in byid.items():
  xs=list(trades[k].values());last=max((dt(x['ts']) for x in xs),default=None)
  age=(clock-last).total_seconds()/60 if last else None
  n60=sum(clock-timedelta(minutes=60)<=dt(x['ts'])<=clock for x in xs)
  n240=sum(clock-timedelta(minutes=240)<=dt(x['ts'])<=clock for x in xs)
  notional240=sum(float(x['price'])*float(x['size']) for x in xs if clock-timedelta(minutes=240)<=dt(x['ts'])<=clock)
  candidate=age is not None and age<=5 and n60>=3 and n240>=3 and notional240>=100
  rows.append({'market_id':k,'episode_id':r['episode_id'],'unique_captured_yes_trades':len(xs),
   'latest_captured_yes_trade_ts':last.isoformat() if last else None,'trade_age_minutes':age,
   'captured_yes_count60':n60,'captured_yes_count240':n240,'captured_yes_notional240':notional240,
   'observed_activity_screen_pass':candidate,'predictive_eligible':False,
   'reason':'Source completeness,240min warmup, as-of features, terminal status and event evidence not certified; no model/target constructed'})
 (out/'market_diagnostics.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
 s={'as_of':h['at'],'health_sha256':sha(health/'report.json'),'journal_sha256':sha(health/'journal_snapshot.jsonl'),
  'unique_valid_captured_yes_trades':sum(len(v) for v in trades.values()),'schema_error_rows':len(schema_errors),
  'markets_with_yes_trades':sum(bool(v) for v in trades.values()),
  'markets_with_trade_age_le5m':sum(r['trade_age_minutes'] is not None and r['trade_age_minutes']<=5 for r in rows),
  'markets_with_at_least3_yes_trades60m':sum(r['captured_yes_count60']>=3 for r in rows),
  'markets_passing_observed_activity_screen':sum(r['observed_activity_screen_pass'] for r in rows),
  'predictive_admitted_markets':0,'minimum_trade_age_minutes':min((r['trade_age_minutes'] for r in rows if r['trade_age_minutes'] is not None),default=None),
  'interpretation':'Diagnostic from captured fills only. A failed screen can reflect unavailable source coverage; passing does not certify full eligibility.',
  'labels_or_predictions_computed':False,'protected_payloads_read':False}
 write(out/'report.json',s);write(out/'schema_errors.json',schema_errors)
 base=REPO_ROOT/'EVENTX_MARKET_CAPTURE_AND_COHORT_20261018.md';report=REPO_ROOT/'EVENTX_MARKET_CAPTURE_AND_COHORT_20261018_REV2.md'
 report.write_text(base.read_text()+f'''
## Frozen trade-freshness diagnosis (revision2)

At the same snapshot, deduplicating repeated raw fills and validating canonical asset IDs, price/size/time fields yields **{s['unique_valid_captured_yes_trades']} unique canonical YES trades** across **{s['markets_with_yes_trades']} markets**; schema-invalid rows:{s['schema_error_rows']}.

**{s['markets_with_trade_age_le5m']} markets** have an observed YES trade within5minutes; **{s['markets_with_at_least3_yes_trades60m']}** have at least three observed YES trades in the past hour. **{s['markets_passing_observed_activity_screen']}** pass the combined observed screen (age<=5m, count60>=3, count240>=3, notional240>=100). Minimum observed trade age:{s['minimum_trade_age_minutes']}minutes.

This screen uses only captured fills. Completeness and timely warmup remain unverified, so **zero predictive markets are admitted**, even if an activity screen passes. No forecast, target label or model fit was produced. Details: [freshness/report.json](data/v7/market_cohort_capture_20261018/freshness/20261018T101247Z/report.json).

Revision1 is preserved unchanged; revision2 adds this diagnosis using its frozen journal/status snapshot. The underlying collector/cohort/model locks are unchanged.
''')
 write(out/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in list(out.iterdir())+[report] if p.is_file()}})
 print(json.dumps({'directory':str(out.relative_to(REPO_ROOT)),'report':s},indent=2))
if __name__=='__main__':main()
