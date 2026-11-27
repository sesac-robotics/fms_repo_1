package dev.amo.signals.domain;

import java.time.Instant;

/** One state report from an intersection signal, as published on /traffic_light_N/state. */
public record SignalState(
    String signalId,
    long seq,
    Phase phase,
    Mode mode,
    Phase holdTarget,
    int remainingMs,
    long uptimeMs,
    SignalCommand.Timing plan,
    boolean planPending,
    String lastCommand,
    String commandResult) {

  /** Lamp phases. Yellow and all red admit no new entry. */
  public enum Phase {
    NORTH_GREEN,
    NORTH_YELLOW,
    ALL_RED,
    EAST_GREEN,
    EAST_YELLOW
  }

  /** AUTO runs the fixed plan; HOLD keeps the hold target. */
  public enum Mode {
    AUTO,
    HOLD
  }

  /** Check cross-field rules that bean validation cannot express. */
  public boolean valid() {
    boolean holdOk =
        mode == Mode.HOLD
            ? holdTarget == Phase.NORTH_GREEN
                || holdTarget == Phase.EAST_GREEN
                || holdTarget == Phase.ALL_RED
            : holdTarget == null;
    return holdOk && remainingMs >= 0 && seq >= 0 && uptimeMs >= 0 && plan.safe();
  }

  /** Latest state and the UTC time when Main Control accepted it. */
  public record Received(SignalState state, Instant receivedAt) {}
}
