# User-attested submission correction

On17 September2026 the user clarified that the three changed family decisions in
`adjudication_packet_completed_with_evidence_refs.jsonl` correct submission mistakes,
not a substantive second adjudication. Accept this provenance clarification as a
user attestation; it is not independent verification of the adjudicator's process.
Retain both historical receipts and count this as one adjudication round.

Corrected submitted labels:3 family must-link,3 no-direct-link,2 distinct-story.
The three corrections concern boundary-9a97498f3b4f266b,
boundary-0f93b14dd34581c8 and boundary-881c4d6f8e86e1ba.
No resampling, graph release, new evidence-based re-adjudication or final audit is
authorized by correcting submission provenance. In particular, missing rules do
not prove independence; the submitted negative labels retain that limitation.

## Story citation bookkeeping

Recomputed SHA256 using the original pipeline's exact encoding:
`json.dumps({"headline": ..., "summary": ...}, sort_keys=True).encode()`.
All four supplied article texts match their embedded original content hashes.
The new citation strings, not the embedded texts, disagree with those hashes.

| Article ID | Verified original content SHA256 |
|---|---|
| 174526285 | 9ffdc7b76e796a631134d9435309eadd200e688eda9b4906931da7f384195ba1 |
| 203505251 | f2783717084db556e8670d4fe7eee633e14fa86ce22e5dc9d1c3ddb1fe0e803b |
| 197127839 | 4b7066a7e2e3a87c9e5eebcf3ff78f8505b0d8d681d0fc36d0cc6a424ce7ff69 |
| 206949562 | b7c5d8b5208e0ef03f37a8022bf7def379549963665047a7af7e63ef89586ddc |

Use this separate correction record for citation reconciliation; never overwrite
submitted/frozen artifacts. This mechanical check neither changes story labels nor
asserts their semantic accuracy. No additional human judgment is requested for these
four hash strings. Remaining review work is the fixed relevance A/B responses;
the last validated copies contained40 blank labels each. No final audit run here.
