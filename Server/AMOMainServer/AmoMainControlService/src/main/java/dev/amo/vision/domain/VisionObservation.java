package dev.amo.vision.domain;

import java.time.Instant;
import java.util.UUID;

/** A detector observation and its UTC timestamps, independent of storage and transport. */
public record VisionObservation(
    UUID resultId,
    String vehicleNo,
    Source source,
    String frameId,
    Instant capturedAt,
    Instant processedAt,
    Outcome outcome,
    String label,
    Double confidence) {
  /** Stable source identities used by the three Vision services. */
  public enum Source {
    DRIVING_PERCEPTION,
    TRAFFIC_RULES,
    DIRECTION_RECOGNITION
  }

  /** A classified result, an empty detection, or an unavailable detector. */
  public enum Outcome {
    DETECTED,
    NOT_DETECTED,
    UNAVAILABLE
  }

  /** Validate temporal order, label presence and optional confidence in [0, 1]. */
  public boolean validAt(Instant receivedAt) {
    return !capturedAt.isAfter(processedAt)
        && !processedAt.isAfter(receivedAt.plusSeconds(5))
        && (outcome == Outcome.DETECTED) == (label != null)
        && (confidence == null
            || (outcome == Outcome.DETECTED
                && Double.isFinite(confidence)
                && confidence >= 0
                && confidence <= 1));
  }

  /** Latest observation and the UTC time when Main Control accepted it. */
  public record Received(VisionObservation observation, Instant receivedAt) {}
}
