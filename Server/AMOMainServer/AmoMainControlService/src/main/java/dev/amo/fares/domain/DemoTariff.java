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

  /** Returns the positive amount still payable after previously applied payments. */
  public static long additionalAmount(long proposedMinor, long previouslyPaidMinor) {
    return Math.max(0, proposedMinor - previouslyPaidMinor);
  }
}
