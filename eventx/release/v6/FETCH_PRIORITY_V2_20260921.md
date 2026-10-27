# Fetch priority v2

Implemented a separate primary-subject fetch planner; existing matchers and frozen
artifacts are unchanged. Same500 development articles,1,648 retrieved pairs:

- 1,048 primary mentions under the bounded question grammar.
- 45 context-only matches, excluded from priority scores.
- 555 unresolved primary identities, excluded rather than guessed.

Ranking counts unique primary-mention article IDs per source event, not contract
variants.93 source-event groups have primary mentions; top40 form the metadata
recovery queue. All member contract IDs are retained. Multi-event/missing-event
cards stay separate. This operational grouping does not certify family independence.

Recovered window status is retained separately. Priority is for metadata recovery,
not an assertion that all articles occurred while contracts traded. Exact name
matching can confuse common names/words and does not bind speaker, claim or event.
These counts are not validated relevance, precision or recall. Zero admissions.

Five new unit tests pass (context, primary, unresolved, conflict, grouping).
Artifacts: `data/v6/fetch_priority_v2_20260921/`, including full ranked groups,
pair-level roles, top40 queue and input/output hashes. No API collection or protected
outcome access in this run.

Next fetch missing descriptive metadata for this corrected event-deduplicated queue,
then verify opening windows and use known article IDs as API positive controls.
