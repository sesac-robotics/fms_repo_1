-- Seed reproducible history in the isolated benchmark database.
\set ON_ERROR_STOP on
SELECT current_database() = 'amo_bench' AS benchmark_database \gset
\if :benchmark_database
\else
    SELECT 1 / 0;
\endif

\timing on
BEGIN;
WITH passengers AS (
    SELECT profile_user_id, row_number() OVER (ORDER BY id) AS sample_number
    FROM (
        SELECT id, profile_user_id
        FROM amo_accounts
        WHERE email LIKE 'bench-passenger-%@example.invalid'
        ORDER BY id LIMIT 100000
    ) accounts
)
INSERT INTO service_requests (
    id, user_id, idempotency_key, service_type, pickup_place_id, destination_place_id,
    called_at, received_at, source_channel, status
)
SELECT nextval('amo_record_id'), profile_user_id, 'benchmark-history', 'ONE_WAY',
       1, 2, arrival - interval '1 second', arrival, 'APP',
       CASE WHEN sample_number % 7 = 0 THEN 'WAITING_DISPATCH' ELSE 'COMPLETED' END
FROM passengers
CROSS JOIN LATERAL (
    SELECT timestamptz '2025-01-01 00:00:00+00' + sample_number * interval '1 minute' AS arrival
) times
ON CONFLICT (user_id, idempotency_key) DO NOTHING;

INSERT INTO operation_events (
    id, request_id, producer, event_key, event_type, received_at, details
)
SELECT nextval('amo_record_id'), r.id, 'BENCHMARK', r.id || '-' || series.n,
       'CALL_RECEIVED', r.received_at + series.n * interval '1 second',
       '{"message":"Synthetic benchmark history"}'
FROM service_requests r
CROSS JOIN generate_series(1, 3) series(n)
WHERE r.idempotency_key = 'benchmark-history'
ON CONFLICT (producer, event_key) DO NOTHING;

INSERT INTO amo_trial_history (name, recorded_at, passed, total, latency_ms)
SELECT 'Benchmark trial ' || n, timestamptz '2025-01-01 00:00:00+00' + n * interval '1 hour',
       80 + n % 21, 100, 12 + n % 180
FROM generate_series(1, 10000) n
WHERE NOT EXISTS (SELECT 1 FROM amo_trial_history WHERE name = 'Benchmark trial 1');
COMMIT;

ANALYZE service_requests;
ANALYZE operation_events;
ANALYZE amo_trial_history;
SELECT count(*) FROM service_requests WHERE idempotency_key = 'benchmark-history';
SELECT count(*) FROM operation_events WHERE producer = 'BENCHMARK';
SELECT count(*) FROM amo_trial_history;
