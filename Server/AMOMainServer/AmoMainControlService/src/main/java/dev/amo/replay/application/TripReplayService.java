package dev.amo.replay.application;

import dev.amo.fares.application.FareService;
import dev.amo.fares.application.RouteChangeStore;
import dev.amo.fares.domain.Fare.Receipt;
import dev.amo.fares.domain.RouteChange;
import dev.amo.replay.domain.TripReplay.Step;
import dev.amo.replay.domain.TripReplay.Totals;
import java.time.Instant;
import java.util.Objects;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Drives one synthetic request at a time without creating or sending vehicle commands. */
@Service
@Profile("demo")
public class TripReplayService {
  private final TripReplayStore store;
  private final FareService fares;
  private final RouteChangeStore routes;

  TripReplayService(TripReplayStore store, FareService fares, RouteChangeStore routes) {
    this.store = store;
    this.fares = fares;
    this.routes = routes;
  }

  /** Applies a step once and returns its original time for an exact replay. */
  @Transactional
  public Result observe(long requestId, Step step, Totals totals) {
    if (step == Step.REDEPART_ORIGINAL) {
      throw new ReplayFailure("DEMO_REVIEW_STEP_ONLY");
    }
    return apply(requestId, step, totals);
  }

  /** Records explicit review resumption on the original route after a failed change. */
  @Transactional
  public Result resumeOriginal(long requestId) {
    return apply(requestId, Step.REDEPART_ORIGINAL, null);
  }

  private Result apply(long requestId, Step step, Totals totals) {
    if ((step == Step.DESTINATION_STOP) != (totals != null)) {
      throw new ReplayFailure("DEMO_TOTALS_REQUIRED_ONLY_AT_DESTINATION");
    }
    long owner =
        store
            .lockPassenger(requestId)
            .orElseThrow(() -> new ReplayFailure("DEMO_RIDE_UNAVAILABLE"));
    var assignment = store.assignment(requestId).orElse(null);
    var prior = store.prior(requestId, step);
    if (prior.isPresent()) {
      var previous = prior.get();
      if (!Objects.equals(previous.totals(), totals)) {
        throw new ReplayFailure("DEMO_OBSERVATION_CONFLICT");
      }
      return result(requestId, owner, assignment.tripId(), step, previous.observedAt());
    }
    if (!step.follows(assignment == null ? null : assignment.status())) {
      throw new ReplayFailure("DEMO_STEP_OUT_OF_ORDER");
    }
    if (step == Step.ASSIGN) {
      fares.requirePrepayment(owner, requestId);
      assignment =
          store.assign(requestId).orElseThrow(() -> new ReplayFailure("DEMO_VEHICLE_BUSY"));
    }
    if (step == Step.REDEPART) {
      Instant stoppedAt = store.prior(requestId, Step.STOP_WAIT).orElseThrow().observedAt();
      routes
          .applied(assignment.tripId())
          .filter(route -> route.appliedAt().isAfter(stoppedAt))
          .orElseThrow(() -> new ReplayFailure("DEMO_APPLIED_CHANGE_REQUIRED_FOR_REDEPARTURE"));
    }
    if (step == Step.REDEPART_ORIGINAL) {
      routes
          .latest(assignment.tripId())
          .filter(route -> route.status() == RouteChange.Status.FAILED)
          .orElseThrow(() -> new ReplayFailure("DEMO_FAILED_CHANGE_REQUIRED_FOR_ORIGINAL_ROUTE"));
    }
    var observation = store.record(requestId, assignment, step, totals);
    return result(requestId, owner, assignment.tripId(), step, observation.observedAt());
  }

  private Result result(long requestId, long owner, long tripId, Step step, Instant observedAt) {
    Receipt receipt =
        step == Step.ALIGHT ? fares.finalizeTrip(owner, requestId, tripId, observedAt) : null;
    return new Result(tripId, step.status(), observedAt, receipt);
  }

  /** Response for a stored synthetic observation. The instant is in UTC. */
  public record Result(long tripId, String status, Instant observedAt, Receipt receipt) {}

  /** A rejected synthetic observation, with a stable client-facing error code. */
  public static final class ReplayFailure extends RuntimeException {
    /** Creates a rejection from an application-defined code. */
    public ReplayFailure(String code) {
      super(code);
    }
  }
}
