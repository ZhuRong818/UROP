# V6 scoped historical-source evidence request

Date: 27 September 2026. **Prepared locally; NOT SENT.** This addendum scopes the earlier `eventx/release/v5/LUMID_CERTIFICATION_REQUEST_20260910.md` to the actual V6 development bottleneck. It contains no credentials or outcome/price requests. The JSON attachment is `data/v6/context_development_review_20260927/provider_scope.json`.

## Evidence requested

1. **Article content versions.** For each article ID/hash below, identify the field representing first availability of the exact headline/summary bytes, whether an update changes that clock, and the archived version or authoritative immutability/lineage guarantee covering these fields and dates. Distinguish publication, ingest, revision and export time. The user-relayed administrator assurance is provisionally accepted; the production field mapping is still required.
2. **Contract versions and trading status.** For each contract below, provide point-in-time question, YES/NO subtitle, rules, outcome/token mapping, open/suspend/close status, and valid/available intervals. Current `ingest_ts` and nominal `end_date` alone cannot certify earlier text or tradability. An archived payload, version ID with validity lineage, or field-specific documented immutability guarantee would be acceptable evidence.
3. **Feed/run completeness.** For the nine listed source runs, provide requested windows, committed-row/page receipts, retry/successor IDs, retention/upsert semantics, and unresolved gaps for the declared feed universe. Five are marked failed in the local run inventory; that status does not invalidate retained rows but leaves completeness unknown. Include source-day coverage for the selected development windows, including zero-export days.
4. **If proof is unavailable.** State which fields/time ranges cannot be certified. We will keep historical admission closed for them and use a separately versioned prospective capture rather than infer past content from a current row.

The scope is opened development `[2026-05-17,2026-07-22)` UTC. It cannot become untouched confirmation by certification. Protected V4 data and market outcomes are outside this request.

## Article scope

| Article ID | Source run ID | Run status | Content SHA-256 | Source clock UTC |
| --- | --- | --- | --- | --- |
| `102500031` | `510bc928-4d72-466b-be04-00532d6051c2` | ok | `dd9a1f96292c7708397d592107fa9f35355781a012c69fae722617cf7c1b1234` | `2026-05-23T15:19:29.435984Z` |
| `152232532` | `eb87b497-a8b2-4d98-a763-5269bf7e5c1c` | ok | `661974d4833f6c938f3dbb1ffc6edf177180e23fa08a7c6834d3a68687cd924d` | `2026-05-26T08:15:07.502489Z` |
| `166357183` | `d8bcb0d0-be28-4a0a-920c-d6087a07e5a8` | failed | `89e61eccf4f7474b82e8797d2c19f27e4287a0e081b31a882bc31659f4a65d9d` | `2026-05-30T13:52:00.659674Z` |
| `168034724` | `c40c9e49-4a6a-44d1-a0d9-43ca033d21ae` | failed | `a6bdfd7961e178114fbb4d0b451a089f5f8e30c1fb4dc11120dfba206b7a4183` | `2026-06-01T16:22:01.898330Z` |
| `189518836` | `fd734424-86f2-4d65-a67c-868d6f80730a` | failed | `8ad77a881ecef9b3d017ef4eee201ef1038b438174f55c59e5d7ded987ebe111` | `2026-06-23T18:52:01.311813Z` |
| `193693829` | `377266b5-b120-47f1-88fc-de86ee87462b` | ok | `87aae8a6f3e5197942b1300c9cff98092bc97ed03e9c02c00525e05e252bb9cb` | `2026-06-28T06:17:55.446337Z` |
| `197137081` | `592ebc42-79ad-4b33-af2d-628b5edb6167` | failed | `2ecbdc0cac2dc0dad3d5db144742d935d143ea2f717e51df4a03279428ab0469` | `2026-06-30T04:52:01.676592Z` |
| `201756152` | `86c568d4-f947-43e2-950b-8cf740690a9e` | failed | `c4388f470e8e1170ba0df5f17b9e57db1ed0d0d7a76b1787c2e9451168e8d207` | `2026-07-02T18:37:01.281842Z` |
| `211869183` | `ad764123-d034-44db-aa25-a156ab855fe2` | ok | `82cf2e0bfd19e76e2eb7d84ec068203d853c48865a966942b3f74daf916a30d9` | `2026-07-09T14:59:45.841566Z` |

## Contract scope

| Contract ID | Venue | Cached snapshot ingest UTC | Cached rule ingest UTC |
| --- | --- | --- | --- |
| `kalshi:contract:KXWC3RDPLACE-26-MEX` | kalshi | `2026-07-06T16:02:59.894847Z` | `2026-07-06T16:02:59.894847Z` |
| `polymarket:contract:0x0c4cd2055d6ea89354ffddc55d6dbcef9355748112ea952fc925f3db6a5c457f` | polymarket | `2026-05-22T08:06:20.099224Z` | `2026-05-22T08:06:20.099224Z` |
| `polymarket:contract:0x38903ef70b7d9ee41ea22ef2aec6287e4e6c77ec8702ca741e37d5c5df090a4d` | polymarket | `2026-07-01T16:45:14.926074Z` | `2026-07-01T16:45:14.926074Z` |
| `polymarket:contract:0x3910cb53f972d00c049ad674c1b183b375bd56786eb4c085ea217f84defdd1ca` | polymarket | `2026-06-02T15:00:21.779468Z` | `2026-06-02T15:00:21.779468Z` |
| `polymarket:contract:0x58078283e2356f9b9537b42e7479d7785b83bcd6f18002de8a2526c499eda837` | polymarket | `2026-05-22T08:06:21.710273Z` | `2026-05-22T08:06:21.710273Z` |
| `polymarket:contract:0x5ccfe1b69a582d2985db08a8481a0d74c314b1fce9b4711ae2efb2c6467fe6aa` | polymarket | `2026-05-22T08:06:20.099224Z` | `2026-05-22T08:06:20.099224Z` |
| `polymarket:contract:0x75a50ed92507226816900d6da63984b4db752ad3a3f73e691514416cc5ccd980` | polymarket | `2026-06-04T15:15:21.399648Z` | `2026-06-04T15:15:21.399648Z` |
| `polymarket:contract:0x84edef36bded182da6a395ac6c785dba8f3e09b6c5ad041385b2042536cbef25` | polymarket | `2026-05-22T08:06:20.099224Z` | `2026-05-22T08:06:20.099224Z` |
| `polymarket:contract:0xa0f4c4924ea1a8b410b4ce821c2a9955fad21a1b19bdcfde90816732278b3dd5` | polymarket | `2026-05-22T08:06:20.831403Z` | `2026-05-22T08:06:20.831403Z` |
| `polymarket:contract:0xbb57ccf5853a85487bc3d83d04d669310d28c6c810758953b9d9b91d1aee89d2` | polymarket | `2026-05-22T08:06:21.298187Z` | `2026-05-22T08:06:21.298187Z` |
| `polymarket:contract:0xbe20fcfd54937c2a48a7b8521ca349e6a2c4373566328ebb950a8c35ab1be3d9` | polymarket | `2026-07-01T16:45:14.926074Z` | `2026-07-01T16:45:14.926074Z` |
| `polymarket:contract:0xc9c9790c8f26dd9c8cabae9dd76be37aa86a6ded7de660e1da9d19324cf618d4` | polymarket | `2026-07-01T16:45:14.926074Z` | `2026-07-01T16:45:14.926074Z` |
| `polymarket:contract:0xce6f2c7437b15b808a6be3ea61fc125077e35ce7cc55b66fdbf15f7ce22493ea` | polymarket | `2026-06-02T16:45:15.711020Z` | `2026-06-02T16:45:15.711020Z` |
| `polymarket:contract:0xdaa4866bae18be58c5a79d2aeeffd035ec78f1bb49dbd88f72993997778a990f` | polymarket | `2026-05-22T08:06:22.104914Z` | `2026-05-22T08:06:22.104914Z` |
| `polymarket:contract:0xe284a52d608552290b056def0a62e1914b3ebe316407504f56f6361fafc68358` | polymarket | `2026-07-01T16:45:14.926074Z` | `2026-07-01T16:45:14.926074Z` |

## Local catalog check

On 27 September, three ad hoc authenticated read-only catalog GETs returned HTTP 200 and exposed `ingest_ts` plus current descriptive/status fields, without visible version/validity/revision columns. A separately receipted repeat at `data/v6/source_schema_probe_20260927/` returned HTTP 502 for all three GETs; its field counts are **unobserved**, and the report conclusion implying field absence is invalid for that failed repeat. Neither observation rules out a private archive or undocumented immutability guarantee. No row-level protected data were requested.

This is a prepared source question and attachment; no provider message has been sent.
