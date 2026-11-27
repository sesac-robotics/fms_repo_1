package dev.amo.fares.adapters;

import dev.amo.fares.application.RouteChangeStore;
import dev.amo.fares.domain.DemoTariff;
import dev.amo.fares.domain.RouteChange.Proposal;
import dev.amo.fares.domain.RouteChange.Report;
import dev.amo.fares.domain.RouteChange.Scope;
import dev.amo.fares.domain.RouteChange.Status;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.Optional;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Stores proposed terms, active route identity and acceptance in PostgreSQL. */
@Repository
@Profile("demo")
class RouteChangeRepository implements RouteChangeStore {
  private static final String PROPOSALS =
      """
      SELECT q.*, r.id AS revision, r.status AS revision_status, r.vehicle_id, r.dispatch_id,
             p.place_key, c.delta_minor, c.accepted_key, c.applied_at, c.command_id, v.connection_epoch
      FROM ride_route_changes c
      JOIN route_revisions r ON r.id = c.revision_id
      JOIN ride_fare_quotes q ON q.route_revision_id = r.id
      JOIN places p ON p.id = c.target_place_id
      LEFT JOIN vehicle_commands v ON v.id = c.command_id
      WHERE c.trip_id = ?
      """;

  private final JdbcClient jdbc;
  private final ReplayRouteCommands commands;

  RouteChangeRepository(JdbcClient jdbc, ReplayRouteCommands commands) {
    this.jdbc = jdbc;
    this.commands = commands;
  }

  @Override
  public Optional<Target> target(long requestId, String destination) {
    return jdbc.sql(
            """
            SELECT d.id, d.map_version_id, d.place_key,
                   sqrt(power(p.x_m - d.x_m, 2) + power(p.y_m - d.y_m, 2)) AS schematic_m
            FROM service_requests r JOIN places p ON p.id = r.pickup_place_id
            JOIN places d ON d.map_version_id = p.map_version_id AND d.kind = 'STOP'
            WHERE r.id = ? AND d.place_key = ? AND d.id <> p.id
            """)
        .params(requestId, destination)
        .query(
            (row, index) ->
                new Target(
                    row.getLong(1),
                    row.getLong(2),
                    row.getString(3),
                    DemoTariff.schematicEstimate(row.getDouble(4))))
        .optional()
        .filter(target -> target.estimate() != null);
  }

  @Override
  public Optional<Proposal> latest(long tripId) {
    return select(tripId, "");
  }

  @Override
  public Optional<Proposal> applied(long tripId) {
    return select(tripId, " AND r.status = 'APPLIED'");
  }

  private Optional<Proposal> select(long tripId, String filter) {
    return jdbc.sql(PROPOSALS + filter + " ORDER BY r.id DESC LIMIT 1")
        .param(tripId)
        .query(RouteChangeRepository::proposal)
        .optional();
  }

  @Override
  public long appliedPayments(long tripId) {
    return jdbc.sql(
            """
            SELECT COALESCE(SUM(p.amount_minor), 0)
            FROM ride_route_changes c JOIN route_revisions r ON r.id = c.revision_id
            JOIN ride_fare_quotes q ON q.route_revision_id = r.id
            JOIN ride_payment_attempts p ON p.quote_id = q.id AND p.result = 'SUCCEEDED'
            WHERE c.trip_id = ? AND r.status = 'APPLIED'
            """)
        .param(tripId)
        .query(Long.class)
        .single();
  }

  @Override
  public Proposal propose(long requestId, Work work, Target target, long deltaMinor, Instant now) {
    String key = "demo-trip:" + work.tripId();
    var time = now.truncatedTo(ChronoUnit.MICROS).atOffset(ZoneOffset.UTC);
    long revision =
        jdbc.sql(
                """
                INSERT INTO route_revisions (id, vehicle_id, dispatch_id, map_version_id, route_key,
                    revision_no, status, planned_distance_m, reason_code, planned_at)
                SELECT nextval('amo_record_id'), ?, ?, ?, ?, COALESCE(MAX(revision_no), 0) + 1,
                       'PROPOSED', ?, 'DEMO_CHANGE', ?
                FROM route_revisions WHERE route_key = ? RETURNING id
                """)
            .params(
                work.vehicleId(),
                work.dispatchId(),
                target.mapVersionId(),
                key,
                target.estimate().distanceMeters(),
                time,
                key)
            .query(Long.class)
            .single();
    jdbc.sql(
            """
            INSERT INTO ride_route_changes (revision_id, trip_id, target_place_id, delta_minor)
            VALUES (?, ?, ?, ?)
            """)
        .params(revision, work.tripId(), target.id(), deltaMinor)
        .update();
    jdbc.sql(
            """
            INSERT INTO ride_fare_quotes (request_id, trip_id, route_revision_id, distance_m,
                duration_s, tariff_version, amount_minor, currency_code, quoted_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """)
        .params(
            requestId,
            work.tripId(),
            revision,
            target.estimate().distanceMeters(),
            target.estimate().durationSeconds(),
            DemoTariff.VERSION,
            DemoTariff.price(target.estimate()),
            DemoTariff.CURRENCY,
            time,
            time.plus(DemoTariff.VALIDITY))
        .update();
    return latest(work.tripId()).orElseThrow();
  }

  @Override
  public void accept(Proposal proposal, String key, Instant now) {
    jdbc.sql("UPDATE ride_route_changes SET accepted_key = ? WHERE revision_id = ?")
        .params(key, proposal.revisionId())
        .update();
    jdbc.sql("UPDATE ride_fare_quotes SET accepted_at = ? WHERE id = ?")
        .params(now.atOffset(ZoneOffset.UTC), proposal.quote().id())
        .update();
  }

  @Override
  public Scope issue(long requestId, Work work, Proposal proposal, Instant now) {
    return commands.issue(requestId, work, proposal, now);
  }

  @Override
  public void report(long requestId, Scope scope, Report report, Instant now) {
    commands.report(requestId, scope, report, now);
  }

  private static Proposal proposal(ResultSet row, int index) throws SQLException {
    long revision = row.getLong("revision");
    Long commandId = row.getObject("command_id", Long.class);
    Scope scope =
        commandId == null
            ? null
            : new Scope(
                row.getLong("vehicle_id"),
                row.getLong("dispatch_id"),
                revision,
                commandId,
                row.getString("connection_epoch"));
    var appliedAt = row.getObject("applied_at", OffsetDateTime.class);
    return new Proposal(
        revision,
        row.getLong("trip_id"),
        row.getString("place_key"),
        row.getLong("delta_minor"),
        FareRows.quote(row, index),
        Status.valueOf(row.getString("revision_status")),
        row.getString("accepted_key"),
        scope,
        appliedAt == null ? null : appliedAt.toInstant());
  }
}
