"""Opened-development V6 contract-day support inventory; no outcomes or admissions."""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / 'data/v3_1_historical/primary/development/prepared'
V5 = ROOT / 'data/v5/readiness_inventory_20260914'
CARDS = ROOT / 'data/v6/enriched_rule_comparison_20260921'
ARTICLES = ROOT / 'data/v6/expanded_coverage_20260919'
OUT = ROOT / 'data/v6/support_ledger_20260926'
START = date(2026, 5, 17)
END = date(2026, 7, 22)
DAYS = (END - START).days
US_DAY = 86_400_000_000
START_US = int(datetime(2026, 5, 17, tzinfo=timezone.utc).timestamp() * 1_000_000)
TRADE_DTYPE = np.dtype([('market', '<u4'), ('timestamp_us', '<i8'), ('price', '<f8'),
                        ('notional', '<f8'), ('ordinal', '<u8')])
NEWS_DTYPE = np.dtype([('market', '<u4'), ('timestamp_us', '<i8')])


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def rows(path: Path):
    with path.open() as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def write_json(path: Path, x) -> None:
    path.write_text(json.dumps(x, indent=2, sort_keys=True) + '\n')


def inputs() -> dict[str, str]:
    paths = [Path(__file__), PREP/'manifest.json', PREP/'market_index.jsonl',
             PREP/'trades.bin', PREP/'news_associations.bin', V5/'manifest.json',
             V5/'daily_news_inventory.json', CARDS/'manifest.json', CARDS/'cards.jsonl',
             CARDS/'scores.jsonl', ARTICLES/'manifest.json', ARTICLES/'articles.jsonl']
    return {str(p.relative_to(ROOT)): digest(p) for p in paths}


def verify_sources() -> None:
    prep = json.loads((PREP/'manifest.json').read_text())
    locked = {x['path']: x['sha256'] for x in prep['artifacts']}
    for name in ('market_index.jsonl', 'trades.bin', 'news_associations.bin'):
        path = PREP/name
        assert digest(path) == locked[str(path.relative_to(ROOT))], name
    for base in (V5, CARDS, ARTICLES):
        manifest = json.loads((base/'manifest.json').read_text())
        for name, expected in manifest.get('outputs', manifest).items():
            assert digest(base/name) == expected, str(base/name)


def prepare() -> None:
    assert not OUT.exists(), 'version already exists'
    verify_sources()
    cards = list(rows(CARDS/'cards.jsonl'))
    index = {(r['venue'], r['market_id']): r['market_index']
             for r in rows(PREP/'market_index.jsonl')}
    assert len(cards) == 134 and len({c['contract_id'] for c in cards}) == 134
    assert all((c['venue'], c['market_id']) in index for c in cards)
    days = json.loads((V5/'daily_news_inventory.json').read_text())
    assert len(days) == DAYS and days[0]['day'] == START.isoformat()
    OUT.mkdir(parents=True)
    spec = {
        'version': 'v6-support-ledger-v0.1-20260926',
        'scope': 'opened development [2026-05-17, 2026-07-22); 134 fixed enriched review cards',
        'granularity': 'one row per contract and UTC day, including no-observed-trade days',
        'days': DAYS, 'contracts': len(cards), 'expected_rows': DAYS*len(cards),
        'trade_projection': 'market index and timestamp only from frozen development trades.bin; prices/outcomes ignored',
        'legacy_association_projection': 'market index and timestamp only; associations are unvalidated source proxies',
        'news_day_projection': 'global export count from V5 inventory, not contract-specific feed completeness',
        'screened_article_projection': '185 retrospective development pairs with article source clock, not validated links or full news windows',
        'support_labels': 'separate observed trade count, feed observation/unknown, metadata snapshot time, rule presence, and admission blocker; no missing day is zero news',
        'admission': 'none; historical versions, status, feed completeness, relevance and family certification unresolved',
        'protected_access': False,
    }
    write_json(OUT/'spec.json', spec)
    write_json(OUT/'receipt.json', {'created_at': datetime.now(timezone.utc).isoformat(),
        'inputs': inputs(), 'spec_sha256': digest(OUT/'spec.json'),
        'receipt_written_before_computation': True})
    print(json.dumps({'prepared': True, 'rows': DAYS*len(cards)}), flush=True)


def array_counts(path: Path, dtype: np.dtype, markets: set[int]) -> np.ndarray:
    n = path.stat().st_size // dtype.itemsize
    assert n*dtype.itemsize == path.stat().st_size
    arr = np.memmap(path, dtype=dtype, mode='r', shape=(n,))
    counts = np.zeros((max(markets)+1, DAYS), dtype=np.int64)
    for start in range(0, n, 1_000_000):
        block = arr[start:start+1_000_000]
        market = block['market'].astype(np.int64)
        day = ((block['timestamp_us']-START_US)//US_DAY).astype(np.int64)
        assert np.all((day>=0)&(day<DAYS)), 'outside opened development'
        keep = np.isin(market, list(markets))
        np.add.at(counts, (market[keep], day[keep]), 1)
    return counts


def run() -> None:
    assert OUT.exists() and {p.name for p in OUT.iterdir()} == {'spec.json','receipt.json'}
    receipt = json.loads((OUT/'receipt.json').read_text())
    assert receipt['receipt_written_before_computation']
    assert receipt['inputs'] == inputs() and receipt['spec_sha256'] == digest(OUT/'spec.json')
    verify_sources()
    spec = json.loads((OUT/'spec.json').read_text())
    index = {(r['venue'], r['market_id']): r['market_index']
             for r in rows(PREP/'market_index.jsonl')}
    cards = sorted(rows(CARDS/'cards.jsonl'), key=lambda x:x['contract_id'])
    market_ids = {index[(c['venue'],c['market_id'])] for c in cards}
    assert len(market_ids) == len(cards) == spec['contracts']
    print('counting opened development trade clocks', flush=True)
    trade_counts = array_counts(PREP/'trades.bin', TRADE_DTYPE, market_ids)
    print('counting legacy association clocks', flush=True)
    association_counts = array_counts(PREP/'news_associations.bin', NEWS_DTYPE, market_ids)
    day_news = json.loads((V5/'daily_news_inventory.json').read_text())
    articles = {a['article_id']:a for a in rows(ARTICLES/'articles.jsonl')}
    screened = Counter()
    for pair in rows(CARDS/'scores.jsonl'):
        available = datetime.fromisoformat(articles[pair['article_id']]['source_clock_available_at'].replace('Z','+00:00'))
        d = available.date()
        assert START <= d < END
        screened[(pair['contract_id'], d.isoformat())] += 1
    assert sum(screened.values()) == 185
    output = []
    for card in cards:
        mi = index[(card['venue'],card['market_id'])]
        snapshot = datetime.fromisoformat(card['source_ingest_ts'].replace('Z','+00:00'))
        rules = card['recovered_rule_evidence']
        for di in range(DAYS):
            day = START+timedelta(days=di)
            day_end = datetime.combine(day+timedelta(days=1), datetime.min.time(), timezone.utc)
            observed_news = day_news[di]
            assert observed_news['day'] == day.isoformat() and not observed_news['coverage_certified']
            meta = 'retrospective_only' if snapshot >= day_end else 'observed_snapshot_version_uncertified'
            rule_clocks = [datetime.fromisoformat(x['available_at'].replace('Z','+00:00'))
                           for x in rules if x.get('available_at')]
            rule = ('missing_in_cached_snapshot' if not rules else
                    'retrospective_only' if not rule_clocks or min(rule_clocks)>=day_end else
                    'observed_text_version_uncertified')
            output.append({
                'contract_id':card['contract_id'], 'venue':card['venue'],
                'market_id':card['market_id'], 'day':day.isoformat(),
                'observed_trade_count':int(trade_counts[mi,di]),
                'trade_status':'observed_export_not_complete_certified' if trade_counts[mi,di] else 'no_observed_trade_unknown_completeness',
                'legacy_association_count':int(association_counts[mi,di]),
                'legacy_association_status':'unvalidated_proxy',
                'global_news_export_rows':int(observed_news['observed_news_rows']),
                'global_news_status':'unreconciled_observed_rows' if observed_news['observed_news_rows'] else 'zero_export_rows_not_proven_empty',
                'screened_article_pair_count':screened[(card['contract_id'],day.isoformat())],
                'screened_pairs_are_complete_or_validated':False,
                'metadata_snapshot_status':meta, 'rule_status':rule,
                'metadata_version_status':'uncertified', 'trading_status_history':'uncertified',
                'family_status':'uncertified', 'training_admissible':False,
                'support_status':'retrospective_only' if meta=='retrospective_only' else 'uncertain',
            })
    assert len(output)==spec['expected_rows']
    with (OUT/'ledger.jsonl').open('w') as f:
        for x in output:
            f.write(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n')
    summary = {
        'contracts':len(cards),'days':DAYS,'contract_days':len(output),
        'contract_days_with_observed_trades':sum(x['observed_trade_count']>0 for x in output),
        'observed_trades':sum(x['observed_trade_count'] for x in output),
        'contract_days_with_legacy_associations':sum(x['legacy_association_count']>0 for x in output),
        'legacy_associations':sum(x['legacy_association_count'] for x in output),
        'contract_days_with_screened_pairs':sum(x['screened_article_pair_count']>0 for x in output),
        'screened_pairs':sum(x['screened_article_pair_count'] for x in output),
        'metadata_snapshot_status':dict(Counter(x['metadata_snapshot_status'] for x in output)),
        'rule_status':dict(Counter(x['rule_status'] for x in output)),
        'global_news_status':dict(Counter(x['global_news_status'] for x in output)),
        'supported_contract_days':0, 'predictive_admissions':0,
        'interpretation':'clock/count inventory only; no contract-specific complete news, historical version/status, validated links or predictive exposure',
    }
    write_json(OUT/'report.json', summary)
    write_json(OUT/'manifest.json', {'inputs':receipt['inputs'],
        'outputs':{p.name:digest(p) for p in OUT.iterdir() if p.name!='manifest.json'}})
    print(json.dumps(summary,indent=2,sort_keys=True),flush=True)

if __name__ == '__main__':
    assert len(sys.argv)==2 and sys.argv[1] in ('prepare','run')
    (prepare if sys.argv[1]=='prepare' else run)()
