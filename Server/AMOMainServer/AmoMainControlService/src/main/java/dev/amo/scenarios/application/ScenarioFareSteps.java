package dev.amo.scenarios.application;

import dev.amo.fares.application.FareFailure;
import dev.amo.fares.application.FareService;
import dev.amo.fares.application.RouteAcceptance;
import dev.amo.fares.application.RouteChangeStore;
import dev.amo.fares.application.RouteReplayService;
import dev.amo.fares.domain.Fare.PaymentStatus;
import dev.amo.fares.domain.RouteChange;
import dev.amo.replay.application.TripReplayService.Result;
import dev.amo.replay.application.TripReplayStore;
import dev.amo.scenarios.application.ScenarioStore.Run;
import dev.amo.scenarios.domain.ReviewEvidence;
import dev.amo.scenarios.domain.Scenario;
import dev.amo.scenarios.domain.Scenario.Step;
import java.time.Instant;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

/**
 * Exercises fare and route services and checks their observed results against the selected case.
 */
@Component
@Profile("demo")
class ScenarioFareSteps {
  private final FareService fares;
  private final RouteAcceptance acceptance;
  private final RouteReplayService routes;
  private final RouteChangeStore changes;
  private final TripReplayStore trips;

  ScenarioFareSteps(
      FareService fares,
      RouteAcceptance acceptance,
      RouteReplayService routes,
      RouteChangeStore changes,
      TripReplayStore trips) {
    this.fares = fares;
    this.acceptance = acceptance;
    this.routes = routes;
    this.changes = changes;
    this.trips = trips;
  }

  ReviewEvidence execute(Run run, Step step, boolean manual, Instant now) {
    return switch (step) {
      case QUOTE, PREPAY -> initial(run, step, manual, now);
      case CHANGE_PROPOSE, CHANGE_ACCEPT -> passengerChange(run, step, manual, now);
      case ROUTE_ISSUE, ROUTE_ACK, ROUTE_APPLIED, ROUTE_FAILED -> command(run, step, now);
      default -> throw new IllegalArgumentException("Not a fare or route step");
    };
  }

  private ReviewEvidence initial(Run run, Step step, boolean manual, Instant now) {
    long owner = run.passengerId();
    long request = run.requestId();
    var view =
        step == Step.QUOTE && !manual
            ? fares.quote(owner, request, now)
            : fares.read(owner, request, now);
    require(view.quote() != null, manual);
    if (step == Step.PREPAY && !manual) {
      view = fares.prepay(owner, request, view.quote().id(), run.key(step), now);
    }
    var attempt = view.attempt();
    boolean paid = step == Step.PREPAY;
    require(!paid || attempt != null && attempt.status() == PaymentStatus.SUCCEEDED, manual);
    return FareReviewEvidence.initial(view, paid);
  }

  private ReviewEvidence passengerChange(Run run, Step step, boolean manual, Instant now) {
    long request = run.requestId();
    if (step == Step.CHANGE_PROPOSE && !manual) {
      routes.proposeForPassenger(run.passengerId(), request, "S4", now);
    }
    var view = change(run, manual, now);
    require(
        view.proposedDestination().equals("S4")
            && view.effectiveDestination().equals("S2")
            && view.deltaMinor() > 0,
        false);
    if (step == Step.CHANGE_ACCEPT && !manual) {
      view = acceptance.accept(run.passengerId(), request, view.quote().id(), run.key(step), now);
    }
    boolean paid = step == Step.CHANGE_ACCEPT;
    require(!paid || view.accepted() && view.paymentStatus() == PaymentStatus.SUCCEEDED, manual);
    return FareReviewEvidence.route(
        view,
        proposal(run),
        paid ? "MOCK_DIFFERENCE_ATTEMPTED" : "CHANGE_FARE_QUOTED",
        paid ? view.attempt().attemptedAt() : view.quote().quotedAt());
  }

  private ReviewEvidence command(Run run, Step step, Instant now) {
    var proposal = proposal(run);
    if (step == Step.ROUTE_ISSUE) {
      routes.issue(run.requestId(), proposal.revisionId(), now);
    } else {
      var report =
          switch (step) {
            case ROUTE_ACK -> RouteChange.Report.ACKNOWLEDGED;
            case ROUTE_APPLIED -> RouteChange.Report.APPLIED;
            case ROUTE_FAILED -> RouteChange.Report.FAILED;
            default -> throw new IllegalArgumentException("Not a report");
          };
      routes.report(run.requestId(), proposal.scope(), report, now);
    }
    var view = change(run, false, now);
    var expected =
        switch (step) {
          case ROUTE_ISSUE -> RouteChange.Status.ISSUED;
          case ROUTE_ACK -> RouteChange.Status.ACKNOWLEDGED;
          case ROUTE_APPLIED -> RouteChange.Status.APPLIED;
          case ROUTE_FAILED -> RouteChange.Status.FAILED;
          default -> throw new IllegalArgumentException("Not a command step");
        };
    String destination = expected == RouteChange.Status.APPLIED ? "S4" : "S2";
    require(
        view.status() == expected
            && view.effectiveDestination().equals(destination)
            && view.paymentStatus() == PaymentStatus.SUCCEEDED,
        false);
    return FareReviewEvidence.route(
        view,
        proposal(run),
        "DEMO_ROUTE_" + expected,
        view.appliedAt() == null ? now : view.appliedAt());
  }

  void requireEffectiveRoute(Run run, Instant now) {
    var view = change(run, false, now);
    require(view.effectiveDestination().equals(run.plan().effectiveDestination()), false);
  }

  ReviewEvidence settlement(Run run, Result trip) {
    var receipt = trip.receipt();
    require(receipt != null, false);
    Instant now = receipt.finalizedAt();
    var quote =
        run.plan() == Scenario.TAXI_APPLIED
            ? change(run, false, now).quote()
            : fares.read(run.passengerId(), run.requestId(), now).quote();
    require(receipt.quoteId() == quote.id() && receipt.amountMinor() == quote.amountMinor(), false);
    return FareReviewEvidence.settled(trip, change(run, false, now).effectiveDestination());
  }

  private RouteChange.View change(Run run, boolean manual, Instant now) {
    try {
      return acceptance.read(run.passengerId(), run.requestId(), now);
    } catch (FareFailure failure) {
      if (manual && failure.reason() == FareFailure.Reason.ROUTE_CHANGE_NOT_FOUND) {
        throw new ScenarioRejected("SCENARIO_WAITING_ANDROID");
      }
      throw failure;
    }
  }

  private RouteChange.Proposal proposal(Run run) {
    return trips
        .assignment(run.requestId())
        .flatMap(trip -> changes.latest(trip.tripId()))
        .orElseThrow(() -> new ScenarioRejected("SCENARIO_EXPECTATION_MISMATCH"));
  }

  private static void require(boolean condition, boolean manual) {
    if (!condition) {
      throw new ScenarioRejected(
          manual ? "SCENARIO_WAITING_ANDROID" : "SCENARIO_EXPECTATION_MISMATCH");
    }
  }
}
