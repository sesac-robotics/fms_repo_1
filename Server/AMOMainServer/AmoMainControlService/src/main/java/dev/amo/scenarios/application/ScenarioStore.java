package dev.amo.scenarios.application;

import dev.amo.scenarios.domain.ReviewEvidence;
import dev.amo.scenarios.domain.Scenario;
import dev.amo.scenarios.domain.Scenario.Step;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** Persistence port for isolated review runs, independent of the business ledgers they exercise. */
public interface ScenarioStore {
  /** Reserves or retrieves an owned run, activating the shared fixture on the first call. */
  Optional<Run> start(long ownerId, UUID id, Scenario plan);

  /** Returns one run belonging to the active admin. Writes must hold its row lock. */
  Optional<Run> find(long ownerId, UUID id, boolean lock);

  /** Locks the current review selection and reports whether this run may advance. */
  boolean lockCurrent(UUID runId);

  /** Returns the last created run for the active admin, when there is one. */
  Optional<Run> latest(long ownerId);

  /** Retrieves committed observations in execution order. */
  List<Played> steps(UUID runId);

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
    /** Produces a stable scoped key for business operations that can be retried. */
    public String key(Step step) {
      return "review:" + id + ":" + step;
    }
  }

  /** An already committed step and its original observed business values. */
  record Played(Step step, ReviewEvidence evidence) {}
}
