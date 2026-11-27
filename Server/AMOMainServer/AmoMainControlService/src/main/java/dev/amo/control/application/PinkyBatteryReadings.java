package dev.amo.control.application;

import dev.amo.control.domain.Operations.PinkyBattery;
import java.util.List;

/** Provides equipment readings independently of fleet and dispatch records. */
public interface PinkyBatteryReadings {
  /** Returns the latest available readings, ordered by equipment identifier. */
  List<PinkyBattery> latest();
}
