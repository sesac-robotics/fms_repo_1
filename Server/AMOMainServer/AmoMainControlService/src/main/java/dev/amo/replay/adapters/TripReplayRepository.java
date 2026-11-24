package dev.amo.replay.adapters;

import dev.amo.replay.application.TripReplayStore;
import dev.amo.replay.domain.TripReplay.Step;
import dev.amo.replay.domain.TripReplay.Totals;
import java.sql.Types;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.Optional;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/**
 * Records fictional trip observations and keeps real hardware command tables outside this replay.
 */
@Repository
@Profile("demo")
class TripReplayRepository implements TripReplayStore {
  private final JdbcClient jdbc;
  private final ReplayAssignments assignments;

  TripReplayRepository(JdbcClient jdbc, ReplayAssignments assignments) {
    this.jdbc = jdbc;
    this.assignments = assignments;
  }

  @Override
  public Optional<Long> lockPassenger(long requestId) {
    return assignments.lockPassenger(requestId);
  }

  @Override
  public Optional<Assignment> assignment(long requestId) {
    return assignments.existing(requestId);
  }

  @Override
  public Optional<Assignment> assign(long requestId) {
    return assignments.create(requestId);
  }

  @Override
  public Optional<Observation> prior(long requestId, Step step) {
    return jdbc.sql(
            """
            SELECT occurred_at, (details->>'distanceMeters')::double precision AS meters,
                   (details->>'elapsedSeconds')::integer AS seconds
            FROM operation_events WHERE producer = 'DEMO_REPLAY' AND event_key = ?
            """)
        .param(key(requestId, step))
        .query(
            (row, index) ->
                new Observation(
                    row.getObject(1, OffsetDateTime.class).toInstant(),
                    step == Step.DESTINATION_STOP
                        ? new Totals(row.getDouble("meters"), row.getInt("seconds"))
                        : null))
        .optional();
  }

  @Override
  public Observation record(long requestId, Assignment work, Step step, Totals totals) {
    if (step != Step.ASSIGN) {
      updateTrip(work.tripId(), step, totals);
    }
    if (step == Step.BOARD || step == Step.ALIGHT) {
      recordPassengerCheck(work.tripId(), key(requestId, step), step);
    }
    jdbc.sql("UPDATE service_requests SET status = ? WHERE id = ?")
        .params(step.status(), requestId)
        .update();
    if (step == Step.ALIGHT) {
      jdbc.sql(
              """
              UPDATE dispatches SET status = 'COMPLETED', ended_at = transaction_timestamp()
              WHERE id = ?
              """)
          .param(work.dispatchId())
          .update();
    }
    return new Observation(appendEvent(requestId, work, step, totals), totals);
  }

  private void updateTrip(long tripId, Step step, Totals totals) {
    jdbc.sql(
            """
            UPDATE trips
            SET status = :status,
                started_at = CASE WHEN :status = 'ON_TRIP' THEN COALESCE(started_at, transaction_timestamp())
                                  ELSE started_at END,
                ended_at = CASE WHEN :status = 'COMPLETED' THEN transaction_timestamp() ELSE ended_at END,
                distance_m = COALESCE(:meters, distance_m),
                elapsed_s = COALESCE(:seconds, elapsed_s)
            WHERE id = :trip
            """)
        .param("status", step.status())
        .param("meters", totals == null ? null : totals.distanceMeters(), Types.DOUBLE)
        .param("seconds", totals == null ? null : totals.elapsedSeconds(), Types.INTEGER)
        .param("trip", tripId)
        .update();
  }

  private void recordPassengerCheck(long tripId, String key, Step step) {
    jdbc.sql(
            """
            INSERT INTO passenger_checks
              (id, trip_id, check_kind, result, provider_result_key, checked_at, received_at)
            VALUES (nextval('amo_record_id'), ?, ?, 'CONFIRMED', ?,
                    transaction_timestamp(), transaction_timestamp())
            """)
        .params(tripId, step == Step.BOARD ? "BOARDING" : "ALIGHTING", key)
        .update();
  }

  private Instant appendEvent(long requestId, Assignment work, Step step, Totals totals) {
    return jdbc.sql(
            """
            INSERT INTO operation_events
              (id, vehicle_id, request_id, dispatch_id, place_id, producer, event_key, event_type,
               occurred_at, received_at, details)
            VALUES (nextval('amo_record_id'), :vehicle, :request, :dispatch,
                    CASE WHEN :type = 'DEMO_DESTINATION_STOP_CONFIRMED' THEN COALESCE(
                      (SELECT c.target_place_id FROM ride_route_changes c
                       JOIN route_revisions r ON r.id = c.revision_id
                       WHERE c.trip_id = :trip AND r.status = 'APPLIED'
                       ORDER BY c.revision_id DESC LIMIT 1),
                      (SELECT destination_place_id FROM service_requests WHERE id = :request))
                    END, 'DEMO_REPLAY', :key,
                    :type, transaction_timestamp(), transaction_timestamp(),
                    jsonb_build_object('vehicleStatus', CAST(:phase AS text),
                      'connection', 'SIMULATED', 'distanceMeters', CAST(:meters AS double precision),
                      'elapsedSeconds', CAST(:seconds AS integer)))
            RETURNING occurred_at
            """)
        .param("vehicle", work.vehicleId())
        .param("request", requestId)
        .param("dispatch", work.dispatchId())
        .param("trip", work.tripId())
        .param("key", key(requestId, step))
        .param("type", step.event())
        .param("phase", step.status())
        .param("meters", totals == null ? null : totals.distanceMeters(), Types.DOUBLE)
        .param("seconds", totals == null ? null : totals.elapsedSeconds(), Types.INTEGER)
        .query(OffsetDateTime.class)
        .single()
        .toInstant();
  }

  private static String key(long requestId, Step step) {
    return requestId + ":" + step.name();
  }
}
