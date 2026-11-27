package dev.amo.web;

import dev.amo.ApiError;
import java.util.List;
import org.springframework.http.HttpStatus;

/** A bounded read page with a zero-based row offset. */
record ReadPage<T>(List<T> items, int offset, int limit, boolean hasMore) {
  static void validate(int offset, int limit, String search) {
    if (offset < 0 || offset > 2_000_000 || limit < 1 || limit > 250 || search.length() > 100) {
      throw new ApiError(HttpStatus.BAD_REQUEST, "INVALID_PAGE");
    }
  }

  static <T> ReadPage<T> from(List<T> rows, int offset, int limit) {
    return new ReadPage<>(
        List.copyOf(rows.subList(0, Math.min(rows.size(), limit))),
        offset,
        limit,
        rows.size() > limit);
  }
}
