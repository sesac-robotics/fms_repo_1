package dev.amo.vision.application;

import dev.amo.vision.domain.VisionObservation;
import java.time.Instant;
import java.util.List;

/** Stores the latest valid observation per vehicle and detector. */
public interface VisionObservations {
  /** Accept a known vehicle's observation and preserve newer observations on retries. */
  boolean record(VisionObservation observation, Instant receivedAt);

  /** Return latest observations of vehicles visible in the normal operations snapshot. */
  List<VisionObservation.Received> latest();
}
