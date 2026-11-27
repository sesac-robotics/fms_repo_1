package dev.amo.vision.adapters;

import dev.amo.vision.application.VisionObservations;
import dev.amo.vision.domain.VisionObservation;
import dev.amo.vision.domain.VisionObservation.Outcome;
import dev.amo.vision.domain.VisionObservation.Received;
import dev.amo.vision.domain.VisionObservation.Source;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Applies the latest-only rule atomically in the existing AMO PostgreSQL database. */
@Repository
class JdbcVisionObservations implements VisionObservations {
  private final JdbcClient jdbc;

  JdbcVisionObservations(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  @Override
  public boolean record(VisionObservation value, Instant receivedAt) {
    return jdbc.sql(
            """
            WITH target AS (
                SELECT id FROM vehicles WHERE vehicle_no = :vehicle AND scenario_run_id IS NULL
            ), saved AS (
                INSERT INTO vision_latest
                    (vehicle_id, source, result_id, frame_id, captured_at, processed_at,
                     received_at, outcome, label, confidence)
                SELECT id, :source, :result, :frame, :captured, :processed,
                       :received, :outcome, :label, :confidence FROM target
                ON CONFLICT (vehicle_id, source) DO UPDATE
                SET result_id = EXCLUDED.result_id, frame_id = EXCLUDED.frame_id,
                    captured_at = EXCLUDED.captured_at, processed_at = EXCLUDED.processed_at,
                    received_at = EXCLUDED.received_at, outcome = EXCLUDED.outcome,
                    label = EXCLUDED.label, confidence = EXCLUDED.confidence
                WHERE vision_latest.result_id <> EXCLUDED.result_id
                  AND vision_latest.captured_at < EXCLUDED.captured_at
                RETURNING vehicle_id
            )
            SELECT EXISTS (SELECT 1 FROM target)
            """)
        .param("vehicle", value.vehicleNo())
        .param("source", value.source().name())
        .param("result", value.resultId())
        .param("frame", value.frameId())
        .param("captured", value.capturedAt().atOffset(ZoneOffset.UTC))
        .param("processed", value.processedAt().atOffset(ZoneOffset.UTC))
        .param("received", receivedAt.atOffset(ZoneOffset.UTC))
        .param("outcome", value.outcome().name())
        .param("label", value.label())
        .param("confidence", value.confidence())
        .query(Boolean.class)
        .single();
  }

  @Override
  public List<Received> latest() {
    return jdbc.sql(
            """
            SELECT v.vehicle_no, s.* FROM vision_latest s
            JOIN vehicles v ON v.id = s.vehicle_id
            WHERE v.scenario_visible AND v.scenario_run_id IS NULL
            ORDER BY v.vehicle_no, s.source
            """)
        .query(
            (row, index) ->
                new Received(
                    new VisionObservation(
                        row.getObject("result_id", UUID.class),
                        row.getString("vehicle_no"),
                        Source.valueOf(row.getString("source")),
                        row.getString("frame_id"),
                        row.getObject("captured_at", OffsetDateTime.class).toInstant(),
                        row.getObject("processed_at", OffsetDateTime.class).toInstant(),
                        Outcome.valueOf(row.getString("outcome")),
                        row.getString("label"),
                        row.getObject("confidence", Double.class)),
                    row.getObject("received_at", OffsetDateTime.class).toInstant()))
        .list();
  }
}
