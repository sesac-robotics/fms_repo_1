package dev.amo.replay.adapters;

import dev.amo.replay.application.DepotReplayStore.Cycle;
import dev.amo.replay.domain.DepotReplay.Observation;
import dev.amo.replay.domain.DepotReplay.Phase;
import dev.amo.replay.domain.DepotReplay.Result;
import dev.amo.replay.domain.DepotReplay.Step;
import java.sql.Types;
import java.time.OffsetDateTime;
import java.util.Optional;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

/** Stores the report identity and original outcome with a namespaced producer. */
@Component
@Profile("demo")
class DepotReplayEvents {
  private final JdbcClient jdbc;

  DepotReplayEvents(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  Optional<Result> prior(long cycleId, String key) {
    return jdbc.sql(
            """
            SELECT state_to, occurred_at, details->>'step',
                   (details->>'batteryPercent')::double precision
            FROM operation_events
            WHERE state_scope = 'DEMO_DEPOT' AND event_key = ?
            """)
        .param(key(cycleId, key))
        .query(
            (row, index) ->
                new Result(
                    cycleId,
                    Step.valueOf(row.getString(3)),
                    Phase.valueOf(row.getString(1)),
                    row.getObject(4, Double.class),
                    row.getObject(2, OffsetDateTime.class).toInstant()))
        .optional();
  }

  Result append(Cycle cycle, Observation observation, Phase next) {
    var timestamp =
        jdbc.sql(
                """
                INSERT INTO operation_events
                  (id, vehicle_id, request_id, dispatch_id, place_id, producer, event_key,
                   event_type, state_scope, state_from, state_to, occurred_at, received_at, details)
                VALUES (nextval('amo_record_id'), :vehicle, :request, :dispatch, :place,
                        :source, :key, :type, 'DEMO_DEPOT', :previous, :next,
                        transaction_timestamp(), transaction_timestamp(),
                        jsonb_build_object('step', CAST(:step AS text),
                          'batteryPercent', CAST(:battery AS double precision),
                          'vehicleStatus', CAST(:next AS text), 'connection', 'SIMULATED',
                          'message', CAST(:message AS text)))
                RETURNING occurred_at
                """)
            .param("vehicle", cycle.vehicleId())
            .param("request", cycle.requestId(), Types.BIGINT)
            .param("dispatch", cycle.dispatchId(), Types.BIGINT)
            .param("place", cycle.placeId())
            .param("source", observation.step().source())
            .param("key", key(cycle.id(), observation.key()))
            .param("type", "DEMO_DEPOT_" + observation.step().name())
            .param(
                "previous",
                observation.step() == Step.RETURN_ORDERED ? null : cycle.phase().name(),
                Types.VARCHAR)
            .param("next", next.name())
            .param("step", observation.step().name())
            .param("battery", observation.batteryPercent(), Types.DOUBLE)
            .param("message", observation.step().source() + " " + next.name())
            .query(OffsetDateTime.class)
            .single()
            .toInstant();
    return new Result(
        cycle.id(), observation.step(), next, observation.batteryPercent(), timestamp);
  }

  private static String key(long cycle, String key) {
    return "depot:" + cycle + ":" + key;
  }
}
