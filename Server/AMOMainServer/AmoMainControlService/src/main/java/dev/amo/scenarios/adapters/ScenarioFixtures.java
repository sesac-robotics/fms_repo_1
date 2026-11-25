package dev.amo.scenarios.adapters;

import java.util.Optional;
import java.util.UUID;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

/** Owns the shared demo vehicle and serializes changes to the active review. */
@Component
@Profile("demo")
class ScenarioFixtures {
  private final JdbcClient jdbc;

  ScenarioFixtures(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  Optional<UUID> lockCurrent() {
    return jdbc.sql("SELECT run_id FROM demo_scenario_current WHERE singleton FOR UPDATE")
        .query((row, index) -> Optional.ofNullable(row.getObject(1, UUID.class)))
        .single();
  }

  long activate(Optional<UUID> previous, UUID next) {
    long vehicle = previous.map(this::retire).orElseGet(this::createVehicle);
    jdbc.sql(
            """
            INSERT INTO demo_depot_cycles (vehicle_id, place_id, phase)
            SELECT ?, p.id, 'INITIAL' FROM places p JOIN map_versions m ON m.id = p.map_version_id
            WHERE m.version_key = 'v0.2' AND p.place_key = ?
            """)
        .params(vehicle, bayKey(vehicle))
        .update();
    jdbc.sql("UPDATE vehicles SET scenario_visible = true, scenario_run_id = ? WHERE id = ?")
        .params(next, vehicle)
        .update();
    jdbc.sql("UPDATE demo_scenario_current SET run_id = ? WHERE singleton").param(next).update();
    return vehicle;
  }

  private long retire(UUID run) {
    long vehicle =
        jdbc.sql(
                """
                SELECT v.id FROM vehicles v JOIN demo_scenario_runs r ON r.vehicle_id = v.id
                WHERE r.id = ? FOR UPDATE OF v
                """)
            .param(run)
            .query(Long.class)
            .single();
    // End open synthetic work without altering committed steps or deleting any ledger rows.
    jdbc.sql(
            """
            WITH closed AS (
                UPDATE dispatches SET status = 'CANCELLED', ended_at = transaction_timestamp()
                WHERE vehicle_id = ? AND ended_at IS NULL RETURNING id
            )
            UPDATE trips SET status = 'CANCELLED', ended_at = transaction_timestamp(),
                outcome_code = 'SCENARIO_RUN_SUPERSEDED'
            WHERE dispatch_id IN (SELECT id FROM closed) AND ended_at IS NULL
            """)
        .param(vehicle)
        .update();
    jdbc.sql(
            """
            UPDATE service_requests SET status = 'CANCELLED'
            WHERE id = (SELECT request_id FROM demo_scenario_runs WHERE id = ?)
              AND status NOT IN ('CANCELLED', 'COMPLETED', 'ARRIVED')
            """)
        .param(run)
        .update();
    jdbc.sql(
            """
            UPDATE facility_uses SET status = 'RELEASED', released_at = transaction_timestamp()
            WHERE vehicle_id = ? AND released_at IS NULL
            """)
        .param(vehicle)
        .update();
    jdbc.sql(
            "UPDATE demo_depot_cycles SET scenario_archived = true WHERE vehicle_id = ? AND NOT scenario_archived")
        .param(vehicle)
        .update();
    return vehicle;
  }

  private long createVehicle() {
    long vehicle = jdbc.sql("SELECT nextval('amo_record_id')").query(Long.class).single();
    jdbc.sql(
            """
            INSERT INTO vehicles (id, vehicle_no, dispatch_enabled, updated_at)
            VALUES (?, ?, false, statement_timestamp())
            """)
        .params(vehicle, "DEMO-REVIEW-" + vehicle)
        .update();
    jdbc.sql(
            """
            INSERT INTO places (id, map_version_id, place_key, name, kind, x_m, y_m)
            SELECT nextval('amo_record_id'), id, ?, 'Scenario review bay', 'CHARGING_BAY', 0, 0
            FROM map_versions WHERE version_key = 'v0.2'
            """)
        .param(bayKey(vehicle))
        .update();
    return vehicle;
  }

  private static String bayKey(long vehicle) {
    return "DEMO-REVIEW-BAY-" + vehicle;
  }
}
