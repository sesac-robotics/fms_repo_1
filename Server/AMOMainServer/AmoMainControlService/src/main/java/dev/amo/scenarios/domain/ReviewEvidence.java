package dev.amo.scenarios.domain;

import java.time.Instant;

/** Observed service output. Times are UTC instants and monetary amounts are minor units. */
public record ReviewEvidence(
    String event,
    Instant observedAt,
    Long tripId,
    String status,
    Long quoteId,
    String paymentStatus,
    Long amountMinor,
    String currencyCode,
    String proposedDestination,
    String effectiveDestination,
    Long revisionId,
    Long commandId,
    Long cycleId,
    Double batteryPercent,
    String receiptReference,
    Long deltaMinor,
    Long distanceMeters,
    Integer durationSeconds) {

  /** Builds an observed intake or trip status. */
  public static ReviewEvidence trip(String event, Instant when, Long tripId, String status) {
    return new ReviewEvidence(
        event, when, tripId, status, null, null, null, null, null, null, null, null, null, null,
        null, null, null, null);
  }

  /** Builds a recorded facility report with an optional battery percentage in [0, 100]. */
  public static ReviewEvidence depot(
      String event, Instant when, Long cycleId, String phase, Double batteryPercent) {
    return new ReviewEvidence(
        event,
        when,
        null,
        phase,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        cycleId,
        batteryPercent,
        null,
        null,
        null,
        null);
  }
}
