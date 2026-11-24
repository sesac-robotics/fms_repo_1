package dev.amo.fares.domain;

import java.time.Instant;

/**
 * Immutable quote, outcome, and receipt values. Amounts are in the stated currency's minor units.
 */
public final class Fare {
  private Fare() {}

  /** Expected distance and duration in whole meters and seconds. */
  public record Estimate(long distanceMeters, int durationSeconds) {
    public Estimate {
      if (distanceMeters <= 0 || durationSeconds <= 0) {
        throw new IllegalArgumentException("A fare estimate requires positive distance and time");
      }
    }
  }

  /** Persisted fare terms. Times are UTC instants, with expiry exclusive. */
  public record Quote(
      long id,
      Estimate estimate,
      String tariffVersion,
      long amountMinor,
      String currencyCode,
      Instant quotedAt,
      Instant expiresAt) {
    /** Returns whether a new payment can use these terms at the supplied time. */
    public boolean usableAt(Instant now) {
      return !now.isBefore(quotedAt) && now.isBefore(expiresAt);
    }
  }

  /** A hold has no attempt, while success and failure represent durable attempts. */
  public enum PaymentStatus {
    QUOTED,
    NOT_REQUIRED,
    ESTIMATE_MISSING,
    METHOD_MISSING,
    QUOTE_EXPIRED,
    FAILED,
    SUCCEEDED
  }

  /** The persisted identity, outcome and UTC start of a mock attempt. */
  public record Attempt(
      long quoteId, String key, long amountMinor, PaymentStatus status, Instant attemptedAt) {}

  /** The single immutable receipt issued against a completed trip. */
  public record Receipt(
      long tripId,
      long quoteId,
      long amountMinor,
      String currencyCode,
      String reference,
      Instant finalizedAt) {}

  /** Authorized passenger or staff projection, with no payment instrument identifier. */
  public record View(
      long requestId, Quote quote, PaymentStatus paymentStatus, Attempt attempt, Receipt receipt) {}
}
