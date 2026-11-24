package dev.amo.fares.application;

import dev.amo.fares.application.FareFailure.Reason;
import dev.amo.fares.application.FareStore.Request;
import dev.amo.fares.domain.Fare.Attempt;
import dev.amo.fares.domain.Fare.PaymentStatus;
import dev.amo.fares.domain.RouteChange.Proposal;
import dev.amo.fares.domain.RouteChange.Status;
import dev.amo.fares.domain.RouteChange.View;
import dev.amo.replay.application.TripReplayStore;
import java.time.Instant;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Accepts a current change quote and records its required mock difference under one lock. */
@Service
@Profile("demo")
public class RouteAcceptance {
  private final FareStore fares;
  private final RouteChangeStore routes;
  private final TripReplayStore trips;

  RouteAcceptance(FareStore fares, RouteChangeStore routes, TripReplayStore trips) {
    this.fares = fares;
    this.routes = routes;
    this.trips = trips;
  }

  /** Reads the proposed and effective routes for a request owned by the signed-in passenger. */
  @Transactional
  public View read(long passengerId, long requestId, Instant now) {
    Request request = owned(passengerId, requestId);
    Proposal current = current(requestId);
    return view(request, current, latest(current), now);
  }

  /**
   * Accepts the same currently proposed quote once. Positive differences use the provided replay
   * key and the server's registered mock method.
   */
  @Transactional
  public View accept(long passengerId, long requestId, long quoteId, String key, Instant now) {
    Request request = owned(passengerId, requestId);
    Proposal current = current(requestId);
    if (current.quote().id() != quoteId) {
      throw new FareFailure(Reason.FARE_QUOTE_CONFLICT);
    }
    var prior = fares.attempt(quoteId, key);
    if (prior.isPresent()) {
      return view(request, current, prior.get(), now);
    }
    Attempt attempt = latest(current);
    if (current.authorizedBy(attempt)) {
      return view(request, current, attempt, now);
    }
    if (current.status() != Status.PROPOSED || !changeable(request.status())) {
      throw new FareFailure(Reason.FARE_PAYMENT_CLOSED);
    }
    if (!current.quote().usableAt(now)) {
      return view(request, current, attempt, now);
    }
    if (current.acceptedKey() == null) {
      routes.accept(current, key, now);
      current = current(requestId);
    }
    if (current.deltaMinor() > 0 && request.method() != null && !request.method().isBlank()) {
      attempt =
          fares.saveAttempt(
              current.quote(),
              key,
              request.method(),
              current.deltaMinor(),
              FareService.outcome(request),
              now);
    }
    return view(request, current, attempt, now);
  }

  static boolean changeable(String status) {
    return "ON_TRIP".equals(status) || "STOPPED_WAIT".equals(status);
  }

  private Request owned(long passengerId, long requestId) {
    return fares
        .lock(requestId, passengerId)
        .orElseThrow(() -> new FareFailure(Reason.RIDE_NOT_FOUND));
  }

  private Proposal current(long requestId) {
    return trips
        .assignment(requestId)
        .flatMap(work -> routes.latest(work.tripId()))
        .orElseThrow(() -> new FareFailure(Reason.ROUTE_CHANGE_NOT_FOUND));
  }

  private Attempt latest(Proposal current) {
    return fares.latestAttempt(current.quote().id()).orElse(null);
  }

  private View view(Request request, Proposal current, Attempt attempt, Instant now) {
    var applied = routes.applied(current.tripId()).orElse(null);
    PaymentStatus status = PaymentStatus.QUOTED;
    if (attempt != null) {
      status = attempt.status();
    } else if (current.deltaMinor() == 0 && current.acceptedKey() != null) {
      status = PaymentStatus.NOT_REQUIRED;
    } else if (!current.quote().usableAt(now)) {
      status = PaymentStatus.QUOTE_EXPIRED;
    } else if (current.deltaMinor() > 0
        && (request.method() == null || request.method().isBlank())) {
      status = PaymentStatus.METHOD_MISSING;
    }
    return new View(
        current.revisionId(),
        current.destination(),
        current.quote(),
        current.deltaMinor(),
        current.status(),
        current.acceptedKey() != null,
        status,
        attempt,
        applied == null ? request.destination() : applied.destination(),
        applied == null ? null : applied.revisionId(),
        applied == null ? null : applied.appliedAt());
  }
}
