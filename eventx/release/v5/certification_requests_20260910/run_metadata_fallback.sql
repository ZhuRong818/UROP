SELECT run_id, endpoint_id, started_at, ended_at, status,
       rows_inserted, rows_updated, rows_failed,
       args->>'from' AS requested_from, args->>'to' AS requested_to,
       CASE WHEN error_text ILIKE '%abandoned%' THEN 'abandoned_cleanup'
            WHEN error_text IS NULL THEN 'none' ELSE 'other_error' END AS error_class
FROM provenance.runs
WHERE run_id IN ('592ebc42-79ad-4b33-af2d-628b5edb6167'::uuid,
                 'b2ea4fcf-57e1-46f4-82dc-5f6c0ea60a62'::uuid,
                 '5022dbb8-a4b4-40fa-9aed-8e88b7363572'::uuid)
ORDER BY run_id
LIMIT 4
