-- Inspect live plan shapes after synthetic data loading.
\set ON_ERROR_STOP on
BEGIN READ ONLY;
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, name, email, role, status
FROM amo_accounts
WHERE strpos(lower(name), 'bench-passenger-999') > 0
   OR strpos(email, 'bench-passenger-999') > 0
ORDER BY id LIMIT 51;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, service_type, status, received_at
FROM service_requests
WHERE received_at >= '2025-01-01T00:00:00Z'
  AND received_at < '2026-01-01T00:00:00Z'
  AND strpos(lower(service_type), 'one_way') > 0
ORDER BY received_at DESC, id DESC LIMIT 50;

EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*)
FROM service_requests
WHERE received_at >= '2025-01-01T00:00:00Z'
  AND received_at < '2026-01-01T00:00:00Z'
  AND strpos(lower(service_type), 'one_way') > 0;

EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*)
FROM amo_trial_history
WHERE strpos(lower(name), 'benchmark') > 0;
ROLLBACK;
