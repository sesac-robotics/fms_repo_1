package dev.amo.replay.application;

import dev.amo.replay.application.TripReplayService.ReplayFailure;
import dev.amo.replay.application.TripReplayStore.Assignment;
import dev.amo.replay.domain.DepotReplay.Observation;
import dev.amo.replay.domain.DepotReplay.Result;
import dev.amo.replay.domain.DepotReplay.Step;
import java.util.Objects;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Checks and records separately the local vehicle, bay, and battery reports. */
@Service
@Profile("demo")
public class DepotReplayService {
  private final DepotReplayStore depot;
  private final TripReplayStore trips;

  DepotReplayService(DepotReplayStore depot, TripReplayStore trips) {
    this.depot = depot;
    this.trips = trips;
  }

  /** Accepts an initial or post-trip observation once, without publishing to a device. */
  @Transactional
  public Result observe(Long requestId, Observation observation) {
    if (!observation.valid()) {
      throw new ReplayFailure("DEMO_DEPOT_OBSERVATION_INVALID");
    }
    Assignment trip = requestId == null ? null : completedTrip(requestId);
    long vehicleId = depot.lockVehicle();
    var cycle = depot.cycle(vehicleId, requestId).orElse(null);
    if (cycle != null) {
      var prior = depot.prior(cycle.id(), observation.key());
      if (prior.isPresent()) {
        Result previous = prior.get();
        if (previous.step() == observation.step()
            && Objects.equals(previous.batteryPercent(), observation.batteryPercent())) {
          return previous;
        }
        throw new ReplayFailure("DEMO_DEPOT_OBSERVATION_CONFLICT");
      }
    }
    var latest = depot.latestDispatch(vehicleId);
    boolean matches =
        trip == null
            ? latest.isEmpty()
            : trip.vehicleId() == vehicleId
                && latest.filter(id -> id == trip.dispatchId()).isPresent();
    if (!matches) {
      throw new ReplayFailure("DEMO_DEPOT_DISPATCH_STALE");
    }
    var phase = observation.next(cycle == null ? null : cycle.phase());
    if (phase == null
        || cycle == null && (trip == null || observation.step() != Step.RETURN_ORDERED)) {
      throw new ReplayFailure("DEMO_DEPOT_STEP_OUT_OF_ORDER");
    }
    if (cycle == null) {
      cycle = depot.startReturn(vehicleId, requestId, trip.dispatchId());
    }
    return depot.save(cycle, observation, phase);
  }

  private Assignment completedTrip(long requestId) {
    trips.lockPassenger(requestId).orElseThrow(() -> new ReplayFailure("DEMO_RIDE_UNAVAILABLE"));
    return trips
        .assignment(requestId)
        .filter(work -> "COMPLETED".equals(work.status()))
        .orElseThrow(() -> new ReplayFailure("DEMO_DEPOT_TRIP_NOT_CLOSED"));
  }
}
