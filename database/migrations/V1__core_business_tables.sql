SET LOCAL search_path TO public;

CREATE TABLE users (
    id bigint PRIMARY KEY,
    name text NOT NULL,
    contact text NOT NULL,
    face_profile_ref text,
    mock_payment_method_ref text,
    registered_at timestamptz NOT NULL
);

CREATE TABLE vehicles (
    id bigint PRIMARY KEY,
    vehicle_no text NOT NULL UNIQUE,
    dispatch_enabled boolean NOT NULL,
    updated_at timestamptz NOT NULL
);

CREATE TABLE map_versions (
    id bigint PRIMARY KEY,
    version_key text NOT NULL UNIQUE,
    frame_id text NOT NULL,
    artifact_ref text NOT NULL,
    artifact_sha256 text NOT NULL,
    created_at timestamptz NOT NULL
);

CREATE TABLE places (
    id bigint PRIMARY KEY,
    map_version_id bigint NOT NULL,
    place_key text NOT NULL,
    name text NOT NULL,
    kind text NOT NULL,
    x_m double precision NOT NULL,
    y_m double precision NOT NULL,
    yaw_rad double precision,
    UNIQUE (map_version_id, place_key)
);

CREATE TABLE service_requests (
    id bigint PRIMARY KEY,
    user_id bigint NOT NULL,
    idempotency_key text NOT NULL,
    service_type text NOT NULL,
    pickup_place_id bigint NOT NULL,
    destination_place_id bigint,
    rental_duration_s integer,
    called_at timestamptz,
    received_at timestamptz NOT NULL,
    source_channel text NOT NULL,
    status text NOT NULL,
    wait_reason_code text,
    UNIQUE (user_id, idempotency_key)
);

CREATE TABLE dispatches (
    id bigint PRIMARY KEY,
    request_id bigint NOT NULL,
    vehicle_id bigint NOT NULL,
    status text NOT NULL,
    assigned_at timestamptz NOT NULL,
    pickup_eta_at timestamptz,
    ended_at timestamptz,
    end_reason_code text
);

CREATE TABLE trips (
    id bigint PRIMARY KEY,
    dispatch_id bigint NOT NULL UNIQUE,
    status text NOT NULL,
    started_at timestamptz,
    ended_at timestamptz,
    distance_m double precision,
    elapsed_s integer,
    outcome_code text
);

CREATE TABLE route_revisions (
    id bigint PRIMARY KEY,
    vehicle_id bigint NOT NULL,
    dispatch_id bigint,
    map_version_id bigint NOT NULL,
    route_key text NOT NULL,
    revision_no integer NOT NULL,
    status text NOT NULL,
    plan_ref text,
    planned_distance_m double precision,
    reason_code text,
    planned_at timestamptz NOT NULL,
    UNIQUE (route_key, revision_no)
);

CREATE TABLE vehicle_commands (
    id bigint PRIMARY KEY,
    vehicle_id bigint NOT NULL,
    dispatch_id bigint,
    target_place_id bigint,
    route_revision_id bigint,
    command_type text NOT NULL,
    status text NOT NULL,
    issuer_ref text NOT NULL,
    connection_epoch text NOT NULL,
    issued_at timestamptz NOT NULL,
    valid_until timestamptz,
    settled_at timestamptz,
    outcome_code text
);

CREATE TABLE operation_events (
    id bigint PRIMARY KEY,
    vehicle_id bigint,
    request_id bigint,
    dispatch_id bigint,
    command_id bigint,
    place_id bigint,
    producer text NOT NULL,
    event_key text NOT NULL,
    event_type text NOT NULL,
    state_scope text,
    state_model_version text,
    state_from text,
    state_to text,
    state_epoch text,
    state_sequence bigint,
    cause_code text,
    result_code text,
    occurred_at timestamptz,
    received_at timestamptz NOT NULL,
    details jsonb,
    UNIQUE (producer, event_key),
    UNIQUE (vehicle_id, state_scope, state_epoch, state_sequence)
);

CREATE TABLE telemetry_samples (
    id bigint PRIMARY KEY,
    vehicle_id bigint NOT NULL,
    dispatch_id bigint,
    route_revision_id bigint,
    command_id bigint,
    map_version_id bigint,
    source_epoch text NOT NULL,
    sample_seq bigint NOT NULL,
    observed_at timestamptz,
    received_at timestamptz NOT NULL,
    x_m double precision,
    y_m double precision,
    yaw_rad double precision,
    speed_mps double precision,
    battery_pct double precision,
    latency_ms double precision,
    perception_summary jsonb,
    UNIQUE (vehicle_id, source_epoch, sample_seq)
);

CREATE TABLE facility_uses (
    id bigint PRIMARY KEY,
    place_id bigint NOT NULL,
    vehicle_id bigint NOT NULL,
    status text NOT NULL,
    allocated_at timestamptz NOT NULL,
    entered_at timestamptz,
    released_at timestamptz,
    reason_code text
);
