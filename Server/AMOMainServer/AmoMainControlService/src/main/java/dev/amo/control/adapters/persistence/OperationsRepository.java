package dev.amo.control.adapters.persistence;

import dev.amo.control.application.OperationsStore;
import dev.amo.control.domain.Operations.Event;
import dev.amo.control.domain.Operations.Request;
import dev.amo.control.domain.Operations.Sample;
import dev.amo.control.domain.Operations.Trial;
import dev.amo.control.domain.Operations.Vehicle;
import java.time.OffsetDateTime;
import java.util.List;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Reads only stored state and measurements; no command path is exposed. */
@Repository
class OperationsRepository implements OperationsStore {
  private final JdbcClient jdbc;

  OperationsRepository(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  @Override
  public boolean ready() {
    try {
      jdbc.sql("SELECT 1").query(Integer.class).single();
      return true;
    } catch (DataAccessException failure) {
      return false;
    }
  }

  @Override
  public List<Vehicle> vehicles() {
    return jdbc.sql(
            """
        SELECT v.id, v.vehicle_no, v.dispatch_enabled, COALESCE(t.battery_pct, depot.battery_pct) AS battery_pct, t.x_m, t.y_m,
          t.yaw_rad, t.speed_mps, t.source_epoch, t.sample_seq, t.received_at,
          e.details->>'stopReason' AS stop_reason,
          COALESCE(e.details->>'vehicleStatus', 'UNKNOWN') AS state,
          COALESCE(e.details->>'connection', 'UNKNOWN') AS connection
        FROM vehicles v
        LEFT JOIN LATERAL (
          SELECT battery_pct, x_m, y_m, yaw_rad, speed_mps, source_epoch, sample_seq, received_at
          FROM telemetry_samples WHERE vehicle_id = v.id
            AND (v.scenario_run_id IS NULL OR source_epoch = 'review-' || v.scenario_run_id)
          ORDER BY received_at DESC, id DESC LIMIT 1
        ) t ON TRUE
        LEFT JOIN LATERAL (
          SELECT details FROM operation_events
          WHERE vehicle_id = v.id
            AND (jsonb_exists(details, 'vehicleStatus') OR jsonb_exists(details, 'connection'))
          ORDER BY received_at DESC, id DESC LIMIT 1
        ) e ON TRUE
        LEFT JOIN LATERAL (
          SELECT battery_pct FROM demo_depot_cycles
          WHERE vehicle_id = v.id AND NOT scenario_archived
          ORDER BY id DESC LIMIT 1
        ) depot ON TRUE
        WHERE v.scenario_visible
        ORDER BY v.vehicle_no
        """)
        .query(
            (row, i) ->
                new Vehicle(
                    row.getLong("id"),
                    row.getString("vehicle_no"),
                    row.getString("state"),
                    row.getObject("battery_pct", Double.class),
                    row.getString("connection"),
                    row.getObject("x_m", Double.class),
                    row.getObject("y_m", Double.class),
                    row.getObject("yaw_rad", Double.class),
                    row.getObject("speed_mps", Double.class),
                    row.getString("stop_reason"),
                    row.getBoolean("dispatch_enabled"),
                    row.getString("source_epoch") == null
                        ? null
                        : new Sample(
                            row.getString("source_epoch"),
                            row.getLong("sample_seq"),
                            row.getObject("received_at", OffsetDateTime.class).toInstant())))
        .list();
  }

  @Override
  public List<Request> requests() {
    return jdbc.sql(
            """
        SELECT r.id, p.place_key AS pickup, d.place_key AS destination, r.status,
               COALESCE(applied.target, d.place_key) AS effective_destination,
               applied.revision_id
        FROM (SELECT * FROM service_requests ORDER BY received_at DESC, id DESC LIMIT 50) r
        JOIN places p ON p.id = r.pickup_place_id
        LEFT JOIN places d ON d.id = r.destination_place_id
        """
                + RideProgressReads.APPLIED_ROUTE
                + " ORDER BY r.received_at DESC, r.id DESC")
        .query(
            (row, i) ->
                new Request(
                    row.getLong("id"),
                    row.getString("pickup"),
                    row.getString("destination"),
                    row.getString("status"),
                    row.getString("effective_destination"),
                    row.getObject("revision_id", Long.class)))
        .list();
  }

  @Override
  public List<Event> events() {
    return jdbc.sql(
            """
        SELECT e.id, e.received_at, e.event_type, v.vehicle_no, e.request_id,
          COALESCE(e.details->>'message', e.result_code, e.cause_code, e.producer) AS detail
        FROM operation_events e LEFT JOIN vehicles v ON v.id = e.vehicle_id
        WHERE e.producer <> 'DEMO_REVIEW' OR (v.scenario_visible
          AND e.event_key LIKE 'review:' || v.scenario_run_id || ':%')
        ORDER BY e.received_at DESC, e.id DESC LIMIT 50
        """)
        .query(
            (row, i) ->
                new Event(
                    row.getLong("id"),
                    row.getObject("received_at", OffsetDateTime.class).toInstant(),
                    row.getString("event_type"),
                    row.getString("vehicle_no"),
                    row.getString("detail"),
                    row.getObject("request_id", Long.class)))
        .list();
  }

  @Override
  public List<Trial> tests() {
    return jdbc.sql("SELECT name, passed, total, latency_ms FROM amo_test_results ORDER BY name")
        .query(
            (row, i) ->
                new Trial(
                    row.getString("name"),
                    row.getInt("passed"),
                    row.getInt("total"),
                    row.getInt("latency_ms")))
        .list();
  }
}
