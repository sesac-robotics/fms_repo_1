-- Fictional operations for a dedicated demo database. Coordinates are schematic display values.
INSERT INTO map_versions
    (id, version_key, frame_id, artifact_ref, artifact_sha256, created_at)
VALUES
    (1, 'v0.2', 'schematic_v02',
     'https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8192349/v0.2+2440x2225',
     '170834f2ea176183b779264270f200dbd969c975dffde6ca901d5827413faa68',
     '2026-11-22 09:00:00+09');

INSERT INTO places (id, map_version_id, place_key, name, kind, x_m, y_m)
VALUES
    (1, 1, 'S1', 'S1', 'STOP', 0.516, 0.913),
    (2, 1, 'S2', 'S2', 'STOP', 1.843, 0.913),
    (3, 1, 'S3', 'S3', 'STOP', 0.653, 0.427),
    (4, 1, 'S4', 'S4', 'STOP', 2.085, 0.255);

INSERT INTO users (id, name, contact, registered_at)
VALUES (1, 'Demo Passenger', 'passenger@amo.test', '2026-11-22 09:00:00+09');

INSERT INTO vehicles (id, vehicle_no, dispatch_enabled, updated_at)
VALUES
    (1, 'PINKY-01', false, '2026-11-22 09:00:00+09'),
    (2, 'PINKY-02', false, '2026-11-22 09:00:00+09');

INSERT INTO service_requests
    (id, user_id, idempotency_key, service_type, pickup_place_id, destination_place_id,
     called_at, received_at, source_channel, status, wait_reason_code)
VALUES
    (1, 1, 'demo-queued', 'ONE_WAY', 1, 2, '2026-11-22 09:00:01+09',
     '2026-11-22 09:00:02+09', 'APP', 'WAITING_DISPATCH', 'NO_AVAILABLE_VEHICLE'),
    (2, 1, 'demo-finished', 'ONE_WAY', 2, 4, '2026-11-22 08:51:01+09',
     '2026-11-22 08:51:02+09', 'APP', 'COMPLETED', NULL);

INSERT INTO dispatches
    (id, request_id, vehicle_id, status, assigned_at, pickup_eta_at, ended_at)
VALUES (1, 2, 1, 'COMPLETED', '2026-11-22 08:51:04+09',
        '2026-11-22 08:52:00+09', '2026-11-22 08:57:00+09');

INSERT INTO trips (id, dispatch_id, status, started_at, ended_at, distance_m, elapsed_s)
VALUES (1, 1, 'COMPLETED', '2026-11-22 08:52:03+09', '2026-11-22 08:57:00+09', 1.85, 297);

INSERT INTO telemetry_samples
    (id, vehicle_id, map_version_id, source_epoch, sample_seq, received_at, x_m, y_m,
     battery_pct, latency_ms)
VALUES
    (1, 1, 1, 'demo-1', 1, '2026-11-22 09:00:00+09', 0.516, 0.913, 82, 48),
    (2, 2, 1, 'demo-1', 1, '2026-11-22 09:00:00+09', 1.843, 0.913, 64, 83);

INSERT INTO operation_events
    (id, vehicle_id, request_id, producer, event_key, event_type, received_at, details)
VALUES
    (1, 1, 2, 'DEMO', 'demo-completed', 'TRIP_COMPLETED', '2026-11-22 08:57:00+09',
     '{"connection":"SIMULATED","vehicleStatus":"AVAILABLE","message":"Fictional completed trip"}'),
    (2, 2, NULL, 'DEMO', 'demo-link-loss', 'LINK_LOST', '2026-11-22 09:00:01+09',
     '{"connection":"DISCONNECTED","vehicleStatus":"STOPPED","message":"Fictional loss of link"}'),
    (3, NULL, 1, 'DEMO', 'demo-waiting', 'REQUEST_WAITING', '2026-11-22 09:00:02+09',
     '{"message":"Fictional request waits for an eligible vehicle"}');

INSERT INTO amo_test_results (name, passed, total, latency_ms)
VALUES
    ('Intersection reservation · demo', 8, 10, 42),
    ('Dispatch eligibility · demo', 10, 10, 31),
    ('Connection loss · demo', 6, 8, 71);
