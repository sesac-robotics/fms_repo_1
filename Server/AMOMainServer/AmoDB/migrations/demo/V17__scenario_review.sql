-- Each review run owns its synthetic vehicle and leaves previous evidence intact.
CREATE TABLE demo_scenario_runs (
    id uuid PRIMARY KEY,
    owner_id bigint NOT NULL REFERENCES amo_accounts(id),
    passenger_id bigint NOT NULL REFERENCES users(id),
    plan text NOT NULL CHECK (plan IN ('TAXI_APPLIED', 'TAXI_APPLY_FAILED')),
    vehicle_id bigint UNIQUE REFERENCES vehicles(id),
    request_id bigint UNIQUE REFERENCES service_requests(id),
    created_at timestamptz NOT NULL DEFAULT statement_timestamp()
);

CREATE INDEX ix_demo_scenario_owner
    ON demo_scenario_runs (owner_id, created_at DESC, id DESC);

CREATE TABLE demo_scenario_steps (
    run_id uuid NOT NULL REFERENCES demo_scenario_runs(id),
    step text NOT NULL,
    ordinal integer NOT NULL CHECK (ordinal >= 0),
    evidence jsonb NOT NULL,
    PRIMARY KEY (run_id, step),
    UNIQUE (run_id, ordinal)
);
