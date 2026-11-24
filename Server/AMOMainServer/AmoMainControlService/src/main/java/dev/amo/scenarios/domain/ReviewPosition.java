package dev.amo.scenarios.domain;

import dev.amo.scenarios.domain.Scenario.Step;
import java.util.Optional;

/** Schematic Taxi checkpoints in v0.2 map meters from the bottom-left origin. */
public record ReviewPosition(double xMeters, double yMeters) {
  private static final ReviewPosition BAY = new ReviewPosition(0.27, 1.53);

  /** Returns a new map checkpoint only for a simulated movement or an initial observation. */
  public static Optional<ReviewPosition> at(Scenario plan, Step step) {
    return Optional.ofNullable(
        switch (step) {
          case INITIAL_OCCUPY, RETURN_ARRIVAL -> BAY;
          case ASSIGN -> new ReviewPosition(0.52, 1.12);
          case PICKUP_STOP -> new ReviewPosition(0.516, 0.913);
          case DEPART -> new ReviewPosition(1.10, 0.913);
          case REDEPART -> new ReviewPosition(1.80, 0.47);
          case DESTINATION_STOP ->
              plan == Scenario.TAXI_APPLIED
                  ? new ReviewPosition(2.085, 0.255)
                  : new ReviewPosition(1.843, 0.913);
          case RETURN_ORDER -> new ReviewPosition(1.12, 1.31);
          default -> null;
        });
  }
}
