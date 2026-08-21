# EventX v1 public-release readiness checklist

**Decision:** **NO-GO for public redistribution**  
**Scope:** frozen v1 pilot only  
**Reviewed:** 2026-07-31

The research result is frozen and reproducible locally. The remaining blockers are
distribution, governance, and documentation issues—not additional v1 model
experiments.

## Readiness matrix

| Area | Status | Required action |
|---|---|---|
| Final research report | Complete | Editorial changes only; preserve frozen claims |
| Datasheet | Complete for internal pilot | Re-review after the public bundle is defined |
| Evidence manifest | Complete | Refresh hashes after release-document changes |
| Release verifier | Complete | Run in a clean environment before distribution |
| Holdout integrity | Complete | Keep receipt; never rerun consumed evaluator |
| Category metadata | Blocked | Version a corrected taxonomy; Karen Bass is incorrectly tagged `sports` |
| Code license | Blocked | Select and add an explicit license |
| Data license | Blocked | Determine a lawful license for derived features/labels |
| Upstream-rights review | Blocked | Review findata, Polymarket, news, and social-source terms |
| Social/news content policy | Blocked | Define an ID/feature-only public surface; exclude restricted raw text |
| Privacy review | Blocked | Review public-handle identifiability and data minimization |
| Dual-use review | Blocked | Document manipulation/front-running risks and mitigations |
| Secret scan | Blocked | Scan the complete export, git history, configs, and notebooks |
| Public bundle | Blocked | Build a minimal feature/label/split/evaluation package |
| Clean-room reproduction | Blocked | Reproduce without `.env`, private API access, or local raw corpora |
| Maintainer and contact | Blocked | Name an owner and support channel |
| Versioning and archive | Blocked | Choose semantic version, archive, DOI, and changelog |
| Citation metadata | Blocked | Add citation file and archival citation |
| Deleted-post measurement | Not available | Measure in a future rehydration release or disclose permanently |

## Required release sequence

1. Freeze a list of files proposed for public distribution.
2. Conduct upstream-rights, licensing, privacy, and dual-use reviews on that exact
   list.
3. Version corrected category metadata without modifying the frozen v1 cohort file.
4. Create an ID/feature-only export with no raw post or article text.
5. Add code/data licenses, maintainer information, citation metadata, and a
   changelog.
6. Run a secret scan on both the bundle and the relevant repository history.
7. Reproduce loading and evaluation in a clean environment without credentials.
8. Hash the final archive, update the manifest, and deposit it in the selected
   archival service.
9. Change this decision to GO only after every blocked item has an owner and evidence.

## Integrity constraint

Public-release preparation must not:

- rerun `eventx.tasks.run_frozen_b0_oot_final`;
- use the OOT result to tune or promote a candidate;
- rewrite frozen data or frozen manifests in place; or
- describe the v1 pilot as the completed multi-venue EventX benchmark.
