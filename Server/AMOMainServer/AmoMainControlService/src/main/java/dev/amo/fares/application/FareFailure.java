package dev.amo.fares.application;

/** Expected fare failure with a stable external code and no sensitive input. */
public final class FareFailure extends RuntimeException {
  /** Rejection codes mapped by the HTTP adapter. */
  public enum Reason {
    RIDE_NOT_FOUND,
    ROUTE_CHANGE_NOT_FOUND,
    FARE_QUOTE_CONFLICT,
    FARE_PAYMENT_CLOSED,
    FARE_EVIDENCE_MISSING,
    FARE_PREPAYMENT_REQUIRED
  }

  private final Reason reason;

  FareFailure(Reason reason) {
    super(reason.name());
    this.reason = reason;
  }

  /** Returns the reason for the rejected action. */
  public Reason reason() {
    return reason;
  }
}
