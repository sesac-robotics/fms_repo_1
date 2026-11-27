package dev.amo.fares.domain;

import dev.amo.fares.domain.Fare.Attempt;
import dev.amo.fares.domain.Fare.PaymentStatus;
import dev.amo.fares.domain.Fare.Quote;
import java.time.Instant;

/** Quotable route changes and matched synthetic IF-04 evidence. */
public final class RouteChange {
  private RouteChange() {}

  /** A proposal's status. Only APPLIED changes the effective terms and destination. */
  public enum Status {
    PROPOSED,
    ISSUED,
    ACKNOWLEDGED,
    APPLIED,
    FAILED;

    /** Returns whether the proposal can be superseded by a subsequent proposal. */
    public boolean terminal() {
      return this == APPLIED || this == FAILED;
    }
  }

  /** The authority and identity required to attribute a simulated command report. */
  public record Scope(
      long vehicleId, long dispatchId, long revisionId, long commandId, String epoch) {}

  /** The proposal and any verified application time. Quote time and application time are UTC. */
  public record Proposal(
      long revisionId,
      long tripId,
      String destination,
      long deltaMinor,
      Quote quote,
      Status status,
      String acceptedKey,
      Scope scope,
      Instant appliedAt) {
    /** Returns whether user acceptance and any positive mock charge permit command issuance. */
    public boolean authorizedBy(Attempt attempt) {
      return acceptedKey != null
          && (deltaMinor == 0 || attempt != null && attempt.status() == PaymentStatus.SUCCEEDED);
    }
  }

  /** Reportable IF-04 results and the predecessor state each requires. */
  public enum Report {
    ACKNOWLEDGED,
    APPLIED,
    FAILED;

    /** Returns whether this result can follow the currently recorded status. */
    public boolean follows(Status current) {
      return switch (this) {
        case ACKNOWLEDGED -> current == Status.ISSUED;
        case APPLIED -> current == Status.ACKNOWLEDGED;
        case FAILED -> current == Status.ISSUED || current == Status.ACKNOWLEDGED;
      };
    }
  }

  /**
   * Passenger/staff route view. A pending or failed proposal can coexist with the applied route.
   */
  public record View(
      long revisionId,
      String proposedDestination,
      Quote quote,
      long deltaMinor,
      Status status,
      boolean accepted,
      PaymentStatus paymentStatus,
      Attempt attempt,
      String effectiveDestination,
      Long appliedRevisionId,
      Instant appliedAt) {}
}
