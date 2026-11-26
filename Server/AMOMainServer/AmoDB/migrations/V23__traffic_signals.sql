-- Latest reported state per intersection signal (SR-027), as relayed by the ROS 2 bridge.
CREATE TABLE signal_latest (
    signal_id text PRIMARY KEY CHECK (signal_id ~ '^[A-Z0-9-]{1,32}$'),
    phase text NOT NULL CHECK (
        phase IN ('NORTH_GREEN', 'NORTH_YELLOW', 'ALL_RED', 'EAST_GREEN', 'EAST_YELLOW')
    ),
    mode text NOT NULL CHECK (mode IN ('AUTO', 'HOLD')),
    hold_target text CHECK (hold_target IN ('NORTH_GREEN', 'EAST_GREEN', 'ALL_RED')),
    remaining_ms integer NOT NULL CHECK (remaining_ms >= 0),
    north_green_ms integer NOT NULL,
    east_green_ms integer NOT NULL,
    yellow_ms integer NOT NULL,
    all_red_ms integer NOT NULL,
    plan_pending boolean NOT NULL,
    device_seq bigint NOT NULL,
    device_uptime_ms bigint NOT NULL,
    last_command text NOT NULL,
    command_result text NOT NULL,
    received_at timestamptz NOT NULL
);

-- Staff commands waiting for, or already handed to, the bridge.
CREATE TABLE signal_commands (
    id bigserial PRIMARY KEY,
    signal_id text NOT NULL CHECK (signal_id ~ '^[A-Z0-9-]{1,32}$'),
    command text NOT NULL,
    requested_by bigint NOT NULL,
    requested_at timestamptz NOT NULL,
    delivered_at timestamptz
);

CREATE INDEX signal_commands_pending ON signal_commands (signal_id, id)
    WHERE delivered_at IS NULL;
