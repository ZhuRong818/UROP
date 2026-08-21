# EventX v1 pilot release

This directory is the release index for the frozen EventX v1 pilot. It packages the
study's final report, evidence map, integrity metadata, and verifier without copying
the multi-gigabyte frozen data.

## Release status

- Release type: frozen pilot/reference result
- Development dataset: `eventx-toy-ceea70842baa88753929`
- Confirmatory dataset: `eventx-oot-7c4fd487edb3928b9253`
- Reference model: B0 market-only standardized logistic SGD
- Confirmatory holdout: evaluated once and **consumed**
- Rerun permitted: **false**
- Post-holdout tuning: **prohibited**

This is not yet the full EventX benchmark described in `research_plan.md`. The v1
pilot covers 20 Polymarket binary outcomes, one 30-minute horizon, a 5-minute
evaluation cadence, and a short retained-trade window. Kalshi, additional horizons,
the public Feature/Rehydration tracks, T5 influence ranking, and an economic
significance study remain future work.

## Start here

1. Read [the final research report](FINAL_RESEARCH_REPORT.md).
2. Read [the dataset datasheet](DATASHEET.md).
3. Review [public-release readiness](PUBLIC_RELEASE_CHECKLIST.md).
4. Inspect [the editorial audit](EDITORIAL_REVIEW.md).
5. Inspect [the machine-readable release manifest](release_manifest.json).
6. Verify every listed artifact and the consumed-holdout state:

   ```bash
   python -m eventx.release.verify_v1_release
   ```

The verifier hashes both small evidence files and the large frozen data artifacts,
so it may take several seconds.

## Integrity rules

The only confirmatory v1 evaluator was already run. Do **not** run:

```bash
python -m eventx.tasks.run_frozen_b0_oot_final
```

The consumption receipt sets `rerun_permitted` to `false`. The July 23–30 result
may be reported, but it may not justify a new feature, eligibility rule, association
rule, model, or hyperparameter choice.

The original development dataset's test block was exposed by an earlier
noncanonical B0 run. It is retained only as descriptive prior evidence. The final
claim uses the separately frozen out-of-time holdout.

## Evidence map

| Question | Canonical evidence |
|---|---|
| What was frozen for development? | `data/v1/toy/frozen_manifest.json` |
| Which baseline was locked? | `data/v1/toy/final_baseline_freeze_manifest.json` |
| How well did the KOL matcher perform? | `data/v1/curated/kol_rule_v3_frozen_manifest.json` |
| How well did the news matcher perform? | `data/v1/curated/news_rule_v1_frozen_manifest.json` |
| Did KOL/news candidates pass development gates? | `data/v1/toy/combined_b3_walk_forward_cv_5m.json` |
| Why did combined KOL performance fail? | `data/v1/toy/combined_b3_failure_diagnostic.md` |
| What authorized the replacement holdout? | `data/v1_oot_20260723_20260730/frozen_holdout_manifest.json` |
| What was the final result? | `data/v1_oot_20260723_20260730/b0_oot_final_result.json` |
| Can the evaluation be rerun? | `data/v1_oot_20260723_20260730/holdout_consumption_receipt.json` |

Paths are repository-relative. The release manifest records exact SHA-256 hashes.

## Verification layers

The release-level verification command checks the complete evidence list and the
holdout-state invariants. The original freeze verifiers remain available for
targeted checks:

```bash
python -m eventx.tasks.freeze_toy --verify
python -m eventx.tasks.freeze_final_baseline --verify
python -m eventx.tasks.freeze_oot_holdout --verify
```

The OOT freeze manifest describes its state at authorization time (`untouched`).
The later consumption receipt is the authoritative current state (`consumed`).

## Reuse and redistribution

This local package is an internal reproducibility bundle, not a redistribution
license. Before a public release:

- verify upstream rights for prediction-market, news, and social-media data;
- distribute public-post identifiers rather than raw social-media text where
  required;
- choose and add explicit code and data licenses;
- add a maintenance owner, versioned archive, and DOI;
- correct the frozen category metadata in a new versioned artifact;
- remove secrets and environment-specific configuration.

The [readiness checklist](PUBLIC_RELEASE_CHECKLIST.md) is the controlling list of
public-release blockers. Current decision: **NO-GO for public redistribution**.

No API token or credential is included in this release index.
