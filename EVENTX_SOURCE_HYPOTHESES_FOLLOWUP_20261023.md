# EventX source hypotheses — completed follow-up

23 October 2026. Supersedes the unresolved questions in the earlier review package where the evidence below applies. Original frozen reports remain preserved.

## What the checks establish

1. **Four ambiguous records resolved.** All belong to one successful CTF exchange transaction. Different provider ID suffixes match different on-chain order hashes; log indices564,566,568,576 separate the equal-sized orders. Summing the duplicate-looking candidates doubles the provider amounts. This sample does not support multi-hop aggregation or competing retry transactions as their explanation.
2. **Partial delayed recovery established.** A repeat of the same four historical windows approximately14.68hours after their endpoints returned138provider rows, versus45originally. Exact record comparison preserves45old records, adds93, and leaves0old records non-identical/absent. Of the63previously missing taker-side rows, **16now have matching transaction/token/time/side/size/rounded-price records;47remain absent.** Late retrieval is not backdated availability. A single repeat does not identify when the records arrived or their upstream cause.
3. **The wallet mismatch is explained by mixed field semantics.**36provider IDs are `transactionHash:orderHash`;their taker fields equal the on-chain event taker.16bare IDs use the event maker instead. Direct API wallets match the event maker for52/52rows;provider taker equals transaction sender for0/52. The official exchange implementation uses these different order roles. A generic router or call-graph join would not address the observed schema mixture.
4. **Chain event ordering is now available for the sampled52rows.** All52map uniquely to52distinct OrderFilled events across29successful transactions. These are order-level event identities,not52independent economic trades. Block/transaction/log indices order settlement,not necessarily CLOB matching or information arrival. Seven of nine price sequences are monotonic;this does not validate API row order.

## Delayed recovery by control market

|Control market|Originally missing|Recovered later|Still absent|
|---|---:|---:|---:|
|Will Bitcoin dip to $80,000 October 19-25?|45|0|45|
|Will Bitcoin dip to $74,000 October 19-25?|6|6|0|
|Will Bitcoin reach $92,000 October 19-25?|5|5|0|
|Will Bitcoin reach $90,000 October 19-25?|7|5|2|

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
