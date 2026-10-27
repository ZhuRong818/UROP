WITH failed(run_id, decision_at) AS (
  VALUES
    ('d8bcb0d0-be28-4a0a-920c-d6087a07e5a8'::uuid, '2026-05-30T13:52:00Z'::timestamptz),
    ('c40c9e49-4a6a-44d1-a0d9-43ca033d21ae'::uuid, '2026-06-01T16:22:01Z'::timestamptz),
    ('fd734424-86f2-4d65-a67c-868d6f80730a'::uuid, '2026-06-23T18:52:01Z'::timestamptz),
    ('592ebc42-79ad-4b33-af2d-628b5edb6167'::uuid, '2026-06-30T04:52:01Z'::timestamptz),
    ('86c568d4-f947-43e2-950b-8cf740690a9e'::uuid, '2026-07-02T18:37:01Z'::timestamptz)
)
SELECT f.run_id::text AS failed_run_id, f.decision_at,
       r.run_id::text AS successor_run_id, r.started_at, r.ended_at,
       r.status, r.rows_inserted, r.rows_failed, r.args->>'to' AS requested_to
FROM failed f
LEFT JOIN LATERAL (
  SELECT r.* FROM provenance.runs r
  WHERE r.endpoint_id = 'finnhub:company-news'
    AND r.started_at > f.decision_at
    AND r.started_at < f.decision_at + interval '7 days'
    AND r.status IN ('ok', 'partial')
  ORDER BY r.started_at
  LIMIT 1
) r ON true
ORDER BY f.decision_at
LIMIT 5
