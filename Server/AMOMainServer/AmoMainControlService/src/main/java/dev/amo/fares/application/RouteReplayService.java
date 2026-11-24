package dev.amo.fares.application;

import dev.amo.fares.application.RouteChangeStore.Work;
import dev.amo.fares.domain.DemoTariff;
import dev.amo.fares.domain.Fare.PaymentStatus;
import dev.amo.fares.domain.RouteChange.Proposal;
import dev.amo.fares.domain.RouteChange.Report;
import dev.amo.fares.domain.RouteChange.Scope;
import dev.amo.fares.domain.RouteChange.Status;
import dev.amo.replay.application.TripReplayService.ReplayFailure;
import dev.amo.replay.application.TripReplayStore;
import java.time.Instant;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Exercises the route command boundary with explicit synthetic IF-04 reports. */
@Service
@Profile("demo")
public class RouteReplayService {
  private final TripReplayStore trips;
  private final FareStore ledger;
  private final FareService fares;
  private final RouteChangeStore routes;

  RouteReplayService(
      TripReplayStore trips, FareStore ledger, FareService fares, RouteChangeStore routes) {
    this.trips = trips;
    this.ledger = ledger;
    this.fares = fares;
    this.routes = routes;
  }

  /** Proposes a supported local destination without altering the effective route. */
  @Transactional
  public Proposal propose(long requestId, String destination, Instant now) {
    Work work = active(requestId);
    Proposal latest = routes.latest(work.tripId()).orElse(null);
    if (latest != null && !latest.status().terminal()) {
      if (latest.destination().equals(destination)) {
        return latest;
      }
      throw new ReplayFailure("DEMO_ROUTE_CHANGE_PENDING");
    }
    if (latest != null
        && latest.status() == Status.FAILED
        && ledger
            .latestAttempt(latest.quote().id())
            .filter(attempt -> attempt.status() == PaymentStatus.SUCCEEDED)
            .isPresent()) {
      throw new ReplayFailure("DEMO_PAID_CHANGE_REQUIRES_REVIEW");
    }
    var target =
        routes
            .target(requestId, destination)
            .orElseThrow(() -> new ReplayFailure("DEMO_ROUTE_TARGET_INVALID"));
    long paid =
        Math.addExact(
            fares.paidQuote(requestId).amountMinor(), routes.appliedPayments(work.tripId()));
    long difference = DemoTariff.additionalAmount(DemoTariff.price(target.estimate()), paid);
    return routes.propose(requestId, work, target, difference, now);
  }

  /** Issues a local command only once, after acceptance and required payment. */
  @Transactional
  public Scope issue(long requestId, long revisionId, Instant now) {
    Work work = active(requestId);
    Proposal proposal = current(work, revisionId);
    if (proposal.scope() != null) {
      return proposal.scope();
    }
    if (!proposal.authorizedBy(ledger.latestAttempt(proposal.quote().id()).orElse(null))) {
      throw new ReplayFailure("DEMO_CHANGE_ACCEPTANCE_OR_PAYMENT_REQUIRED");
    }
    if (!proposal.quote().usableAt(now)) {
      throw new ReplayFailure("DEMO_CHANGE_QUOTE_EXPIRED");
    }
    return routes.issue(requestId, work, proposal, now);
  }

  /** Records the current command's matching result. Repeated terminal reports do not rewrite it. */
  @Transactional
  public Proposal report(long requestId, Scope scope, Report report, Instant now) {
    Work work = active(requestId);
    Proposal proposal = current(work, scope.revisionId());
    if (!scope.equals(proposal.scope())) {
      throw new ReplayFailure("DEMO_ROUTE_SCOPE_MISMATCH");
    }
    if (proposal.status().name().equals(report.name())) {
      return proposal;
    }
    if (!report.follows(proposal.status())) {
      throw new ReplayFailure("DEMO_ROUTE_REPORT_OUT_OF_ORDER");
    }
    routes.report(requestId, scope, report, now);
    return current(work, scope.revisionId());
  }

  private Work active(long requestId) {
    trips.lockPassenger(requestId).orElseThrow(() -> new ReplayFailure("DEMO_RIDE_UNAVAILABLE"));
    var work =
        trips
            .assignment(requestId)
            .filter(trip -> RouteAcceptance.changeable(trip.status()))
            .orElseThrow(() -> new ReplayFailure("DEMO_TRIP_NOT_OPEN_FOR_CHANGE"));
    return new Work(work.vehicleId(), work.dispatchId(), work.tripId());
  }

  private Proposal current(Work work, long revisionId) {
    return routes
        .latest(work.tripId())
        .filter(proposal -> proposal.revisionId() == revisionId)
        .orElseThrow(() -> new ReplayFailure("DEMO_ROUTE_REVISION_STALE"));
  }
}
