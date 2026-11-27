package dev.amo.signals.domain;

import java.util.Optional;
import java.util.regex.Pattern;

/**
 * A command text understood by the SignalKit firmware. Ranges mirror the firmware's config.h so an
 * unsafe plan is refused here before it reaches the device.
 */
public record SignalCommand(String text) {
  public static final int GREEN_MIN_MS = 3_000;
  public static final int GREEN_MAX_MS = 120_000;
  public static final int YELLOW_MIN_MS = 2_000;
  public static final int YELLOW_MAX_MS = 10_000;
  public static final int ALL_RED_MIN_MS = 1_000;
  public static final int ALL_RED_MAX_MS = 10_000;
  public static final int PARTNER_MIN_MS = GREEN_MIN_MS + YELLOW_MIN_MS;
  public static final int PARTNER_MAX_MS = GREEN_MAX_MS + YELLOW_MAX_MS;

  /** Longest command text: "PLAN" and six six-digit numbers. */
  public static final int MAX_LENGTH = 48;

  /** Four numbers, or six with the east yellow and the partner board's east time. */
  private static final Pattern PLAN =
      Pattern.compile(
          "PLAN ([0-9]{1,6}) ([0-9]{1,6}) ([0-9]{1,6}) ([0-9]{1,6})"
              + "(?: ([0-9]{1,6}) ([0-9]{1,6}))?");

  /** Return the command when it is a known, safe instruction. */
  public static Optional<SignalCommand> parse(String text) {
    if (text == null) {
      return Optional.empty();
    }
    return switch (text) {
      case "AUTO", "HOLD NORTH_GREEN", "HOLD EAST_GREEN", "HOLD ALL_RED" ->
          Optional.of(new SignalCommand(text));
      default -> plan(text);
    };
  }

  private static Optional<SignalCommand> plan(String text) {
    var match = PLAN.matcher(text);
    if (!match.matches()) {
      return Optional.empty();
    }
    int yellow = Integer.parseInt(match.group(3));
    boolean full = match.group(5) != null;
    var timing =
        new Timing(
            Integer.parseInt(match.group(1)),
            Integer.parseInt(match.group(2)),
            yellow,
            Integer.parseInt(match.group(4)),
            full ? Integer.parseInt(match.group(5)) : yellow,
            full ? Integer.parseInt(match.group(6)) : 0);
    return timing.safe() ? Optional.of(new SignalCommand(text)) : Optional.empty();
  }

  /**
   * Phase durations in milliseconds. {@code yellowMs} follows the north green and {@code
   * eastYellowMs} the east green. {@code partnerEastMs} is, on a coordinated junction, the other
   * board's east green plus east yellow, so both boards compute one cycle; 0 means none.
   */
  public record Timing(
      int northGreenMs,
      int eastGreenMs,
      int yellowMs,
      int allRedMs,
      int eastYellowMs,
      int partnerEastMs) {
    /** The four-number plan: one yellow for both greens and no partner. */
    public Timing(int northGreenMs, int eastGreenMs, int yellowMs, int allRedMs) {
      this(northGreenMs, eastGreenMs, yellowMs, allRedMs, yellowMs, 0);
    }

    public boolean safe() {
      return in(northGreenMs, GREEN_MIN_MS, GREEN_MAX_MS)
          && in(eastGreenMs, GREEN_MIN_MS, GREEN_MAX_MS)
          && in(yellowMs, YELLOW_MIN_MS, YELLOW_MAX_MS)
          && in(allRedMs, ALL_RED_MIN_MS, ALL_RED_MAX_MS)
          && in(eastYellowMs, YELLOW_MIN_MS, YELLOW_MAX_MS)
          && (partnerEastMs == 0 || in(partnerEastMs, PARTNER_MIN_MS, PARTNER_MAX_MS));
    }

    private static boolean in(int value, int min, int max) {
      return value >= min && value <= max;
    }
  }

  /** A stored command waiting for the bridge. */
  public record Pending(long id, String signalId, String command) {}
}
