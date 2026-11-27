package dev.amo.maincontrol;

/** A rejected ride or menu operation, independent of transport status codes. */
public final class MainControlFailure extends RuntimeException {
  /** Reasons that the caller can use to report an expected rejection. */
  public enum Reason {
    IDENTICAL_STOPS,
    UNKNOWN_STOP,
    IDEMPOTENCY_KEY_CONFLICT,
    SETTINGS_MUST_REMAIN_VISIBLE,
    MENU_NOT_FOUND
  }

  private final Reason reason;

  MainControlFailure(Reason reason) {
    super(reason.name());
    this.reason = reason;
  }

  /** Returns the stable reason for the rejected operation. */
  public Reason reason() {
    return reason;
  }
}
