package dev.amo.control.application;

import java.time.OffsetDateTime;
import java.util.List;

/** Read parameters for a bounded history browse or a filtered count. */
public record HistoryQuery(
    String text, OffsetDateTime from, OffsetDateTime until, int offset, int rows) {
  /** A page and the number of matching records in its read transaction. */
  public record Result<T>(List<T> rows, long matching) {}

  public record Ride(long id, String serviceType, String status, OffsetDateTime receivedAt) {}

  public record Trial(
      long id, String name, OffsetDateTime recordedAt, int passed, int total, int latencyMs) {}
}
