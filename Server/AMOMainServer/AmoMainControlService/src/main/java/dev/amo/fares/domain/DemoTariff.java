package dev.amo.fares.domain;

import java.time.Duration;

/** Fictional local tariff. These values are not operating fares or runtime policy. */
public final class DemoTariff {
  public static final String VERSION = "demo-v1";
  public static final String CURRENCY = "XTS";
  public static final Duration VALIDITY = Duration.ofMinutes(10);

  private DemoTariff() {}

  /** Calculates a test amount in minor units from whole meters and seconds. */
  public static long price(Fare.Estimate estimate) {
    return Math.addExact(estimate.distanceMeters(), estimate.durationSeconds());
  }

  /** Converts a demo-map straight line at 0.2 m/s to whole meters and seconds. */
  public static Fare.Estimate schematicEstimate(double meters) {
    if (!Double.isFinite(meters) || meters <= 0 || meters > 1000) {
      return null;
    }
    return new Fare.Estimate((long) Math.ceil(meters), (int) Math.ceil(meters / 0.2));
  }

  /** Returns the positive amount still payable after previously applied payments. */
  public static long additionalAmount(long proposedMinor, long previouslyPaidMinor) {
    return Math.max(0, proposedMinor - previouslyPaidMinor);
  }
}
