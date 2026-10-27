# EventX V5 family/control review and V4 health

Reviewed 2026-09-09. No new development labels, sealed V4 payloads, outcomes,
predictions or performance metrics were opened. No collector restarted.

## Family review result

Structural triage covered all **1,230 candidate Kalshi venue-event groups** in the
4,651-market staging queue. This is not 1,230 complete manual semantic approvals.
Retained market identities and YES/NO subtitles in the review artifact.

| Finding | Count | Decision |
|---|---:|---|
| Missing Polymarket event membership | 819 markets | Recover event links; no singleton fallback |
| Repeated generic questions | 138 groups | Preserve contract subtitles and settlement semantics |
| Multi-leg venue events | 194 groups | Resolve component graph or exclude before labels |
| World Cup dependency candidates | 297 groups | Review fixtures, stages and whole-tournament bridges |
| Golf tournament/season candidates | 11 groups | Merge shared tournament scopes; check season bridges |

Flags overlap; counts must not be added as disjoint exclusions.

Two concrete split-isolation merge recommendations cover **189 contracts**:

- The Open Championship 2026: winner, top-10, top-20, first-round leader and
  holes-in-one groups belong together within the reviewed scope (125 contracts).
- U.S. Open 2026: winner, top-5, top-10, top-20 and make-cut groups belong together
  within the reviewed scope (64 contracts).

These are lower-bound same-tournament dependencies, not claims that all contract
outcomes are logically equivalent. The four annual-major winner contracts and
multi-leg contracts may bridge tournament scopes; cross-venue duplicates are not
resolved. Therefore **zero final independent event families are certified**.

Concrete identity failure: the 45 `KXWORLDCUPHALFTIME-26` contracts share the generic
question “Who will perform at the 2026 FIFA World Cup final halftime show?” but have
different YES subtitles, such as Alicia Keys, Bad Bunny and Beyoncé. Association
and family review cannot use the generic title alone. A change to association inputs
requires a versioned adapter/audit before new labels, never silent rewriting of V4.

Evidence: `data/v5/family_review_20260909/{report.json,group_triage.jsonl,
missing_membership.jsonl,scoped_merges.json,manifest.json}`. Source staging remains
unchanged and non-admissible. Review generator uses cached metadata only.

## Finalized method decisions

The controlling new document is `MATCHED_CONTROLS_AND_EVALUATION_V1.md`. It specifies
the exact 22-column content versus timing-matched matrices, 24-combination residual
grid, nested base-C selection, source/row/family isolation, inference hierarchy,
LL/Brier/subgroup margins, missing/undefined handling and hard stopping rule.

Primary attribution is now **V5-R versus C-timing-matched**, with identical age/count
features and three content-free timing-polynomial slots replacing the three semantic
slots. The simpler context/timing arms are diagnostics, not models available for
post-result selection. Equal width is nominal capacity matching, not guaranteed equal
effective complexity. The claim remains joint relevance–novelty, not novelty alone.

Added the independent label-free matrix builder and five synthetic tests. **37/37**
combined contract, corrected-pipeline, algorithm-audit, source-readiness and recovery
tests passed. The full production evaluator and source adapter are not implemented
by these tests. Concrete dates/cohort/splits, source certification and synthetic
bootstrap coverage validation remain prerequisites to a complete executable freeze.

## V4 collector health

Checked **2026-09-09 14:37:30 UTC** using process metadata, state, receipt metadata,
file existence and hashes of frozen non-holdout artifacts only:

- Collector PID **72506** and its caffeinate child **72517** are alive.
- **10 news days** (Aug 30–Sep 8) and **3 trade days** (Sep 6–8) checkpointed.
- All expected **10 news receipts and 30 trade-batch receipts** exist with payload
  and SQL files. No closed UTC day is pending; Sep 9 is still open.
- All **15 frozen V4 implementation hashes** match. Collector code matches launch.
- Consumption receipt, examples, evaluation attempt, predictions and result files
  checked for existence only: all absent.

The checkpoint retains `BrokenPipeError: [Errno 32] Broken pipe` at
`2026-09-09T13:00:49.203643Z`, immediately after its successful checkpoint at
`2026-09-09T13:00:49.202187Z`. Code inspection shows flushed progress output occurs
after durable state writes; process file descriptors 1/2 are pipes. This is consistent
with a lost logging reader rather than lost completed partitions, but no traceback
was inspected to prove the exact origin. **Health is caught-up/alive with a logging
warning, not unqualified green.** No logging or process mutation was performed.

Next operational check: after Sep 10 00:00 UTC, confirm both Sep 9 partitions advance.
If they fail to advance, diagnose and use an authorized, checkpoint-preserving restart
with durable stdout/stderr files. Do not change frozen feature/evaluation code.

Receipt presence is not source completeness or a fresh payload-integrity audit. The
frozen post-close collection gate must still run in its prescribed order. Earlier
Sep 5 HTTP-500 backlog is recovered; this does not establish that all Lumid retrieval
routes or the separate V5 provenance queries now work.

Evidence: `data/v4/health_checks/20260909T143730Z/report.json`.

## Next action

Recover projected membership/version evidence and reconcile news completeness; then
finish the dependency components, integrate the matched matrices and evaluator,
publish label-blind source/split/power validation and freeze one executable V5-R test.
Do not open new labels or promote a model while these gates remain unresolved.
