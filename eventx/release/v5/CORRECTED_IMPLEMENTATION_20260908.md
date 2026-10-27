# V5 timing, cross-fitting and fixed-offset repairs

Status: **reference implementation completed and synthetic-tested; not a V5-R
research result, candidate freeze or validated replacement dataset.**

The three requested repair steps now live in the separate `eventx/v5_corrected/`
package. Existing discovery results and frozen V4 code were not rewritten.

## 1. Point-in-time feature construction

`point_in_time.py` consumes immutable article versions, versioned market metadata
and causal market-input rows, rather than the previously materialized discovery
semantic arrays.

- All time fields use integer UTC microseconds. Article availability is the maximum
  of publication, source first-seen and availability of the exact content version.
- Metadata joins require both availability at the decision and validity in the
  half-open `[valid_from, valid_until)` interval. Unknown/closed market metadata
  fails row admission. An unknown scheduled terminal is encoded as zero plus an
  explicit unknown flag; a later snapshot cannot fill it retrospectively.
- Association requires eligible metadata known when the article arrived. It cannot
  borrow a later question/category or a later-created market. Associations are not
  carried across changed question semantics.
- The TF-IDF/LSA encoder retains the inherited representation settings by default
  but is fitted on a **pre-window warm-up corpus, within each training-family scope**.
  Every scored row follows that cutoff by at least 30 minutes. Insufficient warm-up
  support fails; the implementation never silently reduces the semantic dimension.
- Relevance uses clipped question/article cosine. Novelty retains the inherited
  last-20-prior-associated-articles/seven-day definition. Recent features use exactly
  `(t-30m, t]`, without diffusion or a tuned relevance gate.
- Online deduplication retains the first available immutable content version for a
  supplied identity. Later revisions do not rewrite earlier features. The upstream
  adapter must establish the identity rule and exact-version evidence.
- Article-count clipping is fitted only on training rows. This implementation retains
  an all-training-row p99 cap; changing to an exposed-only cap requires a protocol
  decision before labels, not a silent repair.
- Missing coverage, future market inputs, missing family verification, duplicate
  decisions and inconsistent market-to-family mappings fail explicitly.

The warm-up policy is an implementation contract, not an already approved V5-R
preregistration amendment. Its actual dates, corpus and support must be audited and
frozen before a research run.

## 2. Nested cross-fitting

`splits.py` and `pipeline.py` implement three separate levels:

1. Outer evaluation families and their earlier observations are excluded from all
   fitting and tuning.
2. Each inner tuning partition builds its own stack using only its training scope.
3. Each residual training stack generates fresh base OOF predictions inside that
   scope, with an additional held-family/forward split.

Every split requires `training_label_end < validation_start`; for the 30-minute
target this excludes rows whose horizon touches or crosses the boundary. Validation
labels must also finish strictly before the declared fold end. Unknown families do
not fall back to contract hashes. Overlapping OOF/tuning validation rows fail.

Feature preprocessing is refitted at each training scope. The residual learner sees
only honest base OOF probabilities. Initial rows lacking OOF coverage are recorded and
excluded from residual training, never filled with in-sample predictions. The deployment
base is separately fitted on all permitted training rows. Its fitted probabilities
never replace the OOF scores used to train the residual expert.

The ledger records parent/train/validation IDs, family scopes, latest training label
end, feature provenance, OOF exclusions and solver convergence. Regularization and
shrinkage selection use only the supplied inner-fold grid. The market-model factory
must be fixed beforehand; this repair does not authorize another broad model search.

Linear, explicitly selected-column spline and shallow-tree factories are available.
Trees retain depth three, seven leaves and disabled random early stopping. **No tree
was promoted or fitted on real research data in this task.**

## 3. Actual fixed-offset learner

`offset.py` minimizes, on exposed training rows only,

```text
mean[log(1 + exp(offset + X beta + intercept))
     - y * (offset + X beta + intercept)]
  + L1 * ||beta||_1 + L2 / 2 * ||beta||_2^2

offset = logit(p0_OOF)
```

The offset coefficient is fixed at one; it is not an ordinary classifier subsequently
blended with B0. The correction intercept is unpenalized. Scaling is fitted only on
exposed rows. Accelerated proximal gradient handles L1 soft thresholding and checks
the proximal first-order optimality residual. Failure to converge raises an error.
Single-class exposed training partitions fail rather than invent a constant fit.
No exposed training rows produce a documented zero-correction expert.

Prediction is `sigmoid(logit(p0) + kappa * correction)` only on exposed rows. All
other probabilities are copied directly from B0, with bitwise equality. Shrinkage
zero also returns B0 exactly. Invalid/nonfinite probabilities fail explicitly.

## Validation evidence

Published evidence: `data/v5/corrected_implementation_20260908/`:

- `report.json`: **25 tests passed**, zero failures/errors/skips; also 13 legacy
  baseline/residual checks passed.
- `tests.txt`: named regression-test output.
- `fit_ledger.json`: complete synthetic nested-fitting provenance.
- `manifest.json`: source/output hashes; implementation evidence, not a research freeze.

The end-to-end fixture uses 320 synthetic rows. Its final outer partition contains
16 rows, four exposed; the residual trains on 72 honest OOF rows, with 120 training
warm-up rows explicitly excluded for lack of OOF scores. The optimizer converged
with proximal residual `6.050060605299212e-08`. These counts and the stored synthetic
tuning losses are software tests, **not EventX results**.

Tests cover future append/revision invariance, content backfills, unavailable metadata,
exact news-window boundaries, semantic family/time isolation, all-level purging,
outer-label perturbation invariance, OOF score retention, analytic gradients, known
synthetic correction recovery, L1 suppression, convergence failure and exact no-news
equality. All **15 V4 implementation-manifest artifacts remain hash-identical**.
No real example, protected holdout label or protected prediction file was read.
Ruff was unavailable in the existing environment; lint was not run.

Run the tests without publishing anything:

```bash
.venv/bin/python -m unittest eventx.tasks.test_v5_corrected_pipeline \
  eventx.tasks.test_algorithm_audit -v
```

To publish another synthetic validation run, use a new output directory; the runner
refuses to overwrite existing evidence:

```bash
.venv/bin/python -m eventx.tasks.validate_v5_corrected_implementation \
  --output data/v5/corrected_implementation_next_check
```

## Still required before real-data use

This is an integrated reference adapter/trainer, not a scalable warehouse export or
the final research evaluator. It does not reconstruct executed-trade price inputs,
infer missing historical snapshots, generate labels, manufacture family mappings or
prove source completeness from a boolean field.

1. Build an evidence-backed event-family mapping and a new versioned as-of dataset.
   Upstream manifests must substantiate each declared market-input availability,
   coverage flag, article version and warm-up family assignment. The old arrays are
   not repaired merely by installing these modules.
2. Freeze the actual semantic warm-up, feature column order, nonlinear baseline
   columns, fold schedule, tuning grids and minimum support rules. The small fixture
   uses a two-dimensional encoder only for testing; it does not change the proposed
   research representation's 64 components.
3. Finish the timing/count-control and matched-capacity specification. The adapter
   can emit context, timing and news bundles, but this does not automatically make
   their capacities equal or isolate novelty from relevance. No confirmatory claim
   or control selection is made here.
4. Pass label-blind feasibility gates and reserve an untouched V5 interval disjoint
   from protected V4. No new empirical news-effect estimate was produced.

The next task is therefore **data/provenance rematerialization and readiness auditing**,
not a rerun of a consumed holdout or further outcome-driven feature search.
