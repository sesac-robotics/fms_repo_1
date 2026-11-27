package dev.amo.control.application;

import dev.amo.control.application.HistoryQuery.Result;
import dev.amo.control.application.HistoryQuery.Ride;
import dev.amo.control.application.HistoryQuery.Trial;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

/** Reads staff history without extending the fleet snapshot. */
@Service
@Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
public class HistoryService {
  private final HistoryStore store;

  HistoryService(HistoryStore store) {
    this.store = store;
  }

  /** Return a page of calls, newest first, and its filtered count. */
  public Result<Ride> rides(HistoryQuery query) {
    return store.rides(query);
  }

  /** Return a page of trial records, newest first, and its filtered count. */
  public Result<Trial> trials(HistoryQuery query) {
    return store.trials(query);
  }
}
