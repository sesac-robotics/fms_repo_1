package dev.amo.control.adapters.persistence;

import dev.amo.control.application.OperationsStore;
import dev.amo.control.domain.Operations.Event;
import dev.amo.control.domain.Operations.Request;
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
        SELECT v.id, v.vehicle_no, v.dispatch_enabled, t.battery_pct, t.x_m, t.y_m,
          t.yaw_rad, t.speed_mps, e.details->>'stopReason' AS stop_reason,
          COALESCE(e.details->>'vehicleStatus', 'UNKNOWN') AS state,
          COALESCE(e.details->>'connection', 'UNKNOWN') AS connection
        FROM vehicles v
        LEFT JOIN LATERAL (
          SELECT battery_pct, x_m, y_m, yaw_rad, speed_mps
          FROM telemetry_samples WHERE vehicle_id = v.id
          ORDER BY received_at DESC, id DESC LIMIT 1
        ) t ON TRUE
        LEFT JOIN LATERAL (
          SELECT details FROM operation_events
          WHERE vehicle_id = v.id
            AND (jsonb_exists(details, 'vehicleStatus') OR jsonb_exists(details, 'connection'))
          ORDER BY received_at DESC, id DESC LIMIT 1
        ) e ON TRUE
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
                    row.getBoolean("dispatch_enabled")))
        .list();
  }

  @Override
  public List<Request> requests() {
    return jdbc.sql(
            """
        SELECT r.id, p.place_key AS pickup, d.place_key AS destination, r.status
        FROM service_requests r JOIN places p ON p.id = r.pickup_place_id
        LEFT JOIN places d ON d.id = r.destination_place_id
        ORDER BY r.received_at DESC, r.id DESC LIMIT 50
        """)
        .query(
            (row, i) ->
                new Request(
                    row.getLong("id"),
                    row.getString("pickup"),
                    row.getString("destination"),
                    row.getString("status")))
        .list();
  }

  @Override
  public List<Event> events() {
    return jdbc.sql(
            """
        SELECT e.id, e.received_at, e.event_type, v.vehicle_no, e.request_id,
          COALESCE(e.details->>'message', e.result_code, e.cause_code, e.producer) AS detail
        FROM operation_events e LEFT JOIN vehicles v ON v.id = e.vehicle_id
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
