package dev.amo.scenarios.adapters;

import dev.amo.control.application.ReviewPlaybackSource;
import dev.amo.control.domain.ReviewPlayback;
import dev.amo.control.domain.ReviewPlayback.Checkpoint;
import dev.amo.control.domain.ReviewPlayback.SchematicPoint;
import java.util.UUID;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
@Profile("demo")
class ReviewPlaybackRepository implements ReviewPlaybackSource {
  private final JdbcClient jdbc;

  ReviewPlaybackRepository(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  @Override
  public ReviewPlayback current() {
    return jdbc.sql(
            """
            SELECT c.run_id, v.vehicle_no, t.x_m, t.y_m
            FROM amo_review.demo_scenario_current c
            JOIN amo_review.demo_scenario_runs r ON r.id = c.run_id
            JOIN amo_review.vehicles v ON v.id = r.vehicle_id
            LEFT JOIN LATERAL (
              SELECT x_m, y_m FROM amo_review.telemetry_samples
              WHERE vehicle_id = v.id AND source_epoch = 'review-' || c.run_id
              ORDER BY sample_seq DESC LIMIT 1
            ) t ON true
            WHERE c.singleton
            """)
        .query(
            (row, index) -> {
              Double x = row.getObject(3, Double.class);
              Double y = row.getObject(4, Double.class);
              return new Active(
                  row.getObject(1, UUID.class),
                  row.getString(2),
                  x == null || y == null ? null : new SchematicPoint(x, y));
            })
        .optional()
        .map(
            active ->
                new ReviewPlayback(
                    active.id(),
                    active.vehicle(),
                    jdbc.sql(
                            """
                SELECT step, COALESCE(evidence->>'status', evidence->>'paymentStatus', 'OBSERVED'),
                       evidence->>'event'
                FROM amo_review.demo_scenario_steps WHERE run_id = ? ORDER BY ordinal
                """)
                        .param(active.id())
                        .query(
                            (row, index) ->
                                new Checkpoint(
                                    row.getString(1), row.getString(2), row.getString(3)))
                        .list(),
                    active.point()))
        .orElse(null);
  }

  private record Active(UUID id, String vehicle, SchematicPoint point) {}
}
