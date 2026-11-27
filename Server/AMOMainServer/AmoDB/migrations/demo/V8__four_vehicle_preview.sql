-- Extend only the demo roster. These IDs and poses are fictional and cannot dispatch.
INSERT INTO vehicles (id, vehicle_no, dispatch_enabled, updated_at)
VALUES
    (3, 'PINKY-03', false, '2026-11-22 09:00:00+09'),
    (4, 'PINKY-04', false, '2026-11-22 09:00:00+09');

UPDATE telemetry_samples
SET yaw_rad = CASE vehicle_id WHEN 1 THEN 0.0 WHEN 2 THEN 3.141593 END,
    speed_mps = 0.0
WHERE source_epoch = 'demo-1' AND sample_seq = 1 AND vehicle_id IN (1, 2);

INSERT INTO telemetry_samples
    (id, vehicle_id, map_version_id, source_epoch, sample_seq, observed_at, received_at,
     x_m, y_m, yaw_rad, speed_mps, battery_pct, latency_ms)
VALUES
    (3, 3, 1, 'demo-1', 1, '2026-11-22 09:00:00+09', '2026-11-22 09:00:00+09',
     0.653, 0.427, 1.570796, 0.0, 56, 52),
    (4, 4, 1, 'demo-1', 1, '2026-11-22 09:00:00+09', '2026-11-22 09:00:00+09',
     2.085, 0.255, -1.570796, 0.0, 92, 55);

INSERT INTO operation_events (id, vehicle_id, producer, event_key, event_type, received_at, details)
VALUES
    (4, 3, 'DEMO', 'demo-charging', 'CHARGING', '2026-11-22 09:00:00+09',
     '{"connection":"SIMULATED","vehicleStatus":"CHARGING"}'),
    (5, 4, 'DEMO', 'demo-available', 'AVAILABLE', '2026-11-22 09:00:00+09',
     '{"connection":"SIMULATED","vehicleStatus":"AVAILABLE"}');
