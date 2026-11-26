package dev.amo.control.domain;

import dev.amo.signals.domain.SignalState;
import dev.amo.vision.domain.VisionObservation.Received;
import java.time.Instant;
import java.util.List;

/** Snapshot data returned to authorized operations clients. */
public record Operations(
    List<Vehicle> vehicles,
    List<Request> requests,
    List<Event> events,
    List<Trial> tests,
    boolean demo,
    ReviewPlayback review,
    List<Received> vision,
    List<SignalState.Received> signals) {
  /** Latest stored vehicle data. Coordinates are in map meters, yaw in radians, speed in m/s. */
  public record Vehicle(
      long id,
      String vehicleNo,
      String status,
      Double batteryPercent,
      String connection,
      Double xM,
      Double yM,
      Double yawRad,
      Double speedMps,
      String stopReason,
      boolean dispatchEnabled,
      Sample sample) {}

  /** Identity and UTC server reception time of the telemetry used in a vehicle row. */
  public record Sample(String epoch, long sequence, Instant receivedAt) {}

  /** Recent call and the latest matched-applied revision, if one exists. */
  public record Request(
      long id,
      String pickup,
      String destination,
      String status,
      String effectiveDestination,
      Long appliedRevisionId) {}

  public record Event(
      long id, Instant time, String type, String vehicle, String detail, Long requestId) {}

  public record Trial(String name, int pass, int total, int latencyMs) {}
}
