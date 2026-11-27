-- Append one deterministic, four-vehicle telemetry batch.
\set ON_ERROR_STOP on
SELECT current_database() = 'amo_bench' AS benchmark_database \gset
\if :benchmark_database
\else
    SELECT 1 / 0;
\endif

WITH reception AS (
    SELECT clock_timestamp() AS received_at
)
INSERT INTO telemetry_samples (
    id, vehicle_id, map_version_id, source_epoch, sample_seq, observed_at,
    received_at, x_m, y_m, yaw_rad, speed_mps, battery_pct
)
SELECT nextval('amo_record_id'), v.id, m.id, :'epoch', :sequence::bigint,
       r.received_at, r.received_at,
       0.25 + (v.id - 1) * 0.56 + (:sequence::bigint % 17) * 0.008,
       0.6 + (v.id % 2) * 0.7, 0, 0, 90 - (:sequence::bigint % 20)
FROM vehicles v
CROSS JOIN map_versions m
CROSS JOIN reception r
WHERE v.vehicle_no IN ('PINKY-01', 'PINKY-02', 'PINKY-03', 'PINKY-04')
  AND NOT v.dispatch_enabled
  AND m.version_key = 'v0.2'
RETURNING vehicle_id, source_epoch, sample_seq, received_at;
