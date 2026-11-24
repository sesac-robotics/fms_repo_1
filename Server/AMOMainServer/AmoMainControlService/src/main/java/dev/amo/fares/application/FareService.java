package dev.amo.fares.application;

import dev.amo.fares.application.FareFailure.Reason;
import dev.amo.fares.application.FareStore.Request;
import dev.amo.fares.domain.Fare.Attempt;
import dev.amo.fares.domain.Fare.PaymentStatus;
import dev.amo.fares.domain.Fare.Quote;
import dev.amo.fares.domain.Fare.Receipt;
import dev.amo.fares.domain.Fare.View;
import java.time.Instant;
import java.util.Optional;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Coordinates fictional one-way fare transactions on the explicit local demo profile. */
@Service
@Profile("demo")
public class FareService {
  private final FareStore store;
  private final RouteChangeStore routes;

  FareService(FareStore store, RouteChangeStore routes) {
    this.store = store;
    this.routes = routes;
  }

  /** Returns existing terms, or records the first quote for an open owned request. */
  @Transactional
  public View quote(long passengerId, long requestId, Instant now) {
    Request request = owned(passengerId, requestId);
    Quote quote = store.initialQuote(requestId).orElse(null);
    if (quote == null && request.estimate() != null && payable(request)) {
      quote = store.saveInitialQuote(requestId, request.estimate(), now);
    }
    return view(request, quote, now);
  }

  /** Returns durable fare state without issuing a quote or starting a payment. */
  @Transactional
  public View read(long passengerId, long requestId, Instant now) {
    Request request = owned(passengerId, requestId);
    return view(request, store.initialQuote(requestId).orElse(null), now);
  }

  /**
   * Attempts a fictional payment using the registered mock method. Same quote and key replay the
   * stored result. Expired terms, missing method and closed requests cannot create an attempt.
   */
  @Transactional
  public View prepay(long passengerId, long requestId, long quoteId, String key, Instant now) {
    Request request = owned(passengerId, requestId);
    Quote quote =
        store
            .initialQuote(requestId)
            .filter(value -> value.id() == quoteId)
            .orElseThrow(() -> new FareFailure(Reason.FARE_QUOTE_CONFLICT));
    Optional<Attempt> prior = store.attempt(quote.id(), key);
    if (prior.isPresent()) {
      return response(requestId, quote, prior.get());
    }
    View current = view(request, quote, now);
    if (current.paymentStatus() == PaymentStatus.SUCCEEDED
        || current.paymentStatus() == PaymentStatus.METHOD_MISSING
        || current.paymentStatus() == PaymentStatus.QUOTE_EXPIRED) {
      return current;
    }
    if (!payable(request)) {
      throw new FareFailure(Reason.FARE_PAYMENT_CLOSED);
    }
    return response(
        requestId,
        quote,
        store.saveAttempt(
            quote, key, request.method(), quote.amountMinor(), outcome(request), now));
  }

  /** Requires a successful initial payment before the demo dispatch can be authorized. */
  @Transactional
  public void requirePrepayment(long passengerId, long requestId) {
    owned(passengerId, requestId);
    paidQuote(requestId);
  }

  /**
   * Issues the original receipt once after the same trip is closed with successful alighting
   * evidence. Replays for a different trip fail even if associated with the same request.
   */
  @Transactional
  public Receipt finalizeTrip(long passengerId, long requestId, long tripId, Instant now) {
    owned(passengerId, requestId);
    Optional<Receipt> existing = store.receipt(requestId);
    if (existing.isPresent()) {
      return existing
          .filter(receipt -> receipt.tripId() == tripId)
          .orElseThrow(() -> new FareFailure(Reason.FARE_EVIDENCE_MISSING));
    }
    var evidence =
        store
            .closeEvidence(requestId, tripId)
            .orElseThrow(() -> new FareFailure(Reason.FARE_EVIDENCE_MISSING));
    Quote initial = paidQuote(requestId);
    Quote effective = routes.applied(tripId).map(route -> route.quote()).orElse(initial);
    return store.settle(requestId, evidence, effective, now);
  }

  private Request owned(long passengerId, long requestId) {
    return store
        .lock(requestId, passengerId)
        .orElseThrow(() -> new FareFailure(Reason.RIDE_NOT_FOUND));
  }

  Quote paidQuote(long requestId) {
    return store
        .initialQuote(requestId)
        .filter(
            quote ->
                store
                    .latestAttempt(quote.id())
                    .filter(attempt -> attempt.status() == PaymentStatus.SUCCEEDED)
                    .isPresent())
        .orElseThrow(() -> new FareFailure(Reason.FARE_PREPAYMENT_REQUIRED));
  }

  private View view(Request request, Quote quote, Instant now) {
    if (quote == null) {
      return new View(request.id(), null, PaymentStatus.ESTIMATE_MISSING, null, null);
    }
    Attempt attempt = store.latestAttempt(quote.id()).orElse(null);
    PaymentStatus status = PaymentStatus.QUOTED;
    if (attempt != null && attempt.status() == PaymentStatus.SUCCEEDED) {
      status = PaymentStatus.SUCCEEDED;
    } else if (request.method() == null || request.method().isBlank()) {
      status = PaymentStatus.METHOD_MISSING;
    } else if (!quote.usableAt(now)) {
      status = PaymentStatus.QUOTE_EXPIRED;
    } else if (attempt != null) {
      status = attempt.status();
    }
    return new View(request.id(), quote, status, attempt, store.receipt(request.id()).orElse(null));
  }

  private View response(long requestId, Quote quote, Attempt attempt) {
    return new View(
        requestId, quote, attempt.status(), attempt, store.receipt(requestId).orElse(null));
  }

  private static boolean payable(Request request) {
    return "RECEIVED".equals(request.status()) || "WAITING_DISPATCH".equals(request.status());
  }

  static PaymentStatus outcome(Request request) {
    return "demo-declined".equals(request.method())
        ? PaymentStatus.FAILED
        : PaymentStatus.SUCCEEDED;
  }
}
