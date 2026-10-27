"""Publish the source ledger and opened-development coverage findings."""
from pathlib import Path
import json

from eventx.tasks.build_v7_verified_event_ledger_20261015_v02 import ROOT, OUT, sha, read, write


def main():
    destination = ROOT / 'EVENTX_VERIFIED_EVENT_LEDGER_AND_COVERAGE_20261015.md'
    if destination.exists():
        raise FileExistsError('Preserve report')
    report = json.loads((OUT / 'report.json').read_text())
    articles = read(OUT / 'article_ledger.jsonl')
    coverage = {r['article_id']: r for r in read(OUT / 'article_coverage.jsonl')}
    events = read(OUT / 'event_ledger.jsonl')
    components = read(OUT / 'isolation_component_coverage.jsonl')
    md = ['# EventX: source verification, event ledger and coverage', '',
        '15 October 2026 · Opened historical development only · Current package: `data/v7/verified_event_ledger_20261015_v02/`.', '',
        '## Main result', '',
        '**The 12 jointly reviewed articles cover 95 distinct forecast rows, including 27 large-movement labels and 68 non-movements.** Excluding the ambiguous Kalshi zero-basis-point contract leaves 48 rows (11 movements). Also excluding the article with the PPI summary discrepancy leaves 44 rows (11 movements). These are coverage counts, not forecasting performance.', '',
        'The ledger identifies seven referenced event identities: six have an official release, statement or event programme; the Visser podcast is identified only by the original reporting. Three official releases have exact announced public clocks. Several article-to-event mappings remain contextual, four originals could not be recovered, and no historical first-version text is authenticated. The verification task is complete with these explicit unresolved fields; the evidence is not fully certified.', '',
        '**Timing is the principal practical bottleneck:** none of the 12 articles arrives within an hour of its cached publication timestamp. The seven CPI/PPI-linked articles arrive at least 120.25 minutes after their most recent linked official release. This establishes delayed access, not the absence of any residual predictive value.', '',
        '## 1. What was done', '',
        '1. Preserved the two agents’ original judgments and selected their unchanged 32 agreed material-context links. Disputed links were not promoted.',
        '2. Inspected original publisher pages and official BLS, BEA, Federal Reserve, ECB and CENTCOM evidence. Source findings are retrospective diagnostics; they do not replace the historical feed or change `available_at`.',
        '3. Recorded release identities, reporting roles, source clocks, explicit uncertainty and mixed-event references in a separate versioned ledger.',
        '4. Receipted ledger hashes, coverage rules and input hashes before the new counts. Prior development and aggregate outcome exposure is disclosed; this is not a new blinded preregistration.',
        '5. Reconstructed eligible rows from the existing opened examples and deduplicated by contract and decision time. Every one of the 32 pair-level counts reproduces the earlier inventory.', '',
        'Eligibility is inherited example eligibility plus price age ≤5 minutes, at least three trades in the preceding 60 minutes, and an article available within the preceding 30 minutes. This report covers 11–21 July across opened market groups. **None of the reviewed fresh rows belongs to original fold 5.** This broader population cannot replace the original held-market evaluation.', '',
        '## 2. Event ledger and verification status', '',
        '| Event identity | Public disclosure evidence | Status and interpretation |',
        '|---|---|---|',
        '| June CPI | [BLS archived release](https://www.bls.gov/news.release/archives/cpi_07142026.htm), 14 July 12:30 UTC | Release identity, values and clock verified: headline −0.4% monthly; +3.5% annually. Repeated CPI stories share this release. |',
        '| June PPI | [BLS archived release](https://www.bls.gov/news.release/archives/ppi_07152026.htm), 15 July 12:30 UTC | Release identity, values and clock verified: −0.3% monthly; **+5.5% annually**. |',
        '| May core PCE | [BEA release](https://www.bea.gov/news/2026/personal-income-and-outlays-may-2026), 25 June 12:30 UTC | +3.4% annually. The July article recaps an older release. |',
        '| Warsh at Sintra | [ECB programme](https://www.ecb.europa.eu/press/conferences/html/20260629_ecb_forum_on_central_banking.en.html), 1 July | Official panel identity/schedule verified. The statement is attributed by [contemporaneous reporting](https://au.finance.yahoo.com/news/kevin-warsh-fed-will-not-be-comfortable-with-inflation-above-2-183000837.html/); original recording and exact utterance clock remain unverified. |',
        '| Warsh congressional testimony | [Federal Reserve prepared remarks](https://www.federalreserve.gov/newsevents/testimony/warsh20260714a.htm), 14 July | Price-stability statement verified in official text. Identical prepared remarks submitted on 15 July; exact first-public clock unknown. |',
        '| Visser forecast | [Original Benzinga article](https://www.benzinga.com/crypto/cryptocurrency/26/07/60418617/bitcoin-plummets-below-63000-why-is-btc-going-down-again), 13 July, referring to 12 July podcast | Prior podcast and 35–40% hike forecast identified in original reporting. Recording unavailable; reported date only. |',
        '| US military strike statement | [CENTCOM release](https://www.centcom.mil/MEDIA/PUBLIC-RELEASES/Article/4540919/us-forces-finish-latest-round-of-strikes-against-iran/), 11 July | Official statement reports approximately 140 targets. Does not verify every conflict claim or a first-public clock. July article mixes later developments. |', '',
        '“Verified” here describes the specific source fact in the table. It does not establish article novelty, an independent statistical event, information surprise or a causal effect on prices.', '',
        '## 3. Article ledger', '',
        'The complete [article ledger](data/v7/verified_event_ledger_20261015_v02/article_ledger.jsonl) preserves cached text, both clocks, source URLs, event references, delay calculations and flags. The [event ledger](data/v7/verified_event_ledger_20261015_v02/event_ledger.jsonl) records source evidence separately.', '',
        '| Article ID | Referenced events | Publication → system (min) | Rows | Movement rows | Original access |',
        '|---|---|---:|---:|---:|---|']
    short = {'cpi_2026_06':'CPI', 'ppi_2026_06':'PPI', 'pce_2026_05':'May PCE',
        'warsh_sintra_20260701':'Sintra', 'warsh_testimony_20260714':'testimony',
        'visser_podcast_20260712':'Visser podcast', 'centcom_strikes_20260711':'strike statement'}
    for r in articles:
        c = coverage[r['article_id']]
        access = {'original_page_inspected':'Publisher page', 'original_publisher_search_body_inspected':'Publisher search body',
            'finnhub_redirect_unavailable_and_exact_original_not_recovered':'Unrecovered',
            'syndicated_search_excerpt_only_full_page_failed':'Syndicated excerpt'}[r['original_access']]
        md.append(f'| {r["article_id"]} | {", ".join(short[e] for e in r["event_ids"])} | {r["publication_to_system_minutes"]:.2f} | {c["rows"]} | {c["movement_rows"]} | {access} |')
    md += ['', 'Rows are deduplicated within each article. Article and event tables can overlap; their totals must not be added without a union of decision keys. Secondary event references recovered from full articles are conservative split safeguards; they are not newly validated predictive links.', '',
        '## 4. Coverage after review and source flags', '',
        '| Population | Articles | Links | Markets | Unique rows | Movements | Non-movements |',
        '|---|---:|---:|---:|---:|---:|---:|']
    names = {'all_agreed':'All agreed material context', 'exclude_ambiguous_H0':'Exclude ambiguous H0 contract',
        'exclude_H0_and_ppi_summary_discrepancy':'Also exclude PPI summary discrepancy'}
    for name, r in report['populations'].items():
        md.append(f'| {names[name]} | {r["articles"]} | {r["pairs"]} | {r["markets"]} | {r["rows"]} | {r["movement_rows"]} | {r["nonmovement_rows"]} |')
    md += ['', 'The all-agreed set spans five arrival/decision dates; removing H0 leaves four. Sensitivity exclusions are driven by contract/source uncertainty, not label balance. They do not redefine the original protocol.', '',
        '### Reducing repeated observations', '',
        '| Descriptive construction | Rows | Movements | Non-movements |',
        '|---|---:|---:|---:|',
        '| All reviewed arrival windows | 95 | 27 | 68 |',
        '| Earliest reviewed arrival per conservative group and contract | 14 | 6 | 8 |',
        '| Same earliest-arrival construction excluding H0 | 10 | 4 | 6 |',
        '| Greedy 30-minute spacing within each contract, all agreed | 32 | 10 | 22 |', '',
        'Earliest-arrival landmarks use the first eligible decision in the earliest reviewed article’s window, with no substitution of later arrivals. Thirty-minute spacing removes within-contract target overlap only. Neither procedure creates independent information events.', '',
        '## 5. Event dependence and split safeguards', '',
        'Mixed articles connect CPI, PPI and policy statements. Keep each connected group together in a later split. This deliberately conservative grouping can merge distinct economic events; **four groups is not an estimated effective sample size**.', '',
        '| Group to keep together | Articles | Unique rows | Movements |',
        '|---|---:|---:|---:|']
    for r in components:
        md.append(f'| {", ".join(short[e] for e in r["event_ids"])} | {r["articles"]} | {r["rows"]} | {r["movement_rows"]} |')
    md += ['',
        'All contracts concern the same July FOMC decision. Cross-contract observations and even these four groups can share calendar shocks. No valid effective sample size, minimum detectable effect or confirmatory confidence interval is established. The 95 rows and 27 movement labels must not be described as 95 events or 27 independent shocks.', '',
        '## 6. Timing diagnosis', '',
        f'Across the 12 reviewed articles, publication-to-system lag is **{report["publication_to_system_lag_minutes"]["min"]:.2f} / {report["publication_to_system_lag_minutes"]["median"]:.2f} / {report["publication_to_system_lag_minutes"]["max"]:.2f} minutes** (minimum / median / maximum). Zero arrive within 30 or 60 minutes; six within 180 minutes.', '',
        f'For the seven CPI/PPI-linked articles, delay from the most recent linked official release is **{report["cpi_ppi_release_to_system_delay"]["min_minutes"]:.2f} / {report["cpi_ppi_release_to_system_delay"]["median_minutes"]:.2f} / {report["cpi_ppi_release_to_system_delay"]["max_minutes"]:.2f} minutes**. Mixed-release articles use the later verified release, so this understates the age of any older CPI component. None arrives within 30 minutes of that release.', '',
        'The July 13 Warsh article recaps the July 1 forum. The July 19 article discusses earlier testimony and other prior statements; it is not a new July 19 policy announcement. The July 15 PCE article recaps the June 25 release. New article IDs cannot reset these information clocks.', '',
        '### Were markets observable when the official releases occurred?', '',
        'A separate hypothetical source-capture diagnostic applies the same freshness/trading screen in [release, release+30m) over all five original inventory contracts:', '',
        '| Official release window | Fresh eligible rows | Movements | Non-movements |',
        '|---|---:|---:|---:|']
    for r in report['official_release_window_totals']:
        md.append(f'| {short[r["event_id"]]} | {r["rows"]} | {r["movement_rows"]} | {r["nonmovement_rows"]} |')
    md += ['',
        'These 28 rows include both labels and occur on only two release dates; the candidate H0 contract is included in this observability diagnostic. They show opportunities for timely capture, **not news performance or usable historical feed observations**. Official sources were inspected retrospectively and are not inserted into historical features. A new capture protocol would be required to use them prospectively.', '',
        '## 7. Data-quality findings', '',
        '- **PPI summary discrepancy:** article `215472946` attaches a decline to the 5.5% annual figure. The [original publisher](https://www.investing.com/analysis/nasdaq-forecast-ndx-extends-gains-after-cooler-ppi-200683982) and BLS identify an annual increase. Flag the cached summary; do not silently repair historical input text or extract a signed annual surprise from it.',
        '- **Ambiguous contract:** `KXFEDDECISION-26JUL-H0` still lacks official rules/subtitle. The read-only official market API request failed in the sandbox with DNS resolution, then returned HTTP 404 on an approved network retry. Unaffiliated descriptions suggesting “hold” are insufficient to establish the exchange predicate.',
        '- **Market-odds contamination:** the Zacks CPI article quotes Polymarket; other articles mix independent economic observations and market expectations. Separate those evidence spans before any content feature comparison. Neither generic relevance nor the existence of a source citation proves external novelty.',
        '- **Source access:** six original pages, one original-publisher search body and one syndicated excerpt were inspectable. Four exact originals remained unavailable. Present-day pages do not authenticate historical article revisions.', '',
        '## 8. Research decision and next deliverable', '',
        '**Use this set for descriptive event analysis and pipeline debugging. Do not use it to claim a confirmed news gain.** Both outcome classes are now represented, but repeated, delayed information dominates the evidence set and no independent evaluation population has been established.', '',
        'The next useful experiment is a separately recorded cohort of original releases/statements captured promptly, across additional dates and preferably several FOMC cycles. Preserve original text and receipt times, record the first observed source version, and collect price/trade freshness at arrival. Check event yield before selecting the evaluation span.', '',
        'Keep the selected raw `condition_120k` market model fixed. A subsequent unsigned-content development pilot should compare market → exposure/timing → reviewed evidence on identical rows. Exact YES/NO direction is optional for the current absolute-movement target; reliable event identity, text and timing are the immediate priorities. No additional model search was performed here.', '',
        'V4 remains a separate frozen experiment. Its sealed future payload and one-shot consumption sequence were not accessed or changed. No consumed holdout was reopened.', '',
        '## 9. Reproducibility and remaining uncertainty', '',
        '- [Current package index](data/v7/verified_event_ledger_20261015_v02/INDEX.md)',
        '- [Source findings and recovery attempts](data/v7/verified_event_ledger_20261015_v02/source_findings.json)',
        '- [Coverage receipt before new counts](data/v7/verified_event_ledger_20261015_v02/coverage_receipt_before_new_counts.json)',
        '- [Machine-readable report](data/v7/verified_event_ledger_20261015_v02/report.json)',
        '- [Decision-row coverage and memberships](data/v7/verified_event_ledger_20261015_v02/row_coverage.jsonl)',
        '- [Version correction](data/v7/verified_event_ledger_20261015_v02/VERSION_NOTE.md)', '',
        'Version 1 correctly computed reviewed-arrival coverage but mislabeled a four-reviewed-contract release diagnostic as ALL_FIVE. Version 2 includes the fifth inventory contract there: CPI coverage changes 16→17 rows and 4→5 movement labels; PPI and all arrival counts are unchanged. Both versions are preserved. This correction is not model selection.', '',
        'The ledgers are assistant source assessments, not independently adjudicated human gold. Forecast models fitted: **0**. New forecast metrics: **none**. All 32 inherited pair counts reproduce, ledger hashes remain unchanged after counts, and delivery checks reconcile the released tables and memberships.']
    destination.write_text('\n'.join(md) + '\n')
    (OUT / 'INDEX.md').write_text('\n'.join([
        '# Verified event ledger package — current version 2', '',
        'Read the root report: `EVENTX_VERIFIED_EVENT_LEDGER_AND_COVERAGE_20261015.md`.', '',
        '- `article_ledger.jsonl`: 12 articles, cached text/clocks, source findings and flags.',
        '- `event_ledger.jsonl`: seven referenced identities, verification status and source clocks.',
        '- `pair_ledger.jsonl`: 32 unchanged agreed material-context links.',
        '- `contract_ledger.jsonl`: five original inventory contracts, four with agreed links.',
        '- `row_coverage.jsonl`: 95 unique opened decision keys, labels and article memberships.',
        '- `article_coverage.jsonl`, `pair_coverage.jsonl`, `event_coverage.jsonl`: grouped counts.',
        '- `isolation_component_coverage.jsonl`: four conservative split groups, not independent events.',
        '- `earliest_arrival_landmarks.jsonl`: earliest-arrival sensitivity rows in each population.',
        '- `official_release_window_coverage.jsonl`: hypothetical source-clock observability, not historical news features.',
        '- `source_findings.json`: manual source notes and unsuccessful retrievals.',
        '- `coverage_receipt_before_new_counts.json`, `manifest.json`, `delivery_checks.json`, `delivery_manifest.json`: provenance and integrity.',
        '- `VERSION_NOTE.md`: source-clock population correction; version 1 preserved.', ''
    ]))
    rows = read(OUT / 'row_coverage.jsonl')
    pc = read(OUT / 'pair_coverage.jsonl')
    pairids = {r['pair_id'] for r in read(OUT / 'pair_ledger.jsonl')}
    checks = {
        'unique_row_keys': len({(r['market_index'], r['decision_minute']) for r in rows}) == len(rows) == 95,
        'row_labels_reconcile': sum(r['label'] for r in rows) == 27,
        'all_memberships_are_reviewed': all(set(r['pair_ids']) <= pairids for r in rows),
        'pair_memberships_reconcile': all(sum(p['pair_id'] in r['pair_ids'] for r in rows) == p['rows'] for p in pc),
        'pair_movement_counts_reconcile': all(sum(r['label'] for r in rows if p['pair_id'] in r['pair_ids']) == p['movement_rows'] for p in pc),
        'freshness_and_trading_reconcile': all(r['price_age_minutes'] <= 5 and r['preceding60m_trade_count'] >= 3 for r in rows),
        'five_inventory_contracts': len(read(OUT / 'contract_ledger.jsonl')) == 5,
        'article_ids_unchanged': {r['article_id'] for r in articles} == {r['article_id'] for r in read(OUT / 'pair_ledger.jsonl')},
        'v01_arrival_counts_unchanged': report['populations'] == json.loads((OUT.with_name('verified_event_ledger_20261015') / 'report.json').read_text())['populations']
    }
    for p in [OUT / 'manifest.json', OUT.with_name('verified_event_ledger_20261015') / 'manifest.json']:
        checks[str(p.relative_to(ROOT)) + '_hashes'] = all(sha(ROOT / a['path']) == a['sha256'] for a in json.loads(p.read_text())['artifacts'])
    if not all(checks.values()):
        raise RuntimeError(checks)
    write('delivery_checks.json', {'checks': checks, 'all_passed': True, 'note': 'Artifact/count validation, not software tests or external source authentication.'})
    write('delivery_manifest.json', {'artifacts': [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in [*sorted(OUT.iterdir()), destination, Path(__file__)] if p.is_file() and p.name != 'delivery_manifest.json']})
    print(json.dumps({'report': str(destination), 'checks': checks}, indent=2))


if __name__ == '__main__':
    main()
