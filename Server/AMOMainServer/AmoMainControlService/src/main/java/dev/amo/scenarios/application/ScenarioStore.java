package dev.amo.scenarios.application;

import dev.amo.scenarios.domain.ReviewEvidence;
import dev.amo.scenarios.domain.Scenario;
import dev.amo.scenarios.domain.Scenario.Step;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** Persistence port for isolated review runs, independent of the business ledgers they exercise. */
public interface ScenarioStore {
  /** Restricts all unqualified SQL in the current transaction to review-owned relations. */
  void enterReview();

  /** Reserves or retrieves an owned run, activating the shared fixture on the first call. */
  Optional<Run> start(long ownerId, UUID id, Scenario plan);

  /** Returns one run belonging to the active admin. Writes must hold its row lock. */
  Optional<Run> find(long ownerId, UUID id, boolean lock);

  /** Locks the current review selection and reports whether this run may advance. */
  boolean lockCurrent(UUID runId);

  /** Reads identifiable pre-isolation evidence for its original owner. */
  Optional<Run> archived(long ownerId, UUID id);

  /** Returns pre-isolation or isolated evidence without mixing the two ledgers. */
  List<Played> archivedSteps(UUID runId);

  /** Returns recent review runs owned by this administrator, including migrated history. */
  List<Summary> history(long ownerId);

  /** Returns the last created run for the active admin, when there is one. */
  Optional<Run> latest(long ownerId);

  /** Retrieves committed observations in execution order. */
  List<Played> steps(UUID runId);

  /** Selects a mock method on the isolated passenger for the next payment attempt. */
  void useMockPayment(boolean approved);

  /** Links the request created through standard ride intake to its synthetic run. */
  void linkRequest(UUID runId, long requestId);

  /** Persists an observed step exactly once in the current run transaction. */
  void record(UUID runId, int ordinal, Step step, ReviewEvidence evidence);

  /** Stores a synthetic map checkpoint and an audience-facing stage event. */
  void project(Run run, int ordinal, Step step, ReviewEvidence evidence);

  /** IDs provided by the local fixture. requestId is absent until CALL. */
  record Run(
      UUID id,
      Scenario plan,
      long passengerId,
      long vehicleId,
      String vehicleNumber,
      Long requestId) {
    /** Rebinds the observed route outcome without changing the original catalog selection. */
    public Run usingRoute(Scenario route) {
      return new Run(id, route, passengerId, vehicleId, vehicleNumber, requestId);
    }

    /** Produces a stable scoped key for business operations that can be retried. */
    public String key(Step step) {
      return "review:" + id + ":" + step;
    }
  }

  /** Summary of an isolated run or preserved pre-isolation run. */
  record Summary(UUID id, Scenario plan, boolean archived, boolean active) {}

  /** An already committed step and its original observed business values. */
  record Played(Step step, ReviewEvidence evidence) {}
}
