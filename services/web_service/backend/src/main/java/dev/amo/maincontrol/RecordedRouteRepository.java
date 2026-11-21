package dev.amo.maincontrol;

import java.time.OffsetDateTime;
import java.util.List;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Reads a bounded position history for the latest actually started trip of a request. */
@Repository
class RecordedRouteRepository {
  private final JdbcClient jdbc;

  RecordedRouteRepository(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  boolean requestExists(long requestId) {
    return jdbc.sql("SELECT EXISTS (SELECT 1 FROM service_requests WHERE id = :requestId)")
        .param("requestId", requestId)
        .query(Boolean.class)
        .single();
  }

  List<RecordedRoute.Sample> samples(long requestId) {
    return jdbc.sql(
            """
        WITH selected_trip AS (
          SELECT d.id AS dispatch_id, d.vehicle_id, t.started_at,
            LEAST(t.ended_at, d.ended_at) AS ended_at
          FROM dispatches d
          JOIN trips t ON t.dispatch_id = d.id
          WHERE d.request_id = :requestId AND t.started_at IS NOT NULL
          ORDER BY t.started_at DESC, t.id DESC LIMIT 1
        )
        SELECT m.version_key, m.frame_id, s.source_epoch, s.sample_seq, s.observed_at, s.x_m, s.y_m
        FROM selected_trip t
        JOIN telemetry_samples s ON s.dispatch_id = t.dispatch_id AND s.vehicle_id = t.vehicle_id
        LEFT JOIN map_versions m ON m.id = s.map_version_id
        WHERE s.observed_at >= t.started_at AND (t.ended_at IS NULL OR s.observed_at <= t.ended_at)
        ORDER BY s.observed_at DESC, s.id DESC LIMIT :limit
        """)
        .param("requestId", requestId)
        .param("limit", RecordedRoute.MAX_SAMPLES + 1)
        .query(
            (row, index) ->
                new RecordedRoute.Sample(
                    row.getString("version_key"),
                    row.getString("frame_id"),
                    row.getString("source_epoch"),
                    row.getLong("sample_seq"),
                    row.getObject("observed_at", OffsetDateTime.class).toInstant(),
                    row.getObject("x_m", Double.class),
                    row.getObject("y_m", Double.class)))
        .list();
  }
}
