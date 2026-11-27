package dev.amo.control.application;

import dev.amo.control.domain.RecordedRoute.Sample;
import java.util.List;

/** Reads observations associated with the requested service and its last started trip. */
public interface RecordedRouteStore {
  /** Checks whether the request is known to the service. */
  boolean requestExists(long requestId);

  /** Reads a bounded set of observations in reverse acquisition order. */
  List<Sample> samples(long requestId);
}
