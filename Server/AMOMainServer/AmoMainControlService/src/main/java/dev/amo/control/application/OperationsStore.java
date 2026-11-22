package dev.amo.control.application;

import dev.amo.control.domain.Operations.Event;
import dev.amo.control.domain.Operations.Request;
import dev.amo.control.domain.Operations.Trial;
import dev.amo.control.domain.Operations.Vehicle;
import java.util.List;

/** Provides source data for a consistent, read-only operations snapshot. */
public interface OperationsStore {
  /** Reports whether persistence is ready to accept reads. */
  boolean ready();

  /** Reads the last stored status for each vehicle. */
  List<Vehicle> vehicles();

  /** Reads the most recent service requests. */
  List<Request> requests();

  /** Reads the most recent operational events. */
  List<Event> events();

  /** Reads the available trial summaries. */
  List<Trial> tests();
}
