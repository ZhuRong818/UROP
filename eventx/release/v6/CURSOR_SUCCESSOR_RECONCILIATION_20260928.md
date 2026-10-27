# V6 endpoint cursor and successor-run check

Date: 28 September 2026. This is a prereceipted read-only check on EventX's configured `https://lum.id/findata` against the five opened-development failed `finnhub:company-news` runs. The exact SQL, prequery receipt, result, script and hashes are in `data/v6/cursor_successor_probe_20260928/`.

## Endpoint cursor

`provenance.scrape_cursor` returned one row for `finnhub:company-news`, with `scope_key=''`. Its current `last_run_id` is `fd8e77f3-7814-46b5-9a5a-54da94a26545`, `last_data_date=2026-09-28T12:37:40Z`, `last_run_at=2026-09-28T13:10:24.970190Z`, `next_action=delta`, and `retry_count=0`. This confirms that the earlier NVDA/MSTR substring lookup was aimed at nonexistent per-symbol keys. It also conflicts with the relayed assertion that the only current cursor ended on 5 June. The exact endpoint on EventX's API has since advanced; the other analyst's API/deployment, role, filter and query time remain to be aligned. The cursor is overwritten state and does not prove its state at any earlier decision time.

## First completed successor within seven days

| Failed run | First subsequent `ok`/`partial` run | Completion UTC | Requested `to` | Status / inserted / failed |
| --- | --- | --- | --- | --- |
| `d8bcb0d0…` (30 May) | `78ae76ec…` | 30 May 20:39:52 | 31 May | ok / 34 / 0 |
| `c40c9e49…` (1 June) | `05f950df…` | 5 June 08:10:00 | 5 June | partial / 285 / 1 |
| `fd734424…` (23 June) | none within seven days | — | — | — |
| `592ebc42…` (30 June) | `c4c5b4aa…` | 6 July 18:02:33 | 7 July | ok / 1,153 / 0 |
| `86c568d4…` (2 July) | `c4c5b4aa…` | 6 July 18:02:33 | 7 July | ok / 1,153 / 0 |

The query selects the first later completed endpoint run within seven days; it is **not** a per-symbol or per-window coverage check. All four observed successors completed after the failed run's derived `available_at` decision time. Different `args.to` values and aggregate status/counts do not establish that the failed scope/window was retried completely. The missing June successor means only none matched this bounded query, not that no later run exists. No historical cursor transition, clean completed zero receipt, first client visibility, or market active-status history was recovered.

## Decision and next evidence

Keep all five failed-run windows unknown at the proposed decisions. Ask Lumid for append-only cursor or per-window receipts, including requested from/to, scopes/symbols, pages and failures, completion and cursor advance **before each decision time**. Confirm the alternate analyst's exact API/deployment/role/query and align with the two direct EventX SQL results. Separately obtain market status/version history. No link, source day or predictive model is admitted; V6 remains at 0/8,844 certified predictive contract-days.

“JEV” has no definition in the searched EventX repository. Its prospective role in model analysis requires the model name or documentation. Any trial would use opened development, versioned inputs and a separate evaluation; source and audit gates remain unchanged.
