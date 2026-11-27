package dev.amo.vision.application;

import dev.amo.vision.domain.VisionObservation;
import java.time.Instant;
import org.springframework.stereotype.Service;

/** Records Vision evidence without changing driving, dispatch or passenger state. */
@Service
public class RecordVisionObservation {
  private final VisionObservations observations;

  RecordVisionObservation(VisionObservations observations) {
    this.observations = observations;
  }

  /** Return the acceptance outcome given a UTC reception timestamp from the caller. */
  public Result record(VisionObservation observation, Instant receivedAt) {
    if (!observation.validAt(receivedAt)) {
      return Result.INVALID_OBSERVATION;
    }
    return observations.record(observation, receivedAt) ? Result.ACCEPTED : Result.UNKNOWN_VEHICLE;
  }

  /** An accepted result includes duplicate and older observations. */
  public enum Result {
    ACCEPTED,
    INVALID_OBSERVATION,
    UNKNOWN_VEHICLE
  }
}
