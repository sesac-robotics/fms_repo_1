-- Version 1 of the opt-in experiment store. All objects are isolated from AMO operations.
CREATE SCHEMA IF NOT EXISTS amo_learning;

CREATE TABLE IF NOT EXISTS amo_learning.map_graphs (
    map_version text PRIMARY KEY,
    frame_id text NOT NULL,
    image_sha256 text NOT NULL CHECK (image_sha256 ~ '^[a-f0-9]{64}$')
);

CREATE TABLE IF NOT EXISTS amo_learning.map_nodes (
    map_version text NOT NULL REFERENCES amo_learning.map_graphs,
    node_id text NOT NULL,
    kind text NOT NULL,
    x_m double precision NOT NULL,
    y_m double precision NOT NULL,
    PRIMARY KEY (map_version, node_id)
);

CREATE TABLE IF NOT EXISTS amo_learning.map_edges (
    map_version text NOT NULL,
    edge_id text NOT NULL,
    source_node_id text NOT NULL,
    target_node_id text NOT NULL,
    length_m double precision NOT NULL CHECK (length_m > 0),
    speed_limit_mps double precision NOT NULL CHECK (speed_limit_mps > 0),
    intersection boolean NOT NULL,
    PRIMARY KEY (map_version, edge_id),
    FOREIGN KEY (map_version, source_node_id) REFERENCES amo_learning.map_nodes,
    FOREIGN KEY (map_version, target_node_id) REFERENCES amo_learning.map_nodes
);

CREATE TABLE IF NOT EXISTS amo_learning.sim_runs (
    run_id uuid PRIMARY KEY,
    experiment_id uuid NOT NULL,
    seed integer NOT NULL CHECK (seed >= 0),
    map_version text NOT NULL REFERENCES amo_learning.map_graphs,
    intersection_id text NOT NULL,
    partition text NOT NULL CHECK (partition IN ('train', 'test')),
    duration_ticks integer NOT NULL CHECK (duration_ticks > 0),
    ticks_per_second integer NOT NULL CHECK (ticks_per_second > 0),
    vehicle_count integer NOT NULL CHECK (vehicle_count = 4),
    demand_level text NOT NULL CHECK (demand_level IN ('LIGHT', 'MEDIUM', 'HEAVY')),
    signal_plan jsonb NOT NULL,
    simulator_version text NOT NULL,
    admission_policy text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT statement_timestamp(),
    UNIQUE (experiment_id, seed),
    UNIQUE (run_id, map_version)
);

CREATE TABLE IF NOT EXISTS amo_learning.service_requests (
    run_id uuid NOT NULL,
    map_version text NOT NULL,
    vehicle_id integer NOT NULL CHECK (vehicle_id BETWEEN 1 AND 4),
    request_tick integer NOT NULL CHECK (request_tick >= 0),
    approach text NOT NULL CHECK (approach IN ('NORTH', 'EAST')),
    goal_node_id text NOT NULL,
    load_state text NOT NULL CHECK (load_state IN ('EMPTY', 'PASSENGER')),
    PRIMARY KEY (run_id, vehicle_id, request_tick),
    FOREIGN KEY (run_id, map_version) REFERENCES amo_learning.sim_runs (run_id, map_version),
    FOREIGN KEY (map_version, goal_node_id) REFERENCES amo_learning.map_nodes
);

CREATE TABLE IF NOT EXISTS amo_learning.telemetry_samples (
    run_id uuid NOT NULL,
    map_version text NOT NULL,
    vehicle_id integer NOT NULL CHECK (vehicle_id BETWEEN 1 AND 4),
    tick integer NOT NULL CHECK (tick >= 0),
    x_m double precision NOT NULL,
    y_m double precision NOT NULL,
    edge_id text NOT NULL,
    edge_progress double precision NOT NULL CHECK (edge_progress BETWEEN 0 AND 1),
    node_id text,
    goal_node_id text,
    load_state text NOT NULL CHECK (load_state IN ('EMPTY', 'PASSENGER')),
    motion text NOT NULL,
    PRIMARY KEY (run_id, vehicle_id, tick),
    FOREIGN KEY (run_id, map_version) REFERENCES amo_learning.sim_runs (run_id, map_version),
    FOREIGN KEY (map_version, edge_id) REFERENCES amo_learning.map_edges,
    FOREIGN KEY (map_version, goal_node_id) REFERENCES amo_learning.map_nodes,
    FOREIGN KEY (map_version, node_id) REFERENCES amo_learning.map_nodes
);

CREATE TABLE IF NOT EXISTS amo_learning.motion_events (
    run_id uuid NOT NULL,
    map_version text NOT NULL,
    vehicle_id integer NOT NULL CHECK (vehicle_id BETWEEN 1 AND 4),
    start_tick integer NOT NULL CHECK (start_tick >= 0),
    until_tick integer NOT NULL CHECK (until_tick > start_tick),
    motion text NOT NULL,
    edge_id text NOT NULL,
    goal_node_id text,
    load_state text NOT NULL,
    wait_reason text,
    blocked_by integer CHECK (blocked_by BETWEEN 1 AND 4 AND blocked_by <> vehicle_id),
    PRIMARY KEY (run_id, vehicle_id, start_tick),
    FOREIGN KEY (run_id, map_version) REFERENCES amo_learning.sim_runs (run_id, map_version),
    FOREIGN KEY (map_version, edge_id) REFERENCES amo_learning.map_edges,
    FOREIGN KEY (map_version, goal_node_id) REFERENCES amo_learning.map_nodes,
    CHECK ((motion = 'WAITING') = (wait_reason IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS amo_learning.signal_phases (
    run_id uuid NOT NULL REFERENCES amo_learning.sim_runs,
    start_tick integer NOT NULL CHECK (start_tick >= 0),
    until_tick integer NOT NULL CHECK (until_tick > start_tick),
    phase text NOT NULL CHECK (phase IN ('NORTH_GREEN', 'EAST_GREEN', 'ALL_RED')),
    exit_closed boolean NOT NULL,
    PRIMARY KEY (run_id, start_tick)
);

CREATE TABLE IF NOT EXISTS amo_learning.intersection_grants (
    run_id uuid NOT NULL REFERENCES amo_learning.sim_runs,
    vehicle_id integer NOT NULL CHECK (vehicle_id BETWEEN 1 AND 4),
    approach text NOT NULL CHECK (approach IN ('NORTH', 'EAST')),
    request_tick integer NOT NULL CHECK (request_tick >= 0),
    grant_tick integer CHECK (grant_tick >= request_tick),
    entry_tick integer CHECK (entry_tick IS NULL OR (grant_tick IS NOT NULL AND entry_tick >= grant_tick)),
    exit_tick integer CHECK (exit_tick IS NULL OR (entry_tick IS NOT NULL AND exit_tick > entry_tick)),
    PRIMARY KEY (run_id, vehicle_id, request_tick)
);
