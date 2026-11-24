package dev.amo.replay.application;

import dev.amo.replay.domain.DepotReplay.Observation;
import dev.amo.replay.domain.DepotReplay.Phase;
import dev.amo.replay.domain.DepotReplay.Result;
import java.util.Optional;

/** Persists replay evidence with the isolated vehicle locked for the whole transaction. */
public interface DepotReplayStore {
  /** Locks the isolated synthetic vehicle and returns its internal ID. */
  long lockVehicle();

  /** Finds a cycle for the supplied request, or the initial facility cycle if requestId is null. */
  Optional<Cycle> cycle(long vehicleId, Long requestId);

  /** Allocates the bay cycle for a completed dispatch, with no device command. */
  Cycle startReturn(long vehicleId, long requestId, long dispatchId);

  /** Reads an event by its original key within the same cycle. */
  Optional<Result> prior(long cycleId, String key);

  /** Applies the validated state and facility update, then records the observation. */
  Result save(Cycle cycle, Observation observation, Phase next);

  /** Identifies the latest dispatch formed by this replay vehicle, if one exists. */
  Optional<Long> latestDispatch(long vehicleId);

  /** Canonical facility and dispatch references for one replay batch. */
  record Cycle(
      long id,
      long vehicleId,
      Long requestId,
      Long dispatchId,
      long placeId,
      Long useId,
      Phase phase) {}
}
