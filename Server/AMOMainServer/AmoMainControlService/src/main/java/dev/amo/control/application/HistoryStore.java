package dev.amo.control.application;

import dev.amo.control.application.HistoryQuery.Result;
import dev.amo.control.application.HistoryQuery.Ride;
import dev.amo.control.application.HistoryQuery.Trial;

/** Storage boundary for staff history queries. */
public interface HistoryStore {
  /** Reads matching calls and their filtered count. */
  Result<Ride> rides(HistoryQuery query);

  /** Reads matching trial rows and their filtered count. */
  Result<Trial> trials(HistoryQuery query);
}
