# Assessment of six proposals to increase EventX's research value

29 October 2026. Assessment only. Read the canonical handoff, full research review, next-cycle draft,
completed consumption receipts and stored online-rate replication results. No experiment, upload,
current process check or new cycle was initiated.

## Priorities

| Proposal | Contribution to paper | Recommendation |
|---|---|---|
| Add post hoc results and reframe | High immediate clarity; limited new confirmation | Do before submission, with qualifications below |
| Off-host backup | Essential preservation/reproducibility; little direct novelty | Preserve the evidence dependency set and verify restoration |
| Pooled vs own-history study | Highest scientific priority | Refine, then separately authorize development and confirmation |
| Monitoring decision experiment | High potential practical contribution | Define costs and information access before implementation |
| Human news-link gold set | High for Track A; limited immediate Track B value | Separate measurement study before richer models |
| Server, benchmark, focus | Reliability enables evidence; reusable benchmark may be substantive | Treat as distinct deliverables; preserve frozen obligations |

## Report qualifications

Add May replication and history strata as exploratory evidence. The strata reset at each block;
zero matured outcomes does not necessarily mean a newly listed contract. Outcome counts are not elapsed
hours when availability is intermittent. Familiarity is confounded with cohort/date, so these results
do not identify the causal effect of training on a contract. Early-stratum CIs are contract-only and
exploratory; a difference in significance between strata is not a significant difference in effects.

Arithmetic from `data/v7/online_rate_replication_20261028/result.json`:

| Block | Rows with 0–11 matured outcomes | % scored rows | % total net gain contributed by those rows |
|---|---:|---:|---:|
| May13–19 development50 | 473 | 1.6938833977940124 | 4.440905133816395 |
| June1–7 development50 | 296 | 1.7990640004862335 | 6.867719395242199 |
| June8–14 new identities | 590 | 1.6752796865239366 | 81.58928618821903 |

Computed from stored stratum row counts × mean gains, without rescoring. These are descriptive net-gain
shares, not confidence estimates. The June8–14 denominator is small. Larger early per-row gains do not
mean most aggregate gain comes from early history in every block. Corrected the handoff accordingly.

Leading the report with evaluation engineering is reasonable. Leading a methods paper with it requires
evidence of a reusable advance: comparison with existing workflows, controlled failure cases and what
the harness detects/prevents. Hashing, receipts and preregistration alone do not establish novelty.
The earlier claim that discipline exceeds most published finance ML work is unsupported by a systematic audit.

## Backup scope

Results JSON preserves headline scores but cannot reconstruct them. Preserve predictions, ledgers,
cohorts, receipts/manifests, model artifacts, code revision/environment and needed source evidence or
a documented retrieval route. Distinguish reproducing scores from rebuilding inputs. Verify destination
hashes and restore a small completed-study bundle. This review did not check existing off-host storage
or authorize a transfer. Avoid a heavy full-archive operation during the protected live window.

## Focused study and equivalence

Keep HGB plus online rate/count versus rate as primary and matched logistic/GAM/HGB contrasts to
separate input value from learner choice. The existing rate is cumulative within each block, not a
rolling recent-outcome rate. Consider a prespecified recency-weighted reference during new development,
so a future win is not merely against slow adaptation. Do not select variants from consumed tests.
Specify causal feature construction, prior estimation, availability, carry-over/reset, and truly new
test families. Test the early-versus-late interaction directly if it is a central claim.

Equivalence excludes differences outside a justified practical margin; it does not confirm exact zero.
Standard TOST at one-sided alpha .05 corresponds to a valid90% CI wholly inside the bounds. This project
needs dependence-aware inference, separate equivalence power planning, and registered strata/multiplicity
rules. An inconclusive result remains possible. Source:
[Lakens](https://lakens.github.io/statistical_inferences/09-equivalencetest.html).

## Monitoring experiment

Choose the scarce resource first. Fresh quote features for every contract already require acquiring
those quotes. They can allocate expensive downstream attention, but cannot be treated as free when
claiming reduced quote polling. A true polling policy needs previously acquired state, charged refresh
and endpoint-check costs, and policy-specific available labels for online updates. Independent full
capture may provide evaluation ground truth while remaining hidden from the policy.

Compare uniform, round-robin, recent-activity and online-rate rankings at identical information/cost
budgets. Register one primary budget and secondary budget curves. Define endpoint differences versus
unique change episodes and detection latency: overlapping30-minute labels may count one move repeatedly,
and endpoint change misses moves that reverse. Log-loss improvement need not improve top-k ranking.
Report monitoring utility, without inferring trading profit or general economic value.

## News, infrastructure and benchmark

Human labels need explicit relevance criteria, hard negatives, independent annotators/adjudication
and multiple event episodes. Annotators cannot recover exact historical availability without records.
Separate occurrence, publication, revision, provider receipt and strategy availability. Precise timing
does not alone identify a causal news effect. Keep this a later Track A measurement study.

Use a server for future experiments with clock monitoring and durable state; define recovery/restart
rules in that new protocol. Do not migrate/restart the current V02b run. Hosting itself adds no novelty.
A benchmark needs a distinct evaluation gap, accessible data or reproducible access route, documented
tasks/splits/availability, strong baselines and a harness independently replayed by another user.
Originality, significance and usability remain review criteria:
[NeurIPS E&D guidelines](https://neurips.cc/Conferences/2026/EvaluationsDatasetsReviewerGuidelines).

Prioritize reporting/preservation before1November, then one focused empirical study plus one decision
use after separate authorization. Park optional variants while preserving negative findings and
completing frozen obligations. These proposals can materially strengthen an applied paper; they do
not guarantee top-tier readiness without new independent evidence and a defensible contribution.
