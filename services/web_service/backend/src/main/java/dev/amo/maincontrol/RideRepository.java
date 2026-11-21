package dev.amo.maincontrol;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Stores one-way requests using canonical PostgreSQL fields and uniqueness constraints. */
@Repository
class RideRepository {
  private final JdbcClient jdbc;

  RideRepository(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  private static final String READ_RIDES =
      """
      SELECT r.id, p.place_key AS pickup, d.place_key AS destination, r.status, r.received_at,
             v.vehicle_no, a.pickup_eta_at, t.status AS trip_status, r.service_type,
             r.pickup_place_id, r.destination_place_id, r.rental_duration_s
      FROM service_requests r
      JOIN places p ON p.id = r.pickup_place_id
      LEFT JOIN places d ON d.id = r.destination_place_id
      LEFT JOIN LATERAL (
        SELECT id, vehicle_id, pickup_eta_at
        FROM dispatches WHERE request_id = r.id
        ORDER BY assigned_at DESC, id DESC LIMIT 1
      ) a ON TRUE
      LEFT JOIN vehicles v ON v.id = a.vehicle_id
      LEFT JOIN trips t ON t.dispatch_id = a.id
      """;

  Optional<Long> stop(String key) {
    return jdbc.sql(
            """
        SELECT p.id FROM places p JOIN map_versions m ON m.id = p.map_version_id
        WHERE m.version_key = 'v0.2' AND p.place_key = ? AND p.kind = 'STOP'
        """)
        .param(key)
        .query(Long.class)
        .optional();
  }

  boolean insert(long userId, long pickupId, long destinationId, String idempotencyKey) {
    return jdbc.sql(
                """
        INSERT INTO service_requests (id, user_id, idempotency_key, service_type,
          pickup_place_id, destination_place_id, received_at, source_channel, status)
        VALUES (nextval('amo_record_id'), ?, ?, 'ONE_WAY', ?, ?, statement_timestamp(), 'APP',
          'RECEIVED')
        ON CONFLICT (user_id, idempotency_key) DO NOTHING
        """)
            .param(userId)
            .param(idempotencyKey)
            .param(pickupId)
            .param(destinationId)
            .update()
        == 1;
  }

  StoredRide byKey(long userId, String key, long pickupId, long destinationId) {
    return jdbc.sql(READ_RIDES + " WHERE r.user_id = ? AND r.idempotency_key = ?")
        .param(userId)
        .param(key)
        .query(
            (row, i) ->
                new StoredRide(
                    ride(row, i),
                    "ONE_WAY".equals(row.getString("service_type"))
                        && row.getLong("pickup_place_id") == pickupId
                        && Long.valueOf(destinationId)
                            .equals(row.getObject("destination_place_id", Long.class))
                        && row.getObject("rental_duration_s") == null))
        .single();
  }

  List<Ride> history(long userId) {
    return jdbc.sql(
            READ_RIDES + " WHERE r.user_id = ? ORDER BY r.received_at DESC, r.id DESC LIMIT 100")
        .param(userId)
        .query(RideRepository::ride)
        .list();
  }

  void accepted(long requestId) {
    jdbc.sql(
            """
        INSERT INTO operation_events
          (id, request_id, producer, event_key, event_type, occurred_at, received_at, details)
        VALUES (nextval('amo_record_id'), ?, 'MAIN_CONTROL', ?, 'REQUEST_RECEIVED',
          statement_timestamp(), statement_timestamp(), '{"message":"Passenger request received"}')
        """)
        .param(requestId)
        .param("request-received:" + requestId)
        .update();
  }

  private static Ride ride(ResultSet row, int unused) throws SQLException {
    return new Ride(
        row.getLong("id"),
        row.getString("pickup"),
        row.getString("destination"),
        row.getString("status"),
        row.getString("vehicle_no"),
        instant(row, "received_at"),
        instant(row, "pickup_eta_at"),
        row.getString("trip_status"));
  }

  record StoredRide(Ride ride, boolean sameInput) {}

  private static Instant instant(ResultSet row, String column) throws SQLException {
    OffsetDateTime value = row.getObject(column, OffsetDateTime.class);
    return value == null ? null : value.toInstant();
  }
}
