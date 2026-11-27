CREATE INDEX ix_service_requests_received ON service_requests (received_at DESC, id DESC);

CREATE TABLE amo_trial_history (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL,
    recorded_at timestamptz NOT NULL,
    passed integer NOT NULL CHECK (passed >= 0),
    total integer NOT NULL CHECK (total >= passed),
    latency_ms integer NOT NULL CHECK (latency_ms >= 0)
);

CREATE INDEX ix_amo_trial_history_recent ON amo_trial_history (recorded_at DESC, id DESC);
