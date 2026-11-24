package dev.amo.fares.adapters;

import dev.amo.fares.application.RouteChangeStore.Work;
import dev.amo.fares.domain.RouteChange.Proposal;
import dev.amo.fares.domain.RouteChange.Report;
import dev.amo.fares.domain.RouteChange.Scope;
import java.time.Instant;
import java.time.ZoneOffset;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

/** Stores isolated command evidence. No adapter sends these rows to a real vehicle. */
@Component
@Profile("demo")
class ReplayRouteCommands {
  private final JdbcClient jdbc;

  ReplayRouteCommands(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  Scope issue(long requestId, Work work, Proposal proposal, Instant now) {
    String epoch = "demo-dispatch-" + work.dispatchId();
    long id =
        jdbc.sql(
                """
                INSERT INTO vehicle_commands (id, vehicle_id, dispatch_id, target_place_id,
                    route_revision_id, command_type, status, issuer_ref, connection_epoch, issued_at)
                SELECT nextval('amo_record_id'), ?, ?, target_place_id, revision_id,
                       'DEMO_ROUTE_CHANGE', 'ISSUED', 'DEMO_REPLAY', ?, ?
                FROM ride_route_changes WHERE revision_id = ? RETURNING id
                """)
            .params(
                work.vehicleId(),
                work.dispatchId(),
                epoch,
                now.atOffset(ZoneOffset.UTC),
                proposal.revisionId())
            .query(Long.class)
            .single();
    jdbc.sql("UPDATE ride_route_changes SET command_id = ? WHERE revision_id = ?")
        .params(id, proposal.revisionId())
        .update();
    var scope = new Scope(work.vehicleId(), work.dispatchId(), proposal.revisionId(), id, epoch);
    saveEvent(requestId, scope, "ISSUED", now);
    return scope;
  }

  void report(long requestId, Scope scope, Report report, Instant now) {
    var time = now.atOffset(ZoneOffset.UTC);
    jdbc.sql(
            """
            UPDATE vehicle_commands
            SET status = :status,
                settled_at = CASE WHEN :status = 'ACKNOWLEDGED' THEN settled_at ELSE :time END
            WHERE id = :id
            """)
        .param("status", report.name())
        .param("time", time)
        .param("id", scope.commandId())
        .update();
    if (report == Report.APPLIED) {
      jdbc.sql("UPDATE ride_route_changes SET applied_at = ? WHERE revision_id = ?")
          .params(time, scope.revisionId())
          .update();
    }
    saveEvent(requestId, scope, report.name(), now);
  }

  private void saveEvent(long requestId, Scope scope, String status, Instant now) {
    jdbc.sql("UPDATE route_revisions SET status = ? WHERE id = ?")
        .params(status, scope.revisionId())
        .update();
    jdbc.sql(
            """
            INSERT INTO operation_events
                (id, vehicle_id, request_id, dispatch_id, command_id, producer, event_key, event_type,
                 occurred_at, received_at, details, result_code)
            VALUES (nextval('amo_record_id'), :vehicle, :request, :dispatch, :command, 'DEMO_IF04',
                  :key, :type, :time, statement_timestamp(),
                  jsonb_build_object('message', CAST(:message AS text),
                                     'revisionId', CAST(:revision AS bigint)), :status)
            """)
        .param("vehicle", scope.vehicleId())
        .param("request", requestId)
        .param("dispatch", scope.dispatchId())
        .param("command", scope.commandId())
        .param("revision", scope.revisionId())
        .param("key", scope.commandId() + ":" + status)
        .param("type", "DEMO_ROUTE_" + status)
        .param("time", now.atOffset(ZoneOffset.UTC))
        .param("status", status)
        .param("message", "Route revision " + scope.revisionId() + ": " + status)
        .update();
  }
}
