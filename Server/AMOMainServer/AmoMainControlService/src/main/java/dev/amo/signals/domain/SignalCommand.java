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

  private static final Pattern PLAN =
      Pattern.compile("PLAN ([0-9]{1,6}) ([0-9]{1,6}) ([0-9]{1,6}) ([0-9]{1,6})");

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
    var timing =
        new Timing(
            Integer.parseInt(match.group(1)),
            Integer.parseInt(match.group(2)),
            Integer.parseInt(match.group(3)),
            Integer.parseInt(match.group(4)));
    return timing.safe() ? Optional.of(new SignalCommand(text)) : Optional.empty();
  }

  /** Phase durations in milliseconds: north green, east green, yellow and all red. */
  public record Timing(int northGreenMs, int eastGreenMs, int yellowMs, int allRedMs) {
    public boolean safe() {
      return in(northGreenMs, GREEN_MIN_MS, GREEN_MAX_MS)
          && in(eastGreenMs, GREEN_MIN_MS, GREEN_MAX_MS)
          && in(yellowMs, YELLOW_MIN_MS, YELLOW_MAX_MS)
          && in(allRedMs, ALL_RED_MIN_MS, ALL_RED_MAX_MS);
    }

    private static boolean in(int value, int min, int max) {
      return value >= min && value <= max;
    }
  }

  /** A stored command waiting for the bridge. */
  public record Pending(long id, String signalId, String command) {}
}
