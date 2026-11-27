package dev.amo.scenarios.application;

import dev.amo.fares.domain.Fare;
import dev.amo.fares.domain.RouteChange;
import dev.amo.replay.application.TripReplayService.Result;
import dev.amo.scenarios.domain.ReviewEvidence;
import java.time.Instant;

/** Maps observed quote, payment, route and receipt details to the review read model. */
final class FareReviewEvidence {
  private FareReviewEvidence() {}

  static ReviewEvidence initial(Fare.View view, boolean paid) {
    var quote = view.quote();
    return new ReviewEvidence(
        paid ? "MOCK_PREPAYMENT_ATTEMPTED" : "INITIAL_FARE_QUOTED",
        paid ? view.attempt().attemptedAt() : quote.quotedAt(),
        null,
        null,
        quote.id(),
        view.paymentStatus().name(),
        quote.amountMinor(),
        quote.currencyCode(),
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        quote.estimate().distanceMeters(),
        quote.estimate().durationSeconds());
  }

  static ReviewEvidence route(
      RouteChange.View view, RouteChange.Proposal proposal, String event, Instant when) {
    var quote = view.quote();
    return new ReviewEvidence(
        event,
        when,
        proposal.tripId(),
        view.status().name(),
        quote.id(),
        view.paymentStatus().name(),
        quote.amountMinor(),
        quote.currencyCode(),
        view.proposedDestination(),
        view.effectiveDestination(),
        view.revisionId(),
        proposal.scope() == null ? null : proposal.scope().commandId(),
        null,
        null,
        null,
        view.deltaMinor(),
        quote.estimate().distanceMeters(),
        quote.estimate().durationSeconds());
  }

  static ReviewEvidence settled(Result trip, String destination) {
    var receipt = trip.receipt();
    return new ReviewEvidence(
        "FARE_FINALIZED",
        receipt.finalizedAt(),
        trip.tripId(),
        trip.status(),
        receipt.quoteId(),
        null,
        receipt.amountMinor(),
        receipt.currencyCode(),
        null,
        destination,
        null,
        null,
        null,
        null,
        receipt.reference(),
        null,
        null,
        null);
  }
}
