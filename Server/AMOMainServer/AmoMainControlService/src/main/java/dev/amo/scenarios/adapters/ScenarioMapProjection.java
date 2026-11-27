package dev.amo.scenarios.adapters;

import dev.amo.scenarios.application.ScenarioStore.Run;
import dev.amo.scenarios.domain.ReviewEvidence;
import dev.amo.scenarios.domain.ReviewPosition;
import dev.amo.scenarios.domain.Scenario.Step;
import java.time.ZoneOffset;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

/** Persists demo-only map evidence and stage events in the review transaction. */
@Component
@Profile("demo")
class ScenarioMapProjection {
  private final JdbcClient jdbc;

  ScenarioMapProjection(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  void store(Run run, int ordinal, Step step, ReviewEvidence evidence) {
    var when = evidence.observedAt().atOffset(ZoneOffset.UTC);
    jdbc.sql(
            """
            INSERT INTO operation_events
                (id, vehicle_id, request_id, producer, event_key, event_type, received_at,
                 occurred_at, result_code)
            VALUES (nextval('amo_record_id'), ?, ?, 'DEMO_REVIEW', ?, ?, statement_timestamp(), ?, ?)
            """)
        .param(run.vehicleId())
        .param(run.requestId())
        .param(run.key(step))
        .param("DEMO_REVIEW_" + step)
        .param(when)
        .param(evidence.status())
        .update();
    ReviewPosition.at(run.plan(), step)
        .ifPresent(
            point ->
                jdbc.sql(
                        """
                INSERT INTO telemetry_samples
                    (id, vehicle_id, map_version_id, source_epoch, sample_seq, observed_at,
                     received_at, x_m, y_m)
                SELECT nextval('amo_record_id'), ?, id, ?, ?, ?, statement_timestamp(), ?, ?
                FROM map_versions WHERE version_key = 'v0.2'
                """)
                    .params(
                        run.vehicleId(),
                        "review-" + run.id(),
                        ordinal,
                        when,
                        point.xMeters(),
                        point.yMeters())
                    .update());
  }
}
