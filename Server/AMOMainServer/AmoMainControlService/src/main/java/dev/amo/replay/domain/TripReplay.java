package dev.amo.replay.domain;

/** Ordered, synthetic SD-02 to SD-05 evidence for one captive demo vehicle. */
public final class TripReplay {
  private TripReplay() {}

  /** Each action accepts evidence only from its preceding phase. */
  public enum Step {
    ASSIGN(null, "ASSIGNED", "DEMO_DISPATCH_ASSIGNED"),
    PICKUP_STOP("ASSIGNED", "PICKUP_CONFIRMED", "DEMO_PICKUP_STOP_CONFIRMED"),
    BOARD("PICKUP_CONFIRMED", "BOARDED", "DEMO_BOARDING_CONFIRMED"),
    DEPART("BOARDED", "ON_TRIP", "DEMO_DEPARTURE_CONFIRMED"),
    DESTINATION_STOP("ON_TRIP", "ARRIVED", "DEMO_DESTINATION_STOP_CONFIRMED"),
    ALIGHT("ARRIVED", "COMPLETED", "DEMO_ALIGHTING_CONFIRMED");

    private final String previous;
    private final String status;
    private final String event;

    Step(String previous, String status, String event) {
      this.previous = previous;
      this.status = status;
      this.event = event;
    }

    /** Reports whether the observation is legal in the current phase. */
    public boolean follows(String current) {
      return java.util.Objects.equals(previous, current);
    }

    /** Returns the canonical trip phase after this observation. */
    public String status() {
      return status;
    }

    /** Returns the audit type denoting fictional evidence. */
    public String event() {
      return event;
    }
  }

  /** Observed trip totals in meters and seconds, supplied only at the destination stop. */
  public record Totals(double distanceMeters, int elapsedSeconds) {
    public Totals {
      if (!Double.isFinite(distanceMeters) || distanceMeters < 0 || elapsedSeconds < 0) {
        throw new IllegalArgumentException("Invalid synthetic trip totals");
      }
    }
  }
}
