SET LOCAL search_path TO public;

ALTER TABLE places
    ADD CONSTRAINT fk_places_map_version_id
        FOREIGN KEY (map_version_id) REFERENCES map_versions (id);

ALTER TABLE service_requests
    ADD CONSTRAINT fk_service_requests_user_id
        FOREIGN KEY (user_id) REFERENCES users (id),
    ADD CONSTRAINT fk_service_requests_pickup_place_id
        FOREIGN KEY (pickup_place_id) REFERENCES places (id),
    ADD CONSTRAINT fk_service_requests_destination_place_id
        FOREIGN KEY (destination_place_id) REFERENCES places (id);

ALTER TABLE dispatches
    ADD CONSTRAINT fk_dispatches_request_id
        FOREIGN KEY (request_id) REFERENCES service_requests (id),
    ADD CONSTRAINT fk_dispatches_vehicle_id
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id);

ALTER TABLE trips
    ADD CONSTRAINT fk_trips_dispatch_id
        FOREIGN KEY (dispatch_id) REFERENCES dispatches (id);

ALTER TABLE route_revisions
    ADD CONSTRAINT fk_route_revisions_vehicle_id
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id),
    ADD CONSTRAINT fk_route_revisions_dispatch_id
        FOREIGN KEY (dispatch_id) REFERENCES dispatches (id),
    ADD CONSTRAINT fk_route_revisions_map_version_id
        FOREIGN KEY (map_version_id) REFERENCES map_versions (id);

ALTER TABLE vehicle_commands
    ADD CONSTRAINT fk_vehicle_commands_vehicle_id
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id),
    ADD CONSTRAINT fk_vehicle_commands_dispatch_id
        FOREIGN KEY (dispatch_id) REFERENCES dispatches (id),
    ADD CONSTRAINT fk_vehicle_commands_target_place_id
        FOREIGN KEY (target_place_id) REFERENCES places (id),
    ADD CONSTRAINT fk_vehicle_commands_route_revision_id
        FOREIGN KEY (route_revision_id) REFERENCES route_revisions (id);

ALTER TABLE operation_events
    ADD CONSTRAINT fk_operation_events_vehicle_id
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id),
    ADD CONSTRAINT fk_operation_events_request_id
        FOREIGN KEY (request_id) REFERENCES service_requests (id),
    ADD CONSTRAINT fk_operation_events_dispatch_id
        FOREIGN KEY (dispatch_id) REFERENCES dispatches (id),
    ADD CONSTRAINT fk_operation_events_command_id
        FOREIGN KEY (command_id) REFERENCES vehicle_commands (id),
    ADD CONSTRAINT fk_operation_events_place_id
        FOREIGN KEY (place_id) REFERENCES places (id);

ALTER TABLE telemetry_samples
    ADD CONSTRAINT fk_telemetry_samples_vehicle_id
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id),
    ADD CONSTRAINT fk_telemetry_samples_dispatch_id
        FOREIGN KEY (dispatch_id) REFERENCES dispatches (id),
    ADD CONSTRAINT fk_telemetry_samples_route_revision_id
        FOREIGN KEY (route_revision_id) REFERENCES route_revisions (id),
    ADD CONSTRAINT fk_telemetry_samples_command_id
        FOREIGN KEY (command_id) REFERENCES vehicle_commands (id),
    ADD CONSTRAINT fk_telemetry_samples_map_version_id
        FOREIGN KEY (map_version_id) REFERENCES map_versions (id);

ALTER TABLE facility_uses
    ADD CONSTRAINT fk_facility_uses_place_id
        FOREIGN KEY (place_id) REFERENCES places (id),
    ADD CONSTRAINT fk_facility_uses_vehicle_id
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id);

ALTER TABLE mock_payments
    ADD CONSTRAINT fk_mock_payments_trip_id
        FOREIGN KEY (trip_id) REFERENCES trips (id);

ALTER TABLE passenger_checks
    ADD CONSTRAINT fk_passenger_checks_trip_id
        FOREIGN KEY (trip_id) REFERENCES trips (id);

ALTER TABLE cargo_jobs
    ADD CONSTRAINT fk_cargo_jobs_trip_id
        FOREIGN KEY (trip_id) REFERENCES trips (id),
    ADD CONSTRAINT fk_cargo_jobs_attach_place_id
        FOREIGN KEY (attach_place_id) REFERENCES places (id),
    ADD CONSTRAINT fk_cargo_jobs_detach_place_id
        FOREIGN KEY (detach_place_id) REFERENCES places (id);

ALTER TABLE lost_item_reports
    ADD CONSTRAINT fk_lost_item_reports_trip_id
        FOREIGN KEY (trip_id) REFERENCES trips (id);

-- Exclusive open dispatches, facility use, and cart use.

CREATE UNIQUE INDEX ux_dispatches_open_request
    ON dispatches (request_id)
    WHERE ended_at IS NULL;

CREATE UNIQUE INDEX ux_dispatches_open_vehicle
    ON dispatches (vehicle_id)
    WHERE ended_at IS NULL;

CREATE UNIQUE INDEX ux_facility_uses_open_place
    ON facility_uses (place_id)
    WHERE released_at IS NULL;

CREATE UNIQUE INDEX ux_cargo_jobs_open_cart
    ON cargo_jobs (cart_ref)
    WHERE closed_at IS NULL;

-- Operations queries.

CREATE INDEX ix_service_requests_user_history
    ON service_requests (user_id, received_at DESC, id DESC);

CREATE INDEX ix_service_requests_wait_queue
    ON service_requests (status, received_at, id);

CREATE INDEX ix_dispatches_request_history
    ON dispatches (request_id, assigned_at DESC, id DESC);

CREATE INDEX ix_route_revisions_dispatch_history
    ON route_revisions (dispatch_id, planned_at DESC, id DESC)
    WHERE dispatch_id IS NOT NULL;

CREATE INDEX ix_vehicle_commands_vehicle_history
    ON vehicle_commands (vehicle_id, issued_at DESC, id DESC);

CREATE INDEX ix_operation_events_received
    ON operation_events (received_at DESC, id DESC);

CREATE INDEX ix_operation_events_vehicle_history
    ON operation_events (vehicle_id, received_at DESC, id DESC)
    WHERE vehicle_id IS NOT NULL;

CREATE INDEX ix_operation_events_dispatch_history
    ON operation_events (dispatch_id, received_at DESC, id DESC)
    WHERE dispatch_id IS NOT NULL;

CREATE INDEX ix_telemetry_samples_vehicle_latest
    ON telemetry_samples (vehicle_id, received_at DESC, id DESC);

CREATE INDEX ix_telemetry_samples_dispatch_history
    ON telemetry_samples (dispatch_id, received_at DESC, id DESC)
    WHERE dispatch_id IS NOT NULL;
