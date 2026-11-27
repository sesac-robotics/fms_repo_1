package dev.amo.control.domain;

import java.util.List;
import java.util.UUID;

/** Simulated check points for the single active review on the confirmed map. */
public record ReviewPlayback(
    UUID runId, String vehicle, List<Checkpoint> checkpoints, SchematicPoint schematicPoint) {
  /** Optional v0.2 point in metres for the existing Web review map. */
  public record SchematicPoint(double xM, double yM) {}

  /** An ordered step and its committed status and reason codes for the review overlay. */
  public record Checkpoint(String step, String status, String reason) {}
}
