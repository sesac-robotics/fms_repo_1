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
import org.springframework.transaction.support.TransactionSynchronizationManager;

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
  public void enterReview() {
    if (!TransactionSynchronizationManager.isActualTransactionActive()) {
      throw new IllegalStateException("Review storage requires a transaction");
    }
    jdbc.sql("SET LOCAL search_path TO amo_review, pg_catalog").update();
  }

  @Override
  public Optional<Run> start(long ownerId, UUID id, Scenario plan) {
    Optional<UUID> previous = fixtures.lockCurrent();
    jdbc.sql(
            """
            INSERT INTO demo_scenario_runs (id, owner_id, passenger_id, plan)
            VALUES (?, ?, 1, ?)
            ON CONFLICT (id) DO NOTHING
            """)
        .params(id, ownerId, plan.name())
        .update();
    var reserved = find(ownerId, id, true);
    if (reserved.isPresent() && reserved.get().vehicleId() == 0) {
      jdbc.sql("UPDATE demo_scenario_runs SET vehicle_id = ? WHERE id = ?")
          .params(fixtures.activate(previous, id), id)
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
  public boolean lockCurrent(UUID runId) {
    return fixtures.lockCurrent().filter(runId::equals).isPresent();
  }

  @Override
  public Optional<Run> archived(long ownerId, UUID id) {
    String legacyRuns =
        RUNS.replace("FROM demo_", "FROM public.demo_")
            .replace("JOIN vehicles", "JOIN public.vehicles");
    return jdbc.sql(legacyRuns + " AND r.id = ?")
        .params(ownerId, id)
        .query(ScenarioRepository::run)
        .optional();
  }

  @Override
  public List<Played> archivedSteps(UUID runId) {
    return readSteps(runId, "public.demo_scenario_steps");
  }

  @Override
  public List<Summary> history(long ownerId) {
    return jdbc.sql(
            """
            SELECT r.id, r.plan, false, r.closed_at IS NULL, r.created_at
            FROM amo_review.demo_scenario_runs r WHERE r.owner_id = ?
            UNION ALL
            SELECT r.id, r.plan, true, false, r.created_at
            FROM public.demo_scenario_runs r WHERE r.owner_id = ?
            ORDER BY created_at DESC, id DESC LIMIT 100
            """)
        .params(ownerId, ownerId)
        .query(
            (row, index) ->
                new Summary(
                    row.getObject(1, UUID.class),
                    Scenario.valueOf(row.getString(2)),
                    row.getBoolean(3),
                    row.getBoolean(4)))
        .list();
  }

  @Override
  public Optional<Run> latest(long ownerId) {
    return jdbc.sql(RUNS + " AND r.closed_at IS NULL ORDER BY r.created_at DESC, r.id DESC LIMIT 1")
        .param(ownerId)
        .query(ScenarioRepository::run)
        .optional();
  }

  @Override
  public List<Played> steps(UUID runId) {
    return readSteps(runId, "amo_review.demo_scenario_steps");
  }

  private List<Played> readSteps(UUID runId, String table) {
    return jdbc.sql("SELECT step, evidence FROM " + table + " WHERE run_id = ? ORDER BY ordinal")
        .param(runId)
        .query((row, index) -> new Played(Step.valueOf(row.getString(1)), decode(row.getString(2))))
        .list();
  }

  @Override
  public void useMockPayment(boolean approved) {
    jdbc.sql("UPDATE amo_review.users SET mock_payment_method_ref = ? WHERE id = 1")
        .param(approved ? "demo-approved" : "demo-declined")
        .update();
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
