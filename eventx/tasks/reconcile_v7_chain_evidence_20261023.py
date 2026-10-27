"""Reconcile fixed provider rows to scoped on-chain events; diagnostic only."""
from collections import Counter
from decimal import Decimal
from datetime import datetime,timezone
from pathlib import Path
import json
from eventx.tasks.diagnose_v7_execution_accounting_20261022 import ROOT,lines,sha,write,verify_manifest
OUT=ROOT/'data/v7/chain_reconciliation_20261023'
LOCAL=ROOT/'data/v7/source_hypotheses_20261023'
CHAIN=ROOT/'data/v7/scoped_chain_20261023/c8c3fe64457e419989135e831b06ee07'
FAILED=ROOT/'data/v7/scoped_chain_20261023/9e233ea9bdcb42eaa70d6eb7e501cd73'

def main():
    OUT.mkdir(exist_ok=False)
    for base in [LOCAL,CHAIN,FAILED]:verify_manifest(base/'manifest.json')
    provider=lines(LOCAL/'provider_rows.jsonl');fills=lines(CHAIN/'decoded_fills.jsonl')
    receipts={r['transactionHash']:r for r in lines(CHAIN/'receipts.jsonl')}
    ambiguous={r['provider_id_sha256'] for r in lines(LOCAL/'ambiguous.jsonl')}
    rows=[]
    for p in provider:
        parts=p['provider_id'].split(':');suffix=parts[1] if len(parts)==2 else None
        if len(parts)>2:raise RuntimeError('Unexpected provider ID')
        candidates=[]
        for f in fills:
            if f['transaction_hash'] not in p['candidate_transactions'] or f['token_id']!=p['token_id']:continue
            if suffix is not None and f['order_hash']!=suffix.lower():continue
            if suffix is None and f['taker']!=f['exchange']:continue
            ma,ta=Decimal(f['maker_amount']),Decimal(f['taker_amount'])
            if f['side'] not in [0,1] or not ma or not ta:continue
            size=(ta if f['side']==0 else ma)/Decimal(10**6)
            price=ma/ta if f['side']==0 else ta/ma
            err=abs(price-Decimal(p['price']))
            if size==Decimal(p['size']) and err<Decimal('1e-9') and ('BUY' if f['side']==0 else 'SELL')==p['side']:
                candidates.append(dict(f,price_error=str(err)))
        row={'provider_id_sha256':p['provider_id_sha256'],'market_id':p['market_id'],'id_shape':'tx_plus_order_hash' if suffix else 'bare_transaction',
             'candidate_fill_count':len(candidates),'previously_ambiguous':p['provider_id_sha256'] in ambiguous}
        if len(candidates)==1:
            f=candidates[0];receipt=receipts[f['transaction_hash']]
            row.update(transaction_hash=f['transaction_hash'],block_hash=f['block_hash'],block_number=f['block_number'],transaction_index=f['transaction_index'],
                       log_index=f['log_index'],order_hash=f['order_hash'],receipt_status=receipt['status'],removed=f['removed'],
                       provider_taker_equals_event_taker=p['taker']==f['taker'],provider_taker_equals_event_maker=p['taker']==f['maker'],
                       provider_taker_equals_transaction_from=p['taker'].lower()==receipt['from'].lower(),
                       event_maker_matches_direct_wallet=f['maker'] in p['candidate_proxy_wallets'],provider_taker_is_exchange=p['taker']==f['exchange'],
                       price_error=f['price_error'])
        rows.append(row)
    matches=[r for r in rows if r['candidate_fill_count']==1]
    group={}
    for shape in sorted({r['id_shape'] for r in rows}):
        rr=[r for r in matches if r['id_shape']==shape]
        group[shape]={'rows':len(rr),**{k:sum(r[k] for r in rr) for k in ['provider_taker_equals_event_taker','provider_taker_equals_event_maker','provider_taker_equals_transaction_from','event_maker_matches_direct_wallet','provider_taker_is_exchange']}}
    summary={'at':datetime.now(timezone.utc).isoformat(),'provider_rows':len(rows),'unique_event_matches':len(matches),
             'distinct_matched_events':len({(r['block_hash'],r['transaction_hash'],r['log_index']) for r in matches}),
             'transactions':len(receipts),'successful_receipts':sum(r['status']=='0x1' for r in receipts.values()),
             'matched_removed_true':sum(r['removed'] is True for r in matches),'by_id_shape':group,
             'previously_ambiguous_resolved':sum(r['previously_ambiguous'] for r in matches),
             'previously_ambiguous_log_indices':sorted(r['log_index'] for r in matches if r['previously_ambiguous']),
             'maximum_price_error':str(max(Decimal(r['price_error']) for r in matches)),
             'address_code_check':'Historical eth_getCode rejected HTTP403; zero successful code checks; no EOA/router classification made.',
             'join_rule':'tx/orderHash suffix when present; otherwise exchange-facing taker-order event; exact token/side/quantity and rational-price error below1e-9; six-decimal amount scaling. Exploratory sampled mapping only.',
             'limitations':['Receipt lookup is retrospective and cannot create historical decision-time availability.',
                            'One RPC node; no independent chain-finality or reorg-history certification.',
                            '52unique order-fill events need not equal52independent market executions; match legs can represent both counterparties.',
                            'General provider ID/accounting contract remains undocumented; no production mapper changed.',
                            'On-chain settlement order is not necessarily off-chain matching or local arrival order.'],
             'models_scored':False,'labels_computed':False,'predictive_admissions':0}
    (OUT/'row_mapping.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
    write(OUT/'report.json',summary)
    sources=[{'url':'https://docs.polymarket.com/resources/contracts','supports':'Polygon137 and CTF exchange addresses'},
             {'url':'https://github.com/Polymarket/ctf-exchange-v2/blob/main/src/exchange/interfaces/ITrading.sol','local_capture':str((CHAIN/'ITrading.sol').relative_to(ROOT)),'supports':'OrderFilled indexed orderHash/maker/taker and amount layout'},
             {'url':'https://github.com/Polymarket/ctf-exchange-v2/blob/main/src/exchange/mixins/Trading.sol','local_capture':str((CHAIN/'Trading.sol').relative_to(ROOT)),'supports':'Taker-order fill event sets maker to participant and taker to exchange; maker-order event uses counterparty'},
             {'url':'https://docs.polymarket.com/api-reference/feeds/list-trades','supports':'taker_only false includes maker rows'},
             {'url':'https://ethereum.org/developers/docs/transactions/','supports':'Outer signed transaction sender differs from nested call sender'},
             {'url':'https://docs.polygon.technology/pos/reference/rpc-endpoints','supports':'Documented public Polygon RPC options'}]
    write(OUT/'sources.json',sources)
    local=json.loads((LOCAL/'report.json').read_text())
    md=f'''# EventX — results of the four source hypotheses

23 October 2026. Local diagnostics plus a bounded public Polygon receipt lookup.

## Main result

**All52sampled provider records now map uniquely to52distinct on-chain order-fill events across29successful transactions.** This resolves the four ambiguous records in this sample. It does not establish52independent executions or authorize changing the model's input definition.

The mapping required exact token, side and quantity, plus a rational-price tolerance of1e-9. Maximum observed price error was{summary['maximum_price_error']}. This is an exploratory compatibility check; production features and frozen data remain unchanged. Receipt acquisition happened later and cannot be used as earlier decision-time availability.

## 1. Transaction-level IDs, multi-hop aggregation, or retries

The four ambiguous provider rows all belong to transaction `0x31bdac056198a0d7eb6e7e0df4d41611d04bb91a582348530153f1576776662b`. Their IDs contain different suffixes. Each suffix matches an on-chain `orderHash`; the four records resolve to log indices **564,566,568,576**. They are two100-token and two105-token fills. The identical economic candidates were different orders with the same amounts, price and wallet.

Summing each pair yields200or210tokens, twice the corresponding provider row. Thus the proposed aggregation-sum explanation does not fit these four records. The receipt status is successful; the candidates share one transaction, not two competing transaction hashes. No evidence of retries or reorg duplication was found here; reorg history was not independently checked.

Across the full sample,36IDs are `transactionHash:orderHash`;16are bare transaction hashes. All36suffixes match exactly. The16bare IDs each map uniquely in this sample to an exchange-facing taker-order fill. Bare transaction hashes are not guaranteed unique fill IDs in other transactions.

## 2. The63missing taker-side rows

The records span **112.77–17,029.77seconds** before the provider response, approximately1.88minutes–4.73hours. Their distances from the common window end fall in five hourly bins:12,16,19,9,7rows from newest to oldest. **39of63are older than the latest provider trade in the same market. All63use tokens also present in the provider snapshot; none of their transaction hashes appears among that snapshot's provider IDs.** Sizes span0.31–9,161tokens.

The63records occur in four control markets, with7,6,5and45records respectively. This argues against a simple omitted-token catalog, tiny-size cutoff, or single advancing ingestion watermark as a complete explanation. It does not prove any particular alternative: selective indexing, uneven lag, filtering or source outages remain possible. No pool identifier exists in these schemas; these are CLOB outcome-token records, so an AMM pool grouping should not be invented.

We have not re-fetched the provider's exact historical windows after a longer delay. Such a bounded repeat request would distinguish later recovery from persistent omissions, while preserving the original availability clocks.

## 3. Provider taker versus direct proxy wallet

The receipt evidence supports **two different field conventions**:

|Provider ID shape|Rows|Provider `taker` equals|Direct `proxy_wallet` equals|
|---|---:|---|---|
|transactionHash:orderHash|36|On-chain event `taker` in36/36|Event `maker` in36/36|
|Bare transaction hash|16|On-chain event `maker` in16/16|Event `maker` in16/16|

This exactly explains the earlier16/52wallet agreement. In13of the36suffixed records, the provider taker is the exchange itself. The official [exchange implementation](https://github.com/Polymarket/ctf-exchange-v2/blob/main/src/exchange/mixins/Trading.sol) explicitly emits the taker-order participant as `maker` and the exchange address as `taker`. The observed exchange addresses are listed in [Polymarket's contracts documentation](https://docs.polymarket.com/resources/contracts).

None of the52provider taker values equals the outer transaction sender in the fetched receipts. The proposed `tx.from` router explanation is therefore not supported for this sample. More generally, an outer transaction sender and a nested contract caller are different concepts; code presence alone does not prove routing or wallet-resolution semantics. Smart wallets and delegated accounts also make a simple contract-versus-EOA split insufficient.

The public node rejected the first historical `eth_getCode` request withHTTP403. The probe stopped; **zero address-code checks succeeded**. We make no contract/EOA classification from that failed request.

## 4. Same-second ordering

Neither captured trade schema supplies block number, transaction index or log index. The receipt join now provides these for all52sampled provider rows. Use chain ID, block hash, transaction hash and log index to identify the sampled events; block number/transaction index/log index provide settlement order within the observed canonical chain view.

Of nine conflicting-price YES-second groups in the direct snapshot, seven have monotonic returned price sequences and two do not. **Neither result proves or disproves execution order.** Prices can reverse, and an API can sort economically unrelated rows into a monotonic sequence. On-chain settlement order also need not equal CLOB matching order or local receipt order.

The provider request should ask for event identifiers, exchange/order role, block hash/number, transaction/log indices, reorg handling, and first-ingestion timestamps. If the study needs matching order, request a documented matching-engine sequence as well.

## What is now resolved and what remains

- Resolved in this sample: the four ambiguous rows, the meaning of36ID suffixes, and the16/52wallet mismatch pattern.
- Remaining: general accounting guarantees, the63missing records, completeness/late-arrival behavior, and the mapping from order-fill events to the historical model's observation convention.
- Next local diagnostic: repeat the same four provider windows after the longer delay and compare exact transaction/order identities, preserving late retrieval as late availability.
- Continue the scheduled local source rehearsal. Keep the model fixed and do not promote this diagnostic to prospective eligibility.

## Evidence and integrity

`data/v7/source_hypotheses_20261023/` contains timestamp, amount, ID and schema checks.
`data/v7/scoped_chain_20261023/c8c3fe64457e419989135e831b06ee07/` contains29receipt summaries,114allowlisted order-fill logs, the exact official source snapshots and request receipts. Unrelated receipt logs were discarded without economic decoding; full response hashes were recorded. All29receipts have status1. Only the44allowlisted V7tokens were decoded; no broad chain scan or protected evaluation was performed.

The initial sandbox connection failure is preserved separately at `data/v7/scoped_chain_20261023/9e233ea9bdcb42eaa70d6eb7e501cd73/`. The network probe is marked **partial failure**, because the address-code stage was rejected. Successful receipt evidence remains usable with that limitation. No finality certification, model scoring, labels, tests, external messages or source-rule promotion occurred.
'''
    public=ROOT/'EVENTX_SOURCE_HYPOTHESES_RESULTS_20261023.md';public.write_text(md);(OUT/'REPORT.md').write_text(md)
    files=list(OUT.iterdir())+[public,Path(__file__).resolve()]+[p/'manifest.json' for p in [LOCAL,CHAIN,FAILED]]
    write(OUT/'manifest.json',{'files':{str(p.relative_to(ROOT)):sha(p) for p in files}})
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
