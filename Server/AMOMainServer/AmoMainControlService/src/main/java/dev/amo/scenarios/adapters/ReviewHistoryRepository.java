package dev.amo.scenarios.adapters;

import dev.amo.scenarios.application.ReviewHistory;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
@Profile("demo")
class ReviewHistoryRepository implements ReviewHistory {
  private static final List<String> REVIEW_HISTORY_TABLES =
      List.of(
          "demo_scenario_steps",
          "demo_scenario_runs",
          "demo_depot_cycles",
          "facility_uses",
          "telemetry_samples",
          "operation_events",
          "ride_fare_settlements",
          "passenger_checks",
          "ride_payment_attempts",
          "ride_fare_quotes",
          "ride_route_changes",
          "vehicle_commands",
          "route_revisions",
          "trips",
          "dispatches",
          "service_requests");

  private final JdbcClient jdbc;
  private final ScenarioFixtures fixtures;

  ReviewHistoryRepository(JdbcClient jdbc, ScenarioFixtures fixtures) {
    this.jdbc = jdbc;
    this.fixtures = fixtures;
  }

  @Override
  public Counts counts() {
    return jdbc.sql(
            """
            SELECT (SELECT count(*) FROM amo_review.demo_scenario_runs),
                   (SELECT count(*) FROM amo_review.demo_scenario_steps), run_id
            FROM amo_review.demo_scenario_current WHERE singleton
            """)
        .query(
            (row, index) -> new Counts(row.getInt(1), row.getInt(2), row.getObject(3, UUID.class)))
        .single();
  }

  @Override
  public boolean close(long owner, UUID expected) {
    if (fixtures.lockCurrent().filter(expected::equals).isEmpty()) {
      return false;
    }
    boolean owned =
        jdbc.sql("SELECT EXISTS (SELECT 1 FROM demo_scenario_runs WHERE id = ? AND owner_id = ?)")
            .params(expected, owner)
            .query(Boolean.class)
            .single();
    if (owned) {
      fixtures.retire(expected);
      releaseCurrent();
    }
    return owned;
  }

  @Override
  public Optional<Counts> clear(Counts expected) {
    fixtures.lockCurrent();
    if (!counts().equals(expected)) {
      return Optional.empty();
    }
    releaseCurrent();
    for (String table : REVIEW_HISTORY_TABLES) {
      jdbc.sql("DELETE FROM amo_review." + table).update();
    }
    jdbc.sql("UPDATE amo_review.vehicles SET scenario_visible = false, scenario_run_id = NULL")
        .update();
    return Optional.of(expected);
  }

  private void releaseCurrent() {
    jdbc.sql("UPDATE demo_scenario_current SET run_id = NULL WHERE singleton").update();
  }
}
