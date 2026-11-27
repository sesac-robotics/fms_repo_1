-- Add synthetic passengers to the isolated benchmark database.
\set ON_ERROR_STOP on
SELECT current_database() = 'amo_bench' AS benchmark_database \gset
\if :benchmark_database
\else
    \echo 'Expected the isolated amo_bench database.'
    SELECT 1 / 0;
\endif

\timing on
WITH synthetic AS (
    SELECT n, 'bench-passenger-' || n || '@example.invalid' AS email
    FROM generate_series(:first::bigint, :last::bigint) AS n
),
profiles AS (
    INSERT INTO users (id, name, contact, registered_at)
    SELECT nextval('amo_record_id'), 'Benchmark passenger ' || n, email,
           timestamptz '2026-01-01 00:00:00+00' + n * interval '1 second'
    FROM synthetic
    RETURNING id, name, contact, registered_at
)
INSERT INTO amo_accounts (profile_user_id, email, name, role, status, created_at)
SELECT id, contact, name, 'PASSENGER', 'ACTIVE', registered_at
FROM profiles;

ANALYZE users;
ANALYZE amo_accounts;
SELECT count(*) AS synthetic_passengers
FROM amo_accounts
WHERE email LIKE 'bench-passenger-%@example.invalid';
SELECT pg_database_size(current_database()) AS database_bytes;
SELECT relname, pg_table_size(oid) AS table_bytes,
       pg_indexes_size(oid) AS index_bytes,
       pg_total_relation_size(oid) AS total_bytes
FROM pg_class
WHERE oid IN ('users'::regclass, 'amo_accounts'::regclass)
ORDER BY relname;
