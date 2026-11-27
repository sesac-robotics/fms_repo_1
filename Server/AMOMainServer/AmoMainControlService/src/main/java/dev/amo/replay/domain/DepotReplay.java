package dev.amo.replay.domain;

import java.time.Instant;

/** Pure state transitions for local SD-05/07 observations and initial charging. */
public final class DepotReplay {
  private DepotReplay() {}

  /** Vehicle return and independent facility states; WAITING still occupies the bay. */
  public enum Phase {
    INITIAL,
    RETURNING,
    ARRIVED,
    OCCUPIED,
    CHARGING,
    WAITING,
    VACATED
  }

  /** Each synthetic observation identifies which interface would report it. */
  public enum Step {
    RETURN_ORDERED("DEMO_IF04"),
    RETURN_ARRIVAL("DEMO_IF05"),
    OCCUPIED("DEMO_IF10"),
    CHARGE_STARTED("DEMO_IF10"),
    BATTERY_REPORTED("DEMO_IF05"),
    VACATED("DEMO_IF10");

    private final String source;

    Step(String source) {
      this.source = source;
    }

    /** Returns the fictional evidence producer used in the operations ledger. */
    public String source() {
      return source;
    }
  }

  /**
   * Incoming observation including the stable event key and a battery percentage when applicable.
   */
  public record Observation(Step step, String key, Double batteryPercent) {
    /** Returns whether the observation includes exactly its required fields. */
    public boolean valid() {
      return (step == Step.BATTERY_REPORTED) == (batteryPercent != null)
          && (batteryPercent == null
              || Double.isFinite(batteryPercent) && batteryPercent >= 0 && batteryPercent <= 100);
    }

    /** Returns the next phase, or null when evidence arrives in the wrong order. */
    public Phase next(Phase phase) {
      return switch (step) {
        case RETURN_ORDERED -> phase == null ? Phase.RETURNING : null;
        case RETURN_ARRIVAL -> phase == Phase.RETURNING ? Phase.ARRIVED : null;
        case OCCUPIED -> phase == Phase.INITIAL || phase == Phase.ARRIVED ? Phase.OCCUPIED : null;
        case CHARGE_STARTED -> phase == Phase.OCCUPIED ? Phase.CHARGING : null;
        case BATTERY_REPORTED ->
            phase == Phase.CHARGING ? batteryPercent >= 70 ? Phase.WAITING : Phase.CHARGING : null;
        case VACATED -> phase == Phase.WAITING ? Phase.VACATED : null;
      };
    }
  }

  /** Durable observation result; observedAt is the original UTC replay time. */
  public record Result(
      long cycleId, Step step, Phase phase, Double batteryPercent, Instant observedAt) {
    /** Reports whether the facility is vacant for a subsequent demo assignment check. */
    public boolean facilityVacant() {
      return phase == Phase.VACATED;
    }
  }
}
