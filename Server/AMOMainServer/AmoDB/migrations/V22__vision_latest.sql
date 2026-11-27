-- Keep one independent observation per vehicle and Vision service.
CREATE TABLE vision_latest (
    vehicle_id bigint NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    source text NOT NULL CHECK (
        source IN ('DRIVING_PERCEPTION', 'TRAFFIC_RULES', 'DIRECTION_RECOGNITION')
    ),
    result_id uuid NOT NULL,
    frame_id text NOT NULL,
    captured_at timestamptz NOT NULL,
    processed_at timestamptz NOT NULL,
    received_at timestamptz NOT NULL,
    outcome text NOT NULL CHECK (outcome IN ('DETECTED', 'NOT_DETECTED', 'UNAVAILABLE')),
    label text,
    confidence double precision CHECK (confidence BETWEEN 0 AND 1),
    PRIMARY KEY (vehicle_id, source)
);
