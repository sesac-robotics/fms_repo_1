SET LOCAL search_path TO public;

CREATE TABLE mock_payments (
    id bigint PRIMARY KEY,
    trip_id bigint NOT NULL,
    attempt_key text NOT NULL,
    tariff_version text NOT NULL,
    billed_distance_m double precision NOT NULL,
    billed_duration_s integer NOT NULL,
    amount_minor bigint NOT NULL,
    currency_code text NOT NULL,
    method_ref text NOT NULL,
    status text NOT NULL,
    attempted_at timestamptz NOT NULL,
    settled_at timestamptz,
    UNIQUE (trip_id, attempt_key)
);

CREATE TABLE passenger_checks (
    id bigint PRIMARY KEY,
    trip_id bigint NOT NULL,
    check_kind text NOT NULL,
    result text NOT NULL,
    provider_result_key text NOT NULL,
    checked_at timestamptz,
    received_at timestamptz NOT NULL,
    reason_code text,
    UNIQUE (trip_id, provider_result_key)
);

CREATE TABLE cargo_jobs (
    id bigint PRIMARY KEY,
    trip_id bigint NOT NULL UNIQUE,
    cart_ref text NOT NULL,
    attach_place_id bigint NOT NULL,
    detach_place_id bigint NOT NULL,
    status text NOT NULL,
    attached_at timestamptz,
    profile_applied_at timestamptz,
    detached_at timestamptz,
    closed_at timestamptz,
    result_code text
);

CREATE TABLE lost_item_reports (
    id bigint PRIMARY KEY,
    trip_id bigint NOT NULL,
    detector_result_key text NOT NULL,
    detected_at timestamptz NOT NULL,
    status text NOT NULL,
    user_notified_at timestamptz,
    operator_notified_at timestamptz,
    detail_code text,
    UNIQUE (trip_id, detector_result_key)
);
