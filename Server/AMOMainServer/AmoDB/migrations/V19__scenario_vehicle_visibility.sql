-- Production vehicles retain their existing visibility and telemetry behavior.
ALTER TABLE vehicles
    ADD COLUMN scenario_visible boolean NOT NULL DEFAULT true,
    ADD COLUMN scenario_run_id uuid;

ALTER TABLE demo_depot_cycles
    ADD COLUMN scenario_archived boolean NOT NULL DEFAULT false;
