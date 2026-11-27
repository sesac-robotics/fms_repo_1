-- Schematic telemetry for the completed S2 to S4 demo request only.
INSERT INTO telemetry_samples (
    id, vehicle_id, dispatch_id, map_version_id, source_epoch, sample_seq,
    observed_at, received_at, x_m, y_m
)
SELECT
    100 + step.seq,
    1,
    1,
    1,
    'demo-trip-2',
    step.seq,
    timestamptz '2026-11-22 08:52:03+09' + step.seq * interval '25 seconds',
    timestamptz '2026-11-22 08:52:03.010+09' + step.seq * interval '25 seconds',
    step.x_m,
    step.y_m
FROM (VALUES
    (1, 1.843, 0.913),
    (2, 1.642, 0.913),
    (3, 1.430, 0.913),
    (4, 1.430, 0.585),
    (5, 2.320, 0.585),
    (6, 2.320, 0.255),
    (7, 2.085, 0.255)
) AS step(seq, x_m, y_m);
