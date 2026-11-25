"""Persist experimental observations with transactional PostgreSQL COPY."""

from collections.abc import Iterable
from dataclasses import asdict
from importlib.resources import files
from uuid import UUID, uuid5

import psycopg
from psycopg import Cursor, sql
from psycopg.types.json import Jsonb

from .log_rows import Row, motions, signals, telemetry
from .road_graph import FRAME_ID, INTERSECTION_ID, LANES, MAP_SHA256, MAP_VERSION
from .trial import TICKS_PER_SECOND, VEHICLE_COUNT, Trial


def _copy(cursor: Cursor[tuple[object, ...]], table: str, rows: Iterable[Row]) -> None:
    statement = sql.SQL('COPY amo_learning.{} FROM STDIN').format(sql.Identifier(table))
    with cursor.copy(statement) as writer:
        for row in rows:
            writer.write_row(row)


def _graph(cursor: Cursor[tuple[object, ...]]) -> None:
    cursor.execute(
        'INSERT INTO amo_learning.map_graphs VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',
        (MAP_VERSION, FRAME_ID, MAP_SHA256),
    )
    cursor.execute(
        'SELECT frame_id, image_sha256 FROM amo_learning.map_graphs WHERE map_version = %s',
        (MAP_VERSION,),
    )
    if cursor.fetchone() != (FRAME_ID, MAP_SHA256):
        raise ValueError(
            'The stored graph version has a conflicting frame or map image.'
        )
    nodes = {
        (node.id, node.kind, node.x_m, node.y_m)
        for lane in LANES.values()
        for node in (lane[0].source, *(edge.target for edge in lane))
    }
    edges = {
        (
            edge.id,
            edge.source.id,
            edge.target.id,
            edge.length_m,
            edge.speed_limit_mps,
            edge.intersection,
        )
        for lane in LANES.values()
        for edge in lane
    }
    cursor.executemany(
        'INSERT INTO amo_learning.map_nodes VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
        ((MAP_VERSION, *node) for node in sorted(nodes)),
    )
    cursor.executemany(
        'INSERT INTO amo_learning.map_edges VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
        ((MAP_VERSION, *edge) for edge in sorted(edges)),
    )
    cursor.execute(
        'SELECT node_id, kind, x_m, y_m FROM amo_learning.map_nodes WHERE map_version = %s',
        (MAP_VERSION,),
    )
    if set(cursor.fetchall()) != nodes:
        raise ValueError('The stored graph version has conflicting nodes.')
    cursor.execute(
        """
        SELECT edge_id, source_node_id, target_node_id, length_m, speed_limit_mps, intersection
        FROM amo_learning.map_edges WHERE map_version = %s
        """,
        (MAP_VERSION,),
    )
    if set(cursor.fetchall()) != edges:
        raise ValueError('The stored graph version has conflicting edges.')


def store_experiment(
    dsn: str, experiment_id: UUID, partitions: Iterable[tuple[str, Trial]]
) -> None:
    """Commit all runs together to amo_learning or roll back on any storage error."""
    schema = files('amo_deepfleet').joinpath('schema.sql').read_text(encoding='utf-8')
    with (
        psycopg.connect(dsn, connect_timeout=5) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtext('amo_learning.schema.1'))"
        )
        cursor.execute(sql.SQL(schema))
        _graph(cursor)
        for split, trial in partitions:
            run = uuid5(experiment_id, str(trial.seed))
            cursor.execute(
                """
                INSERT INTO amo_learning.sim_runs
                    (run_id, experiment_id, seed, map_version, intersection_id, partition,
                     duration_ticks, ticks_per_second, vehicle_count, demand_level, signal_plan,
                     simulator_version, admission_policy)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    run,
                    experiment_id,
                    trial.seed,
                    MAP_VERSION,
                    INTERSECTION_ID,
                    split,
                    trial.duration_ticks,
                    TICKS_PER_SECOND,
                    VEHICLE_COUNT,
                    trial.demand_level,
                    Jsonb(asdict(trial.signal)),
                    '1',
                    'earliest-eligible-full-exit',
                ),
            )
            _copy(
                cursor,
                'service_requests',
                (
                    (
                        run,
                        MAP_VERSION,
                        d.vehicle_id,
                        d.tick,
                        d.approach.value,
                        d.goal_node_id,
                        d.load_state,
                    )
                    for d in trial.demand
                ),
            )
            _copy(cursor, 'telemetry_samples', telemetry(run, trial))
            _copy(cursor, 'motion_events', motions(run, trial))
            _copy(cursor, 'signal_phases', signals(run, trial))
            _copy(
                cursor,
                'intersection_grants',
                (
                    (
                        run,
                        p.vehicle_id,
                        p.approach.value,
                        p.request_tick,
                        p.grant_tick,
                        p.entry_tick,
                        p.exit_tick,
                    )
                    for p in trial.passages
                ),
            )
