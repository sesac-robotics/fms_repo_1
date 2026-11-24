package dev.amo.replay.adapters;

import dev.amo.replay.application.DepotReplayStore;
import dev.amo.replay.domain.DepotReplay.Observation;
import dev.amo.replay.domain.DepotReplay.Phase;
import dev.amo.replay.domain.DepotReplay.Result;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Types;
import java.util.Optional;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Persists independent vehicle and facility facts for the local demo. */
@Repository
@Profile("demo")
class DepotReplayRepository implements DepotReplayStore {
  private final JdbcClient jdbc;
  private final ReplayAssignments assignments;
  private final DepotReplayEvents events;

  DepotReplayRepository(JdbcClient jdbc, ReplayAssignments assignments, DepotReplayEvents events) {
    this.jdbc = jdbc;
    this.assignments = assignments;
    this.events = events;
  }

  @Override
  public long lockVehicle(Long vehicleId) {
    return assignments.lockVehicle(vehicleId);
  }

  @Override
  public Optional<Long> latestDispatch(long vehicleId) {
    return jdbc.sql("SELECT id FROM dispatches WHERE vehicle_id = ? ORDER BY id DESC LIMIT 1")
        .param(vehicleId)
        .query(Long.class)
        .optional();
  }

  @Override
  public Optional<Cycle> cycle(long vehicleId, Long requestId) {
    return jdbc.sql(
            """
            SELECT * FROM demo_depot_cycles WHERE vehicle_id = :vehicle
              AND request_id IS NOT DISTINCT FROM CAST(:request AS bigint)
            """)
        .param("vehicle", vehicleId)
        .param("request", requestId, Types.BIGINT)
        .query(DepotReplayRepository::cycle)
        .optional();
  }

  @Override
  public Cycle startReturn(long vehicleId, long requestId, long dispatchId) {
    return jdbc.sql(
            """
            INSERT INTO demo_depot_cycles (vehicle_id, dispatch_id, request_id, place_id, phase)
            SELECT vehicle_id, ?, ?, place_id, 'RETURNING'
            FROM demo_depot_cycles WHERE vehicle_id = ? AND dispatch_id IS NULL RETURNING *
            """)
        .params(dispatchId, requestId, vehicleId)
        .query(DepotReplayRepository::cycle)
        .single();
  }

  @Override
  public Optional<Result> prior(long cycleId, String key) {
    return events.prior(cycleId, key);
  }

  @Override
  public Result save(Cycle cycle, Observation observation, Phase next) {
    Long use = cycle.useId();
    if (next == Phase.OCCUPIED) {
      use = occupy(cycle);
    } else if (next == Phase.VACATED) {
      release(use);
    }
    jdbc.sql(
            """
            UPDATE demo_depot_cycles
            SET phase = :phase, facility_use_id = :use,
                battery_pct = COALESCE(:battery, battery_pct),
                charge_started_at = CASE WHEN :step = 'CHARGE_STARTED'
                                         THEN transaction_timestamp() ELSE charge_started_at END
            WHERE id = :cycle
            """)
        .param("cycle", cycle.id())
        .param("phase", next.name())
        .param("step", observation.step().name())
        .param("use", use, Types.BIGINT)
        .param("battery", observation.batteryPercent(), Types.DOUBLE)
        .update();
    return events.append(cycle, observation, next);
  }

  private long occupy(Cycle cycle) {
    return jdbc.sql(
            """
            INSERT INTO facility_uses
              (id, place_id, vehicle_id, status, allocated_at, entered_at, reason_code)
            VALUES (nextval('amo_record_id'), ?, ?, 'OCCUPIED',
                    transaction_timestamp(), transaction_timestamp(), 'DEMO_CHARGING')
            RETURNING id
            """)
        .params(cycle.placeId(), cycle.vehicleId())
        .query(Long.class)
        .single();
  }

  private void release(long use) {
    jdbc.sql(
            """
            UPDATE facility_uses SET status = 'RELEASED', released_at = transaction_timestamp()
            WHERE id = ? AND released_at IS NULL
            """)
        .param(use)
        .update();
  }

  private static Cycle cycle(ResultSet row, int index) throws SQLException {
    return new Cycle(
        row.getLong("id"),
        row.getLong("vehicle_id"),
        row.getObject("request_id", Long.class),
        row.getObject("dispatch_id", Long.class),
        row.getLong("place_id"),
        row.getObject("facility_use_id", Long.class),
        Phase.valueOf(row.getString("phase")));
  }
}
