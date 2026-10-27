SELECT r.run_id, r.endpoint_id, r.started_at, r.ended_at, r.status,
       r.rows_inserted, r.rows_updated, r.rows_failed,
       r.args->>'from' AS requested_from, r.args->>'to' AS requested_to,
       (SELECT count(*) FROM news.articles a WHERE a.source_run_id=r.run_id) AS retained_articles
FROM provenance.runs r
WHERE r.run_id IN ('592ebc42-79ad-4b33-af2d-628b5edb6167'::uuid,
                  'b2ea4fcf-57e1-46f4-82dc-5f6c0ea60a62'::uuid,
                  '5022dbb8-a4b4-40fa-9aed-8e88b7363572'::uuid)
ORDER BY r.run_id
