# Automated subject/relation diagnosis — 17 September

## Completed, without another annotation round

Used the same fixed 160 opened-development articles and cached 4,651 contract cards.
Earlier artifacts remain unchanged. No reviewer responses, reserved articles,
holdout outcomes, model fits or network fetches were used. Diagnostic categories
are program outputs, not human ground truth.

## Why the previous 155 pairs failed

| Failure | Pairs |
|---|---:|
| Unsupported proposition adapter | 65 |
| Extension subject without bound relation | 37 |
| Subject without bound predicate | 36 |
| Required primary subject absent | 17 |

None reached a period-check failure. Blanket relaxation of date requirements is
therefore unjustified as a fix for this set. Code inspection confirms that some
existing adapters require literal observation dates/deadlines. This can be too
restrictive for incremental-information links, but changing it must distinguish
event updates from settlement evidence: a current negotiation update need not repeat
a future deadline; an album-sales measurement still needs the correct tracking week.
No temporal/source eligibility restriction was relaxed in this task.

## Uncovered contract inventory

The previous 2,909 cards without subjects comprise these deterministic categories:

- 2,220 unsupported subject structures.
- 398 compound-looking questions requiring leg resolution (a lexical category,
  not a change to the authoritative 397 combo-parent inventory).
- 164 answer identities requiring typed subtitles.
- 127 goal-total questions without fixture identity in the question.

Implemented new extraction forms for named speakers/team changes, golf finish
positions, election victory margins and asset/compute prices. Exact contract quotes
and offsets are retained. No subject is invented for a context-free goal-total
question; no compound question is treated as one entity.

## Fixed development rerun

| Measure | Result |
|---|---:|
| Contracts with extracted subjects | 2,099 |
| Newly covered contracts | 357 |
| Still uncovered | 2,552 |
| Retrieved mention pairs | 508 |
| Context-retained pairs / articles | 180 / 22 |
| Added / removed retained pairs vs previous version | 44 / 19 |
| Background / insufficient evidence | 73 / 107 |
| Uncertified / temporally ineligible | 162 / 18 |
| Direct candidates / predictive admissions | 0 / 0 |

New context checks reject date-only sports-question matches without sports context
and Spotify-question matches without music context. Fewer covered articles can be
appropriate after filtering; neither the added pairs nor the rejected pairs have
been independently validated. All 123 related tests pass, including ten new tests.

## Decision and next step

Retrieval engineering progressed; semantic acceptance remains unimplemented for
many retrieved relations. Do not interpret zero accepted links as a news-null result
or request more bulk annotation. Next build a bounded, evidence-span relation layer
that explicitly distinguishes same-event updates, settlement measurements and mere
entity background, prioritizing the actual unsupported relation groups. Preserve
separate source eligibility and avoid promoting a candidate from co-occurrence alone.
If cached metadata cannot identify the event, classify that as a metadata gap rather
than adding increasingly permissive regexes. Independent accuracy validation remains
necessary before any future association-quality claim.

## Artifacts

- Implementation: `eventx/v6/subject_retrieval_v02.py`
- Tests: `eventx/tasks/test_subject_retrieval_v02.py`
- Runner: `eventx/tasks/diagnose_subject_v02.py` (refuses output overwrite)
- `data/v6/subject_diagnosis_v02_20260917/`: receipt, registry, uncovered inventory,
  all decisions, report and output manifest.
