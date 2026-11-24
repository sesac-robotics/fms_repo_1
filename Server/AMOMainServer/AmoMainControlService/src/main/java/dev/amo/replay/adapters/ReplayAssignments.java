package dev.amo.replay.adapters;

import dev.amo.replay.application.TripReplayStore.Assignment;
import java.util.Optional;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

/** Allocates the single isolated replay vehicle while holding its database row lock. */
@Component
@Profile("demo")
class ReplayAssignments {
  private final JdbcClient jdbc;

  ReplayAssignments(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  Optional<Long> lockPassenger(long requestId) {
    return jdbc.sql(
            """
            SELECT r.user_id FROM service_requests r JOIN users u ON r.user_id = u.id
            WHERE r.id = ? AND r.service_type = 'ONE_WAY' AND u.id = 1
              AND u.contact = 'passenger@amo.test' AND r.id >= 10000
            FOR UPDATE OF r
            """)
        .param(requestId)
        .query(Long.class)
        .optional();
  }

  Optional<Assignment> existing(long requestId) {
    return jdbc.sql(
            """
            SELECT d.vehicle_id, d.id AS dispatch_id, t.id AS trip_id, t.status
            FROM dispatches d
            JOIN trips t ON t.dispatch_id = d.id
            WHERE d.request_id = ? AND d.vehicle_id = ?
            ORDER BY d.id DESC LIMIT 1
            """)
        .params(requestId, vehicleFor(requestId))
        .query(
            (row, index) ->
                new Assignment(row.getLong(1), row.getLong(2), row.getLong(3), row.getString(4)))
        .optional();
  }

  private long vehicleFor(long requestId) {
    return jdbc.sql(
            """
            SELECT COALESCE(
                (SELECT vehicle_id FROM demo_scenario_runs WHERE request_id = ?),
                (SELECT id FROM vehicles WHERE vehicle_no = 'DEMO-REPLAY-01'))
            """)
        .param(requestId)
        .query(Long.class)
        .single();
  }

  long lockVehicle(Long scopedVehicle) {
    if (scopedVehicle == null) {
      return jdbc.sql("SELECT id FROM vehicles WHERE vehicle_no = 'DEMO-REPLAY-01' FOR UPDATE")
          .query(Long.class)
          .single();
    }
    return jdbc.sql(
            """
            SELECT v.id FROM vehicles v WHERE v.id = ?
              AND (v.vehicle_no = 'DEMO-REPLAY-01' OR EXISTS (
                SELECT 1 FROM demo_scenario_runs WHERE vehicle_id = v.id))
            FOR UPDATE OF v
            """)
        .param(scopedVehicle)
        .query(Long.class)
        .single();
  }

  Optional<Assignment> create(long requestId) {
    long vehicleId = lockVehicle(vehicleFor(requestId));
    boolean eligible =
        jdbc.sql(
                """
                SELECT NOT EXISTS (
                    SELECT 1 FROM dispatches WHERE vehicle_id = :vehicle AND ended_at IS NULL)
                  AND EXISTS (
                    SELECT 1 FROM demo_depot_cycles c
                    WHERE c.vehicle_id = :vehicle AND c.phase = 'VACATED'
                      AND c.dispatch_id IS NOT DISTINCT FROM (
                        SELECT id FROM dispatches WHERE vehicle_id = :vehicle ORDER BY id DESC LIMIT 1))
                """)
            .param("vehicle", vehicleId)
            .query(Boolean.class)
            .single();
    if (!eligible) {
      return Optional.empty();
    }
    long dispatchId =
        jdbc.sql(
                """
                INSERT INTO dispatches (id, request_id, vehicle_id, status, assigned_at)
                VALUES (nextval('amo_record_id'), ?, ?, 'ASSIGNED', statement_timestamp())
                RETURNING id
                """)
            .params(requestId, vehicleId)
            .query(Long.class)
            .single();
    long tripId =
        jdbc.sql(
                """
                INSERT INTO trips (id, dispatch_id, status)
                VALUES (nextval('amo_record_id'), ?, 'ASSIGNED') RETURNING id
                """)
            .param(dispatchId)
            .query(Long.class)
            .single();
    return Optional.of(new Assignment(vehicleId, dispatchId, tripId, "ASSIGNED"));
  }
}
