package dev.amo.vision.domain;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import dev.amo.vision.domain.VisionObservation.Outcome;
import dev.amo.vision.domain.VisionObservation.Source;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class VisionObservationTest {
  private static final Instant NOW = Instant.parse("2026-11-26T02:00:00Z");

  @Test
  void rejectsReversedAndFutureTimestamps() {
    assertFalse(event(NOW, NOW.minusSeconds(1), Outcome.DETECTED, "RED", 0.9).validAt(NOW));
    assertFalse(event(NOW, NOW.plusSeconds(6), Outcome.DETECTED, "RED", 0.9).validAt(NOW));
    assertTrue(
        event(NOW.minusSeconds(1), NOW.plusSeconds(5), Outcome.DETECTED, "RED", 0.9).validAt(NOW));
  }

  @Test
  void distinguishesDetectionFromEmptyOrUnavailableResults() {
    assertTrue(event(NOW, NOW, Outcome.NOT_DETECTED, null, null).validAt(NOW));
    assertTrue(event(NOW, NOW, Outcome.UNAVAILABLE, null, null).validAt(NOW));
    assertFalse(event(NOW, NOW, Outcome.DETECTED, null, null).validAt(NOW));
    assertFalse(event(NOW, NOW, Outcome.NOT_DETECTED, "RED", null).validAt(NOW));
    assertFalse(event(NOW, NOW, Outcome.DETECTED, "RED", Double.NaN).validAt(NOW));
    assertFalse(event(NOW, NOW, Outcome.UNAVAILABLE, null, 0.0).validAt(NOW));
  }

  private VisionObservation event(
      Instant capture, Instant processed, Outcome outcome, String label, Double confidence) {
    return new VisionObservation(
        UUID.randomUUID(),
        "PINKY-01",
        Source.TRAFFIC_RULES,
        "frame-1",
        capture,
        processed,
        outcome,
        label,
        confidence);
  }
}
