-- The proposal points to a canonical route revision. Hardware command delivery remains disabled.
CREATE TABLE ride_route_changes (
    revision_id bigint PRIMARY KEY REFERENCES route_revisions(id),
    trip_id bigint NOT NULL REFERENCES trips(id),
    target_place_id bigint NOT NULL REFERENCES places(id),
    delta_minor bigint NOT NULL CHECK (delta_minor >= 0),
    accepted_key text CHECK (length(accepted_key) BETWEEN 1 AND 128),
    command_id bigint UNIQUE REFERENCES vehicle_commands(id),
    applied_at timestamptz
);

CREATE INDEX ix_ride_route_changes_trip ON ride_route_changes (trip_id, revision_id DESC);
