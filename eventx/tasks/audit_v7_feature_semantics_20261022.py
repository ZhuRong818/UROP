"""Trace frozen feature units and audit source screens without loading a predictor."""
import json
from pathlib import Path
from collections import Counter
from eventx.tasks.discover_v7_direct_pilot_20261022 import REPO_ROOT,now,sha,write,verify_originals
from eventx.tasks.audit_v7_direct_pilot_20261022 import stamp

OUT=REPO_ROOT/'data/v7/feature_semantics_20261022'
AUDIT=REPO_ROOT/'data/v7/direct_source_pilot_20261022/audits/20261022T105137Z_f62ac0'
RUN=REPO_ROOT/'data/v7/direct_source_pilot_20261022/live'

def main():
    OUT.mkdir(exist_ok=False)
    code_receipts=[]
    references=[('data/v3_1_historical/primary/development/prepared/manifest.json','eventx/tasks/prepare_v3_1_historical_development_arrays.py'),
                ('data/v3_1_historical/primary/development/examples_manifest.json','eventx/tasks/build_v3_1_historical_development_examples.py'),
                ('data/v4/discovery/examples/manifest.json','eventx/tasks/build_v4_discovery_examples.py'),
                ('data/v5/market_condition_tuning_20261012/manifest.json','eventx/tasks/tune_v5_market_conditions_20261012.py')]
    for manifest,code in references:
        h=next(x['sha256'] for x in json.loads((REPO_ROOT/manifest).read_text())['artifacts'] if x['path']==code)
        if sha(REPO_ROOT/code)!=h: raise RuntimeError('Frozen code mismatch')
        code_receipts.append({'manifest':manifest,'code':code,'sha256':h})
    sample=[json.loads(l) for l in (REPO_ROOT/'eventx/release/v7/direct_source_pilot_20261022/sample.jsonl').read_text().splitlines()]
    by_id={x['market_id']:x for x in sample}
    record=[json.loads(l) for l in (AUDIT/'journal.jsonl').read_text().splitlines()]
    summaries={(r['market_id'],r['cycle'],r['source']):r for r in record if r['kind']=='window_summary'}
    comparisons={(r['market_id'],r['cycle']):r for r in map(json.loads,(AUDIT/'market_comparison.jsonl').read_text().splitlines())}
    output=[]
    for r in record:
        if r['kind']!='rest' or r.get('source')!='venue' or r.get('endpoint_kind')!='trades' or r.get('status')!='observed':continue
        c=comparisons.get((r['market_id'],r['cycle']))
        if not c or c['status']!='comparable_single_page_window':continue
        s=by_id[r['market_id']];end=c['window_to'];path=RUN/'objects'/r['payload_sha256']
        if sha(path)!=r['payload_sha256']:raise RuntimeError('Receipt payload mismatch')
        rows=json.loads(path.read_text());yes=[x for x in rows if str(x['asset'])==s['yes_asset_id']]
        w240=[x for x in yes if end-14400 < stamp(x['timestamp']) <= end]
        w60=[x for x in yes if end-3600 < stamp(x['timestamp']) <= end]
        size=sum(float(x['size']) for x in w240);cash=sum(float(x['size'])*float(x['price']) for x in w240)
        age=c.get('latest_yes_age_minutes');fresh=age is not None and 0<=age<=5
        rest_ok=fresh and len(w60)>=3 and len(w240)>=3
        signatures=Counter((x.get('transactionHash'),x.get('proxyWallet'),x['asset'],x['timestamp'],x['side'],str(x['price']),str(x['size'])) for x in rows)
        output.append({'market_id':s['market_id'],'role':s['diagnostic_role'],'cycle':r['cycle'],'payload_sha256':r['payload_sha256'],
                       'window_to':end,'size240':size,'cash240':cash,'yes60_open_left':len(w60),'yes240_open_left':len(w240),
                       'historical_size_screen':bool(rest_ok and size>=100),'cash_screen_same_open_left':bool(rest_ok and cash>=100),
                       'prior_frozen_cash_screen':c.get('observed_activity_screen',False),
                       'exact_economic_wallet_signature_duplicate_rows':sum(n-1 for n in signatures.values()),
                       'empty_transaction_hash_rows':sum(not x.get('transactionHash') for x in rows),
                       'execution_identity_certified':False})
    macro=[x for x in output if x['role']=='prospective_macro_candidate']
    report={'at':now().isoformat(),'verified_code_chain':code_receipts,'production_locks_verified':verify_originals(),
            'model_loaded_or_scored':False,'labels_computed':False,'historical_or_v4_holdout_payloads_read':False,
            'historical_notional_semantics':'Polymarket size; Kalshi count; summed quantity, not price-times-quantity',
            'historical_window_convention':'(t-window,t], from searchsorted side=right at both boundaries',
            'historical_ordering':'market,timestamp_us,source ordinal; upstream SQL canonical YES asset and trade_id ordering; adjacent duplicate trade_id+timestamp collapsed',
            'model_columns_affected':['log1p_notional_60m','log1p_notional_240m','size_rate_ratio'],
            'candidate_comparable_windows':len(macro),'candidate_size_screen_passes':sum(x['historical_size_screen'] for x in macro),
            'candidate_cash_screen_passes':sum(x['cash_screen_same_open_left'] for x in macro),
            'candidate_boundary_or_unit_screen_changes':sum(x['historical_size_screen']!=x['prior_frozen_cash_screen'] for x in macro),
            'all_roles_signature_duplicate_rows_across_overlapping_windows':sum(x['exact_economic_wallet_signature_duplicate_rows'] for x in output),
            'feature_compatibility_status':'not_established',
            'blockers':['Direct API lacks documented unique execution ID matching provider trade_id; maker/taker row accounting unresolved.',
                        'Same-second distinct-price ordering is unresolved for an exact last execution.',
                        'Direct-source completeness and historical provider selection are not equivalent.',
                        'Source receipt gaps prevent retrospective timely-history claims.'],
            'new_api_facts':{'checked_at':'2026-10-22','migration_url':'https://docs.polymarket.com/migrate/data-api-v1-to-v2',
                'retirement_notice':'Legacy Data API retirement stated as2026-10-24',
                'trade_url':'https://docs.polymarket.com/api-reference/feeds/list-trades',
                'critical_changes':['condition filter replaces market','data/pagination envelope and cursor','market-scoped start/end ignored; local filtering required','taker_only=false includes maker rows; true each fill taker-side','default minimum size0.01;0 does not remove documented minimum']},
            'decision':'Preserve historical cash diagnostics; future size fields explicit. Do not score until semantics and coverage pass. API migration belongs to V7 source study, not project v2 research.'}
    (OUT/'window_units.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in output))
    write(OUT/'report.json',report)
    md=f'''# EventX: feature semantics and API migration diagnosis

## Findings

The frozen historical preparation assigns Polymarket `size` to its field named `notional`. The market model therefore expects summed **token quantity** in its two notional columns and derived size ratio. Substituting cash value (`price × size`) would change three model inputs. Historical code hashes verified through four linked manifests; the predictor was not loaded.

Earlier source diagnostics used cash value and inclusive left boundaries. The historical trailing sums use **(t−window, t]**. Their saved results remain intact and should be described as cash-based source diagnostics, not exact replicas of model-input eligibility.

A versioned re-audit of {len(macro)} comparable candidate windows found **{report['candidate_size_screen_passes']} quantity-screen passes**, versus **{report['candidate_cash_screen_passes']} cash-screen passes** with the same open-left boundary. It changed {report['candidate_boundary_or_unit_screen_changes']} candidate pass decisions relative to the frozen earlier diagnostic. These overlap in time and do not count independent events. No predictive admissions follow.

## Source migration required before the first release

Polymarket's [official migration notice](https://docs.polymarket.com/migrate/data-api-v1-to-v2) states retirement of the legacy Data API on24October2026. The [replacement trade API](https://docs.polymarket.com/api-reference/feeds/list-trades) changes filtering and pagination. In particular, market-scoped requests ignore start/end bounds, so simply changing the URL would silently break six-hour reconciliation. The new collector must traverse ordered cursors and filter windows locally, leaving capped or unordered pages unresolved.

The replacement documentation distinguishes taker-only rows from maker-inclusive rows and specifies a default minimum trade size. Neither API success nor matching economic fingerprints establishes unique executions or reproduces historical provider sampling. The migration does not authorize changing a frozen historical study or the project-v2 cycle.

## Remaining compatibility gaps

- Map provider `trade_id` to venue execution identity and account for maker/taker rows.
- Resolve ordering of different-price trades sharing a timestamp; a transaction hash alone is not necessarily one execution.
- Verify source coverage, retained-size thresholds, availability and pagination independently of activity.
- Preserve received-at clocks; backfill cannot restore timely capture during an outage.

The fixed model remains blocked from scoring. Units are now understood; exact observation semantics are not yet established. Machine evidence: `data/v7/feature_semantics_20261022/report.json` and `window_units.jsonl`.
'''
    (OUT/'REPORT.md').write_text(md);public=REPO_ROOT/'EVENTX_FEATURE_SEMANTICS_20261022.md';public.write_text(md)
    files=[*OUT.iterdir(),public,Path(__file__).resolve(),AUDIT/'manifest.json']
    write(OUT/'manifest.json',{'files':{str(p.relative_to(REPO_ROOT)):sha(p) for p in files}})
    print(json.dumps({k:report[k] for k in ['candidate_comparable_windows','candidate_size_screen_passes','candidate_cash_screen_passes','candidate_boundary_or_unit_screen_changes','feature_compatibility_status']}))

if __name__=='__main__':main()
