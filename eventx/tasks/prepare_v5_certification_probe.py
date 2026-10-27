"""Generate bounded, source-only reconciliation requests from existing opened IDs."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'data/v5/certification_probe_20260910'


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    plan = json.loads((ROOT/'data/v5/lineage_recovery_20260909/request_plan.json').read_text())
    ids = [r['run_id'] for r in plan['selected']]
    # UUID validation before SQL interpolation.
    from uuid import UUID
    values = ','.join("'"+str(UUID(x))+"'::uuid" for x in ids)
    sql = f"""WITH committed AS (
 SELECT source_run_id, count(*) AS retained_articles,
        min(ingest_ts) AS min_ingest, max(ingest_ts) AS max_ingest
 FROM news.articles
 WHERE source_run_id IN ({values})
 GROUP BY source_run_id
)
SELECT r.run_id, r.endpoint_id, r.started_at, r.ended_at, r.status,
       r.rows_inserted, r.rows_updated, r.rows_failed,
       r.args->>'from' AS requested_from, r.args->>'to' AS requested_to,
       r.args->>'window_days' AS window_days,
       CASE WHEN r.error_text ILIKE '%abandoned%' THEN 'abandoned_cleanup'
            WHEN r.error_text IS NULL THEN 'none' ELSE 'other_error' END AS error_class,
       c.retained_articles, c.min_ingest, c.max_ingest
FROM provenance.runs r LEFT JOIN committed c ON c.source_run_id=r.run_id
WHERE r.run_id IN ({values})
ORDER BY r.run_id
LIMIT 25
"""
    (OUT/'run_reconciliation.sql').write_text(sql)
    (OUT/'request_plan.json').write_text(json.dumps({
        'run_ids': ids, 'source': 'prior priority reconciliation sample, not representative',
        'no_article_text_or_outcomes': True,
        'counts_are_current_retained_rows_not_original_commits': True}, indent=2)+'\n')
    print('Prepared bounded reconciliation for', len(ids), 'existing run IDs')


if __name__ == '__main__':
    main()
