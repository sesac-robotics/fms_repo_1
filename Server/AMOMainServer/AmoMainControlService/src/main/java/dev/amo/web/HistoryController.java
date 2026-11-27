package dev.amo.web;

import dev.amo.ApiError;
import dev.amo.control.application.HistoryQuery;
import dev.amo.control.application.HistoryQuery.Result;
import dev.amo.control.application.HistoryQuery.Ride;
import dev.amo.control.application.HistoryQuery.Trial;
import dev.amo.control.application.HistoryService;
import java.time.OffsetDateTime;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Staff history queries with half-open ISO-8601 time ranges. */
@RestController
class HistoryController {
  private final HistoryService history;

  HistoryController(HistoryService history) {
    this.history = history;
  }

  @GetMapping("/api/operations/trip-history")
  Result<Ride> trips(
      @RequestParam(defaultValue = "") String q,
      @RequestParam(defaultValue = "0") int offset,
      @RequestParam(defaultValue = "50") int limit,
      @RequestParam(defaultValue = "1900-01-01T00:00:00Z") OffsetDateTime from,
      @RequestParam(defaultValue = "9999-01-01T00:00:00Z") OffsetDateTime until) {
    return history.rides(query(q, offset, limit, from, until));
  }

  @GetMapping("/api/operations/test-history")
  Result<Trial> tests(
      @RequestParam(defaultValue = "") String q,
      @RequestParam(defaultValue = "0") int offset,
      @RequestParam(defaultValue = "50") int limit,
      @RequestParam(defaultValue = "1900-01-01T00:00:00Z") OffsetDateTime from,
      @RequestParam(defaultValue = "9999-01-01T00:00:00Z") OffsetDateTime until) {
    return history.trials(query(q, offset, limit, from, until));
  }

  private static HistoryQuery query(
      String q, int offset, int limit, OffsetDateTime from, OffsetDateTime until) {
    ReadPage.validate(offset, limit, q);
    if (!from.isBefore(until)) {
      throw new ApiError(HttpStatus.BAD_REQUEST, "INVALID_HISTORY_WINDOW");
    }
    return new HistoryQuery(q.strip(), from, until, offset, limit);
  }
}
