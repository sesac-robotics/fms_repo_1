package dev.amo.replay.application;

import dev.amo.replay.domain.TripReplay.Step;
import dev.amo.replay.domain.TripReplay.Totals;
import java.time.Instant;
import java.util.Optional;

/** Persists only fictional replay observations within the locked request transaction. */
public interface TripReplayStore {
  /** Locks a one-way request belonging to the fictional demo passenger. */
  Optional<Long> lockPassenger(long requestId);

  /** Returns the captive demo vehicle's existing assignment and trip for this request. */
  Optional<Assignment> assignment(long requestId);

  /** Records a replay assignment, or returns empty when the captive vehicle is busy. */
  Optional<Assignment> assign(long requestId);

  /** Reads the original timestamp and observed totals for a repeated step. */
  Optional<Observation> prior(long requestId, Step step);

  /** Updates the trip, saves necessary evidence and records the observation once. */
  Observation record(long requestId, Assignment assignment, Step step, Totals totals);

  /** Identifies the trip and dispatch affected by observations. */
  record Assignment(long vehicleId, long dispatchId, long tripId, String status) {}

  /** The original time and optional totals of the synthetic observation. */
  record Observation(Instant observedAt, Totals totals) {}
}
