# Signed-evidence predicate-binding repair

**12 October 2026 — completed development implementation**

Current extractor: `eventx/v7/signed_evidence_v03_3.py` (**v0.3.3**).  
Current diagnostic package: `data/v7/signed_evidence_v03_3_development_20261012/`.

## Result

| Opened-development diagnostic | Original v0.2 | Current v0.3.3 |
|---|---:|---:|
| Exact signed article–market associations | 1,559 | **11** |
| Distinct contributing articles | 400 | **2** |
| Distinct associated markets | 32 | **10** |
| Previously identified erroneous fitting links still signed | 6 | **0** |
| Signed rows in fold-4 fitting population | 21 | **0** |
| Signed rows in fold-5 evaluation population | 0 | **0** |

Four old signed associations remain, 1,555 lose exact status, and seven gain an exact negative/positive implication under the new grammar. Reduced volume is a consequence of stricter binding; it is not an independently measured precision or recall improvement. All six previously inspected fitting errors now abstain, a concrete repair on the known development cases.

The corpus diagnostic processed all **479,179 existing associations** from **147,377 deduplicated documents**. Thirty-six prior input/artifact hashes matched, new code hashes were receipted before each corpus run, and accepted evidence spans reproduce the exact input substrings. Independent event-to-row tracing agrees with the existing feature aggregator.

No forecasting model was fit or scored. No outcome or prediction fields were accessed. The original clocks, groups, target eligibility and 30-minute feature window were preserved.

## What changed

### 1. Bind the agency, action and object

Fed action extraction requires a bounded clause with the Federal Reserve/Fed/FOMC as actor and a rate object or explicit basis-point amount. Article-wide occurrences of `lower`, `cut`, `increase` or `hold` cannot establish a policy action.

This removes the demonstrated “lower courts” and “traders cut risk” errors. A Fed mention elsewhere in the document cannot supply the subject of those actions.

### 2. Parse the required contract quantity

Contract predicates carry explicit quantity operators:

| Wording | Parsed constraint |
|---|---|
| `25 bps` | Exactly 25 |
| `50+ bps` | At least 50 |
| `>25bps` | Strictly greater than 25 |
| `0bps` | Hold/no rate change |
| `1 Fed rate cut` | Annual count equals one |
| `2 Fed rate cuts` | Annual count equals two |
| `no Fed rate cuts` | Annual count equals zero |

An absent article quantity cannot establish a matching positive exact-size bucket. An explicit opposing action or hold can still oppose a bucket. Exact annual count predicates require an explicit annual count forecast; a past rate level or a generic rate-cut mention cannot establish one versus two cuts.

### 3. Bind the period

Monthly claims need a period in the action span and a compatible year. No meeting month is borrowed from the contract, unrelated headline text or availability timestamp.

An explicit month without a year, or “this year,” may use the article's conservative availability year as an explicit **year-anchor assumption**. The returned claim records `period_binding=availability_year_anchor`. Supplying no availability context and no article year causes the year comparison to abstain.

The narrow same-clause `with the first ... hike/cut in ...` path can inherit a bound Fed actor and forecast attribution while extracting its own month and amount. This retains the Bank of America forecast. Same-month day-level deadline inference is deliberately unsupported. Full meeting/episode identity and resolution-rule entailment still require review.

### 4. Preserve uncertainty

Conditional, negated, modal and generic odds/bets language cannot automatically become an exact action. Conditional Fed headlines remain contextual. A bare infinitive embedded in prose needs a governing forecast predicate; statements about the “case for” or “scope for” an action cannot establish an asserted policy path.

The parser distinguishes the month **May** from modal **may**. It also separates infinitival future plans from the rate-level preposition in wording such as “cut rates to 3.75%.” Conflicting matched directions cause abstention.

### 5. Make decisions inspectable

Each result supplies the typed contract predicate, bound claims, quantity operators, period binding, evidence offsets, exact spans and indices of claims used for direction. It separately records claim type, attribution and general expectation/explicit prediction-odds flags. A policy actor mention alone is not proof that the institution is the reporting source.

`confidence=1.0` is a deterministic rule weight, not a calibrated probability of correctness. `public_surprise` remains null.

## The six known repairs

| Article | Previous defect | Current behavior |
|---|---|---|
| `197135093` | “lower courts” becomes a 50+ bp cut | Abstain: no bound Fed rate action |
| `201331696` | Generic cut odds become a July 50+ bp cut | Abstain: no exact bound action/size/period |
| `199965294`, one-cut contract | Past rate level fixes annual cut count | Abstain: missing annual count/period |
| `199965294`, two-cut contract | Same text also supports two cuts | Abstain: missing annual count/period |
| `211002653` | Traders cutting risk becomes a Fed cut | Abstain: wrong action subject/object |
| `202999082` | Easing cut bets supports exactly two cuts | Abstain: unsupported action/count implication |

The replay is a previously opened assistant debugging set. It cannot establish general semantic accuracy or substitute for independent review.

## Remaining accepted evidence and coverage

- **Article `189435511`: five associations.** An attributed Bank of America forecast describes 75 bp of hikes in the year, starting with a 25 bp September hike. The grammar supports the annual hike predicate and September hike bucket, and opposes the earlier deadline, September hold and September cut predicates.
- **Article `63696548`: six associations.** A headline reports Yardeni's forecast that the Fed will have to raise interest rates in July. It supports the annual hike predicate and opposes July cut/hold buckets. It does not establish a positive exact-size hike bucket, because no hike size is given. Structured attribution stays unspecified because the bounded attribution adapter does not resolve Yardeni's identity.

These are two article arrivals, not two certified independent information surprises. Every accepted pair needs evidence/episode review.

Both fitting and evaluation coverage remain zero. The current eleven associations fall outside folds 4 and 5; earlier folds also contain no matching eligible decision in the unchanged window. Even the descriptive all-group eligible-example coverage is zero across the five existing OOF date intervals. Thus fixing semantics does not recover a usable forecasting population in these data.

## Development lineage

Every completed intermediate version is preserved with its own code receipt, decisions and manifest:

| Version | Exact associations | What the next iteration addressed |
|---|---:|---|
| v0.3 | 13 | Hypothetical-policy scope and source attribution |
| v0.3.1 | 11 | May/month versus may/modal ambiguity and infinitive role |
| v0.3.2 | 12 | Newly exposed “scope for ... to hike” prose fragment |
| **v0.3.3** | **11** | Current governing-predicate repair |

Their data directories use `signed_evidence_v03[_1/_2/_3]_development_20261012`. The original v0.2 extractor and original forecast trial remain unchanged. The current extractor is used by the new corpus diagnostic; no historical model or frozen confirmation pipeline was silently switched to it.

## Use and next action

```python
from eventx.v7.signed_evidence_v03_3 import extract_signed_evidence

evidence = extract_signed_evidence(
    headline, summary, question,
    available_at=available_at,
)
# Only applicability == "exact" and nonzero direction enter signed features.
```

The package contains the 11 accepted association traces, all 1,559 previous exact decisions, six known-error replays, coverage counts, source/code receipts and hash manifests. A separate **17-pair evidence packet** combines every accepted association with the six known rejected links, hiding algorithm decisions. Blank A/B response templates are included for development review. This selected packet diagnoses these examples; it is not a representative independent precision/recall audit.

**Next:** review the evidence and establish a small event pilot with fresh, observable market decisions at conservative article availability. Measure distinct supported arrivals and episode yield before another forecasting fit. Broader grammar/retrieval recall, exact meeting identity, source delivery and dependable event-level inference remain open. No predictive improvement is claimed.

Software tests were not added or run in this task. The executed checks are the authorized opened-data research diagnostic, evidence-span checks and artifact/coverage consistency checks.
