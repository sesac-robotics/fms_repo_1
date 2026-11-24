package dev.amo.scenarios.adapters;

import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

/**
 * Allocates a separate non-dispatchable vehicle, bay and initial cycle in the review transaction.
 */
@Component
@Profile("demo")
class ScenarioFixtures {
  private final JdbcClient jdbc;

  ScenarioFixtures(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  long createVehicle() {
    long vehicle = jdbc.sql("SELECT nextval('amo_record_id')").query(Long.class).single();
    jdbc.sql(
            """
            INSERT INTO vehicles (id, vehicle_no, dispatch_enabled, updated_at)
            VALUES (?, ?, false, statement_timestamp())
            """)
        .params(vehicle, "DEMO-REVIEW-" + vehicle)
        .update();
    long place =
        jdbc.sql(
                """
                INSERT INTO places (id, map_version_id, place_key, name, kind, x_m, y_m)
                SELECT nextval('amo_record_id'), id, ?, 'Scenario review bay', 'CHARGING_BAY', 0, 0
                FROM map_versions WHERE version_key = 'v0.2' RETURNING id
                """)
            .param("DEMO-REVIEW-BAY-" + vehicle)
            .query(Long.class)
            .single();
    jdbc.sql("INSERT INTO demo_depot_cycles (vehicle_id, place_id, phase) VALUES (?, ?, 'INITIAL')")
        .params(vehicle, place)
        .update();
    return vehicle;
  }
}
