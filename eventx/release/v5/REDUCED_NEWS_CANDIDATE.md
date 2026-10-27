# EventX v5 reduced-news candidate

**Status:** proposed for a new development interval; not tested, preregistered or frozen  
**Prepared:** 2026-09-03  
**Baseline:** direct nonlinear `B0-v5N` development candidate  
**Protected evidence:** the v4 confirmation interval remains untouched

**2026-09-07 audit prerequisite:** this proposal is not ready to freeze. The separate
user-authorized exploratory algorithm audit found historical semantic preprocessing
using later discovery text, terminal metadata without as-of checks, omitted meta-fold
horizon purges, and standalone-expert blending rather than true offset optimization.
Before execution, repair these issues and specify a timing/count control for attributing
relevance–novelty. No new model is promoted and no new-data V5-R test was consumed.
See [ALGORITHM_AUDIT_20260907.md](ALGORITHM_AUDIT_20260907.md).

**2026-09-08 implementation update:** the three timing/cross-fitting/true-offset
repairs now have a separate integrated reference implementation, with 25 passing
regression tests and unchanged V4 hashes. This does **not** rematerialize the legacy
dataset or freeze the new experiment. Verified families, as-of source evidence,
semantic warm-up dates and the matched timing/control contract are still required.
See [CORRECTED_IMPLEMENTATION_20260908.md](CORRECTED_IMPLEMENTATION_20260908.md).

## Purpose

The opened historical mechanism controls found no incremental value from broad
24-hour article volume, quality or lifecycle families after controlling for nonlinear
market state. Repeated fitting on that same interval would increase researcher degrees
of freedom without creating confirmation. This document therefore narrows the next
news hypothesis before a new development interval is opened.

V5-R is a mechanism-identification experiment, not a general model-improvement
exercise. Its question is whether a minimal recent relevance-novelty signal adds
information after nonlinear market state and exposure-conditioned recalibration have
both been controlled.

## Proposed comparison

```text
B0-v5N: direct nonlinear market-only model
V5-R:   B0-v5N logit offset plus a sparse, gated recent-news correction
C5-R:   identical gate and market-context correction, but no news content variables
```

The news claim is eligible only if `V5-R` improves over both `B0-v5N` and `C5-R`.

The architecture of B0-v5N is fixed before new labels are inspected, but its fitted
parameters and inner-fold regularization are learned only from the new development
training partitions. B0-v5N, C5-R and V5-R must be evaluated on identical outer-fold
rows.

## Exposure gate

```text
E30(t) = 1 if at least one valid associated article became conservatively available
         in (t - 30 minutes, t]; otherwise 0.
```

The 30-minute window is fixed from the only opened age band with a positive
relevance/novelty hint. No relevance threshold is used. Missing or censored source
coverage fails the data gate and is never interpreted as no news.

## News variables

The primary candidate contains only:

1. maximum `relevance × novelty` in the 30-minute window;
2. `relevance × novelty` of the most recently available article;
3. minutes since that article became conservatively available;
4. count of valid associated articles in the window, capped at the
   development-frozen 99th percentile and transformed with `log1p`.

One prespecified interaction is permitted:

```text
maximum relevance × novelty  ×  log1p(minutes_to_scheduled_terminal)
```

Publisher diffusion, publisher diversity, semantic clustering and story lifecycle are
excluded from the primary candidate because the opened controls supplied no positive
mechanism evidence. They may be reported only as separately labelled exploratory
analyses after primary evaluation.

## Residual form

```text
p(t) = sigmoid(logit(p_B0-v5N(t)) + E30(t) * kappa * delta(t))
```

`delta` is an elastic-net logistic residual trained only on exposed rows. `kappa` is
selected from a small preregistered grid inside nested training folds. The exact
software invariant is:

```text
E30(t) == 0  =>  p_V5-R(t) == p_B0-v5N(t)
```

## Context-only negative control

`C5-R` uses the same exposure rows, optimizer, cross-fitting, regularization search
and shrinkage search, but only market-context inputs. Its transformed coefficient
budget must equal V5-R's; any additional context basis terms needed for this match are
specified label-blind and frozen before development labels. The permitted inputs are:

- B0-v5N logit and probability;
- recent volatility and activity;
- price age and minutes since latest execution;
- time to scheduled terminal;
- venue and preregistered broad category where supported.

The control prevents conditional nonlinear recalibration from being attributed to
news content.

Because `C5-R` uses the `E30` exposure gate, the three-model comparison has distinct
interpretations:

| Result | Interpretation |
|---|---|
| B0-v5N beats linear B0 | Nonlinear market-state improvement replicates |
| C5-R beats B0-v5N but V5-R does not beat C5-R | News arrival/exposure may matter, but relevance-novelty content does not |
| V5-R beats both B0-v5N and C5-R | Evidence attributable to the prespecified news-content variables |
| V5-R fails either comparison | No news candidate proceeds to confirmation |

## B0-v5N replication gate

Before interpreting the news comparisons, report

```text
Delta_LL_market = LL(linear_B0) - LL(B0-v5N).
```

The proposed replication gate is positive mean improvement with a paired
market/calendar-block bootstrap lower 95% bound above zero. Its exact material-effect
threshold must be set by the label-blind power audit. If B0-v5N fails this gate, report
that failure and do not claim that the nonlinear market benchmark generalized.

The complete B0-v5N, C5-R and V5-R evaluator must nevertheless be frozen before any
new development labels are inspected. “Report B0 first” describes the inferential
hierarchy; it does not authorize looking at B0 results and then changing V5-R.

## News promotion and hard stopping rule

V5-R may proceed from new development to untouched confirmation only if all
preregistered conditions hold, including:

1. `LL(B0-v5N) - LL(V5-R) >= 0.001` nats per row;
2. the paired lower 95% bound for V5-R versus B0-v5N is above zero;
3. the paired lower 95% bound for `LL(C5-R) - LL(V5-R)` is above zero;
4. the frozen Brier non-inferiority and eligible-subgroup material-harm rules pass;
5. every required metric is defined.

If V5-R fails either the nonlinear-baseline comparison or the context-control
attribution comparison, the v5 news branch stops. No news model proceeds to
confirmation.

After such a failure, v5 must not be rescued by extending the window, restoring
diffusion/lifecycle, tuning a relevance cutoff, creating category-specific variants,
adding interactions or changing the semantic representation. Any such hypothesis
requires a separately versioned cycle, a new development sample and another untouched
confirmation sample.

## Allowed implementation tuning

Inside the prespecified nested development folds, the following may be selected only
from frozen grids:

- regularization strength and elastic-net mixing;
- correction shrinkage `kappa`;
- convergence/stopping parameters needed to reach the frozen numerical tolerance;
- calibration parameters;
- the already specified B0-v5N transformations.

The following are hypothesis changes and are prohibited within v5-R:

- new feature families or interaction classes;
- a different news-exposure window;
- a new relevance or novelty definition;
- a new semantic or embedding model;
- category-specific candidate models;
- reintroduction of diffusion, publisher diversity or story lifecycle.

## Development and confirmation requirements

1. Pass a label-blind Lumid coverage, cohort breadth, exposure-count and power gate.
2. Freeze the complete evaluator and the architecture of linear B0, B0-v5N, C5-R and
   V5-R before inspecting any new development label.
3. Use a new development interval not used in the opened v4/v5 diagnostics.
4. Report B0-v5N replication before interpreting the news mechanism comparisons.
5. Test V5-R once against B0-v5N and C5-R under identical nested purged folds.
6. If either news gate fails, stop the v5 news branch.
7. If all gates pass, freeze at most one news candidate.
8. Reserve a separate untouched confirmation interval disjoint from protected v4 and
   consume it exactly once.

The inferential sequence is:

```text
source/exposure feasibility
  -> B0-v5N replication
  -> V5-R versus B0-v5N
  -> V5-R versus C5-R
  -> freeze at most one news candidate
  -> independent untouched confirmation
```

The opened May–July data may validate software mechanics but must not be used again to
choose thresholds, variables or hyperparameters for `V5-R`.

## Claim boundary

Success would support incremental short-horizon predictive information from this
specific point-in-time relevance/novelty representation. It would not establish
causality, signed trading value, publisher independence, social virality, KOL effects
or universal prediction-market behavior.
