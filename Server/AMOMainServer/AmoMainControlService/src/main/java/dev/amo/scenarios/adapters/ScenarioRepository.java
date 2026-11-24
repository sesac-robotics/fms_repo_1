package dev.amo.scenarios.adapters;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.amo.scenarios.application.ScenarioStore;
import dev.amo.scenarios.domain.ReviewEvidence;
import dev.amo.scenarios.domain.Scenario;
import dev.amo.scenarios.domain.Scenario.Step;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
@Profile("demo")
class ScenarioRepository implements ScenarioStore {
  private static final String RUNS =
      """
      SELECT r.id, r.plan, r.passenger_id, r.vehicle_id, v.vehicle_no, r.request_id
      FROM demo_scenario_runs r LEFT JOIN vehicles v ON v.id = r.vehicle_id
      WHERE r.owner_id = ?
      """;

  private final JdbcClient jdbc;
  private final ScenarioFixtures fixtures;
  private final ObjectMapper json;
  private final ScenarioMapProjection projection;

  ScenarioRepository(
      JdbcClient jdbc,
      ScenarioFixtures fixtures,
      ObjectMapper json,
      ScenarioMapProjection projection) {
    this.jdbc = jdbc;
    this.fixtures = fixtures;
    this.json = json;
    this.projection = projection;
  }

  @Override
  public Optional<Run> start(long ownerId, UUID id, Scenario plan) {
    jdbc.sql(
            """
            INSERT INTO demo_scenario_runs (id, owner_id, passenger_id, plan)
            SELECT ?, ?, profile_user_id, ? FROM amo_accounts
            WHERE email = 'passenger@amo.test' AND role = 'PASSENGER' AND status = 'ACTIVE'
            ON CONFLICT (id) DO NOTHING
            """)
        .params(id, ownerId, plan.name())
        .update();
    var reserved = find(ownerId, id, true);
    if (reserved.isPresent() && reserved.get().vehicleId() == 0) {
      jdbc.sql("UPDATE demo_scenario_runs SET vehicle_id = ? WHERE id = ?")
          .params(fixtures.createVehicle(), id)
          .update();
      return find(ownerId, id, false);
    }
    return reserved;
  }

  @Override
  public Optional<Run> find(long ownerId, UUID id, boolean lock) {
    return jdbc.sql(RUNS + " AND r.id = ?" + (lock ? " FOR UPDATE OF r" : ""))
        .params(ownerId, id)
        .query(ScenarioRepository::run)
        .optional();
  }

  @Override
  public Optional<Run> latest(long ownerId) {
    return jdbc.sql(RUNS + " ORDER BY r.created_at DESC, r.id DESC LIMIT 1")
        .param(ownerId)
        .query(ScenarioRepository::run)
        .optional();
  }

  @Override
  public List<Played> steps(UUID runId) {
    return jdbc.sql(
            """
            SELECT step, evidence FROM demo_scenario_steps WHERE run_id = ? ORDER BY ordinal
            """)
        .param(runId)
        .query((row, index) -> new Played(Step.valueOf(row.getString(1)), decode(row.getString(2))))
        .list();
  }

  @Override
  public void linkRequest(UUID runId, long requestId) {
    jdbc.sql("UPDATE demo_scenario_runs SET request_id = ? WHERE id = ? AND request_id IS NULL")
        .params(requestId, runId)
        .update();
  }

  @Override
  public void record(UUID runId, int ordinal, Step step, ReviewEvidence evidence) {
    jdbc.sql(
            """
            INSERT INTO demo_scenario_steps (run_id, ordinal, step, evidence)
            VALUES (?, ?, ?, CAST(? AS jsonb))
            """)
        .params(runId, ordinal, step.name(), encode(evidence))
        .update();
  }

  @Override
  public void project(Run run, int ordinal, Step step, ReviewEvidence evidence) {
    projection.store(run, ordinal, step, evidence);
  }

  private static Run run(ResultSet row, int index) throws SQLException {
    return new Run(
        row.getObject(1, UUID.class),
        Scenario.valueOf(row.getString(2)),
        row.getLong(3),
        row.getLong(4),
        row.getString(5),
        row.getObject(6, Long.class));
  }

  private String encode(ReviewEvidence evidence) {
    try {
      return json.writeValueAsString(evidence);
    } catch (JsonProcessingException error) {
      throw new IllegalStateException("Cannot encode scenario evidence", error);
    }
  }

  private ReviewEvidence decode(String evidence) {
    try {
      return json.readValue(evidence, ReviewEvidence.class);
    } catch (JsonProcessingException error) {
      throw new IllegalStateException("Cannot read scenario evidence", error);
    }
  }
}
