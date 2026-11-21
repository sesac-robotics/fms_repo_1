package dev.amo.maincontrol;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;
import java.util.List;

/** Snapshot data returned to authorized operations clients. */
public record Operations(
    List<Vehicle> vehicles,
    List<Request> requests,
    List<Event> events,
    List<Trial> tests,
    boolean demo) {
  public record Vehicle(
      long id,
      String vehicleNo,
      String status,
      Double batteryPercent,
      String connection,
      Double xM,
      Double yM,
      boolean dispatchEnabled) {}

  public record Request(long id, String pickup, String destination, String status) {}

  public record Event(
      long id, Instant time, String type, String vehicle, String detail, Long requestId) {}

  public record Trial(String name, @JsonProperty("pass") int passed, int total, int latencyMs) {}
}
