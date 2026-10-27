"""Close the bounded hypothesis checks with exact late-recovery comparisons."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import json
from eventx.tasks.diagnose_v7_execution_accounting_20261022 import ROOT,AUDIT,RUN,PROBE,RELEASE,lines,sha,stamp,economic,write,verify_manifest
LATE=ROOT/'data/v7/delayed_recovery_20261023/bb25916406b04e52aa3f230324ac68c2'
FAIL=ROOT/'data/v7/delayed_recovery_20261023/e5c322cd5cc544f08ebeeda987ab5553'
CHAIN=ROOT/'data/v7/chain_reconciliation_20261023'
OUT=ROOT/'data/v7/hypothesis_followup_20261023'

def main():
    OUT.mkdir(exist_ok=False)
    manifests=[p/'manifest.json' for p in [LATE,FAIL,CHAIN]]
    for p in manifests:verify_manifest(p)
    windows={r['market_id']:r for r in lines(ROOT/'data/v7/participant_coverage_20261023/market_coverage.jsonl')}
    old={r['market_id']:r for r in lines(AUDIT/'journal.jsonl') if r['kind']=='rest' and r.get('endpoint_kind')=='trades' and r['cycle']==1 and r['source']=='lumid' and r.get('status')=='observed'}
    probe={r['market_id']:r for r in lines(PROBE/'journal.jsonl') if r.get('status')=='observed' and r['taker_only']}
    samples={r['market_id']:r for r in lines(RELEASE/'sample.jsonl')}
    comparisons=[];rows=[];used={}
    def body(base,r):
        p=base/'objects'/r['payload_sha256']
        if sha(p)!=r['payload_sha256']:raise RuntimeError('Payload mismatch')
        used[str(p.relative_to(ROOT))]=sha(p);return json.loads(p.read_text())
    for r in lines(LATE/'journal.jsonl'):
        if r.get('status')!='observed':continue
        cid=r['market_id'];w=windows[cid];lo,hi=w['window_start'],w['window_end']
        before=[p for p in body(RUN,old[cid]) if lo<=stamp(p)<=hi]
        after=body(LATE,r)
        takers=[p for p in body(PROBE,probe[cid])['data'] if lo<=stamp(p)<=hi]
        cp=Counter(economic(p,True) for p in before);miss=[]
        for t in takers:
            k=economic(t,True)
            if cp[k]:cp[k]-=1;continue
            ms=[p for p in after if economic(p,True)==k and str(p['trade_id']).startswith(t['transaction_hash'])]
            row={'market_id':cid,'transaction_hash':t['transaction_hash'],'token_id':str(t['token_id']),'timestamp':stamp(t),
                 'late_full_economic_prefix_matches':len(ms),'recovered':bool(ms)}
            miss.append(row);rows.append(row)
        bkeys=Counter((p['trade_id'],economic(p)) for p in before)
        akeys=Counter((p['trade_id'],economic(p)) for p in after)
        comparisons.append({'market_id':cid,'question':samples[cid]['question'],'old_provider_rows':len(before),'late_provider_rows':len(after),
            'old_records_unchanged':sum((bkeys&akeys).values()),'new_records':sum((akeys-bkeys).values()),'old_records_not_identical':sum((bkeys-akeys).values()),
            'original_missing':len(miss),'recovered_exact_token_time_side_size_rounded_price_prefix':sum(x['recovered'] for x in miss),
            'still_missing':sum(not x['recovered'] for x in miss),'hours_after_window_end':(datetime.fromisoformat(r['response_received_at']).timestamp()-hi)/3600})
    report={'at':datetime.now(timezone.utc).isoformat(),'markets':len(comparisons),'original_missing':len(rows),'recovered':sum(r['recovered'] for r in rows),
            'still_missing':sum(not r['recovered'] for r in rows),'old_provider_rows':sum(r['old_provider_rows'] for r in comparisons),
            'late_provider_rows':sum(r['late_provider_rows'] for r in comparisons),'old_records_unchanged':sum(r['old_records_unchanged'] for r in comparisons),
            'new_records':sum(r['new_records'] for r in comparisons),'old_records_not_identical':sum(r['old_records_not_identical'] for r in comparisons),
            'recovery_method':'Transaction prefix plus exact token/second/side/quantity and ten-decimal rounded price, using the same full economic fingerprint as prior diagnosis.',
            'interpretation':'Partial delayed availability established in sampled windows;47rows remain absent after approximately14.68hours. No universal latency bound or root cause identified.',
            'model_scored':False,'labels_computed':False,'predictive_admissions':0,'historical_availability_changed':False}
    if report['original_missing']!=63:raise RuntimeError('Prior sample count changed')
    for name,rs in [('market_recovery',comparisons),('missing_row_recovery',rows)]:
        (OUT/(name+'.jsonl')).write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rs))
    write(OUT/'report.json',report);write(OUT/'input_payload_hashes.json',used)
    table='\n'.join('|'+r['question'].replace('|','/')+'|'+str(r['original_missing'])+'|'+str(r['recovered_exact_token_time_side_size_rounded_price_prefix'])+'|'+str(r['still_missing'])+'|' for r in comparisons)
    md=f'''# EventX source hypotheses — completed follow-up

23 October 2026. Supersedes the unresolved questions in the earlier review package where the evidence below applies. Original frozen reports remain preserved.

## What the checks establish

1. **Four ambiguous records resolved.** All belong to one successful CTF exchange transaction. Different provider ID suffixes match different on-chain order hashes; log indices564,566,568,576 separate the equal-sized orders. Summing the duplicate-looking candidates doubles the provider amounts. This sample does not support multi-hop aggregation or competing retry transactions as their explanation.
2. **Partial delayed recovery established.** A repeat of the same four historical windows approximately14.68hours after their endpoints returned138provider rows, versus45originally. Exact record comparison preserves{report['old_records_unchanged']}old records, adds{report['new_records']}, and leaves{report['old_records_not_identical']}old records non-identical/absent. Of the63previously missing taker-side rows, **{report['recovered']}now have matching transaction/token/time/side/size/rounded-price records;{report['still_missing']}remain absent.** Late retrieval is not backdated availability. A single repeat does not identify when the records arrived or their upstream cause.
3. **The wallet mismatch is explained by mixed field semantics.**36provider IDs are `transactionHash:orderHash`;their taker fields equal the on-chain event taker.16bare IDs use the event maker instead. Direct API wallets match the event maker for52/52rows;provider taker equals transaction sender for0/52. The official exchange implementation uses these different order roles. A generic router or call-graph join would not address the observed schema mixture.
4. **Chain event ordering is now available for the sampled52rows.** All52map uniquely to52distinct OrderFilled events across29successful transactions. These are order-level event identities,not52independent economic trades. Block/transaction/log indices order settlement,not necessarily CLOB matching or information arrival. Seven of nine price sequences are monotonic;this does not validate API row order.

## Delayed recovery by control market

|Control market|Originally missing|Recovered later|Still absent|
|---|---:|---:|---:|
{table}

Before the repeat,39of63missing records were older than the latest provider trade in their own market;all63tokens also occurred in the provider snapshot. Missing sizes ranged0.31–9,161tokens. Thus neither an excluded-token catalog nor a simple newest-record-only lag explains the whole sample. The repeat confirms some delayed availability, while substantial persistent omissions remain. These are CLOB outcome-token markets;no pool field exists to support a pool-level attribution.

## Limits and failed attempts

The receipt probe obtained29successful receipts and114allowlisted fill logs,then stopped when historical `eth_getCode` returnedHTTP403. No address-code classification succeeded. An exchange address appearing in event taker does not imply it was the outer transaction sender. Code presence alone would not establish router identity or distinguish all smart/delegated accounts.

Both network probes first failed in the sandbox; those attempts are preserved. Four authorized provider requests then succeeded below the1000-row page cap. The chain evidence comes from one RPC node;it does not certify finality/reorg history. No protected payloads, forecasts, labels or model changes were involved.

## Remaining provider questions

The previous broad ID/wallet questions can now be made specific:

- Confirm the two ID/field conventions observed here and define when each is emitted. Document the canonical counting unit and whether one order can emit multiple fills per transaction.
- Explain the47remaining omissions in the attached four exact windows, particularly the45concentrated in one control market. State filters, upstream source and any collection outages.
- Explain the93late-added records, provide first-ingestion/revision clocks,and specify backfill behavior. Our two snapshots only bound late availability.
- Expose chain ID,exchange,order hash,block hash/number,transaction/log index and removal/reorg state;provide a matching-engine sequence separately if matching order is needed.

These questions are prepared for provider review and have **not been sent**. The next research gate remains source coverage and compatibility with the frozen model. The scheduled local source workflow continues independently;this diagnostic does not activate event forecasting.

## Evidence

- [Detailed chain and hypothesis report](EVENTX_SOURCE_HYPOTHESES_RESULTS_20261023.md).
- `data/v7/chain_reconciliation_20261023/row_mapping.jsonl`:52event mappings with receipt IDs and comparisons.
- `data/v7/delayed_recovery_20261023/bb25916406b04e52aa3f230324ac68c2/`:four late responses,exact windows and receipt clocks.
- `data/v7/hypothesis_followup_20261023/`:reproducible full-fingerprint comparisons and this report.
- Official semantics: [exchange event definition](https://github.com/Polymarket/ctf-exchange-v2/blob/main/src/exchange/interfaces/ITrading.sol),[exchange implementation](https://github.com/Polymarket/ctf-exchange-v2/blob/main/src/exchange/mixins/Trading.sol),[contracts](https://docs.polymarket.com/resources/contracts),[trade API](https://docs.polymarket.com/api-reference/feeds/list-trades). Exact Solidity snapshots are preserved with the chain probe.
'''
    public=ROOT/'EVENTX_SOURCE_HYPOTHESES_FOLLOWUP_20261023.md';public.write_text(md);(OUT/'REPORT.md').write_text(md)
    request='''# Provider follow-up — prepared, not sent

Please review the bounded EventX V7 source comparison in EVENTX_SOURCE_HYPOTHESES_FOLLOWUP_20261023.md.

We mapped52provider rows to52distinct OrderFilled events in29successful Polygon transactions.36IDs use transactionHash:orderHash with event taker;16bare IDs instead expose event maker in the taker field. Please confirm these conventions and the canonical counting/deduplication rule,including repeated partial fills of one order within a transaction.

The same four historical windows returned45rows initially and138about14.68hours after their endpoints.16of63originally missing direct taker-side records appeared;47remain absent,45in one control market. Please reconcile these exact missing identities,explain filters/outages/backfills,and supply first-ingestion/revision timestamps. The timestamped raw responses and market IDs are in the attached evidence directories;no credentials are needed in the reply.

Please expose chain/exchange/order identifiers,block hash/number,transaction/log indices,and reorg/removal status. Document settlement order separately from any available matching-engine sequence.

Evidence:data/v7/hypothesis_followup_20261023/market_recovery.jsonl;missing_row_recovery.jsonl;data/v7/chain_reconciliation_20261023/row_mapping.jsonl. Original and late receipt hashes are linked from their manifests. This is a source compatibility inquiry,not a request to alter historical records or backdate availability.
'''
    (OUT/'PROVIDER_FOLLOWUP_DRAFT.md').write_text(request)
    files=list(OUT.iterdir())+[public,Path(__file__).resolve()]+manifests
    write(OUT/'manifest.json',{'files':{str(p.relative_to(ROOT)):sha(p) for p in files}})
    state=ROOT/'CURRENT_STATE.md';s=state.read_text()
    s=s.replace('(local workflow active; execution accounting diagnosed)','(sampled chain identities resolved; partial delayed recovery)')
    a=s.index('- Next: bounded repeat of four exact provider windows');b=s.index('\n\n',a)
    s=s[:a]+'''- Same four windows re-fetched23Oct01:53UTC(~14.68hafter endpoints):45→138provider
  rows,45unchanged+93added;16/63missing taker rows recovered,47remain(45inonecontrol).
  Full economic+transaction-prefix checks agree. Late availability is not backdated.
- Latest:`EVENTX_SOURCE_HYPOTHESES_FOLLOWUP_20261023.md`; narrower unsent request
  `data/v7/hypothesis_followup_20261023/PROVIDER_FOLLOWUP_DRAFT.md`. Remaining review:
  general mixed-schema/counting contract,47omissions,backfill/ingestion clocks.
  Local workflow checkpoint23Oct01:53UTCstillwaiting;original474,270records,0admissions.'''+s[b:]
    state.write_text(s)
    with (ROOT/'docs/progress/2026-10.md').open('a') as f:
        f.write('\n### Same-window delayed recovery — '+report['at']+'\n\n')
        f.write('Bounded four-market provider retry: initial sandbox ConnectError preserved; network run completed4/4HTTP200,allpages below1000cap. Same historic windows approximately14.68hoursafter endpoint:45old rows→138late rows;45unchanged,93added,0oldremoved. Full transaction-prefix/token/time/side/size/rounded-price join recovers16of63missing taker-side rows;47remain(45onecontrol,2another). Late first retrieval is not historical availability.\n\n')
        f.write('Frozen evidence:data/v7/hypothesis_followup_20261023/manifest.json;EVENTX_SOURCE_HYPOTHESES_FOLLOWUP_20261023.md. Narrowed provider request prepared,unsent. Earlier review questions partially resolved by chain evidence;remainingcoverage/backfill/general-accountingreview persists. Workflow status01:53UTCwaitingfororiginal;originalcheckpoint474270records,zero admissions. No tests/model/protected evaluation changes.\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
