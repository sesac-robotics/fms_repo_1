package dev.amo.fares.adapters;

import dev.amo.fares.domain.Fare.Attempt;
import dev.amo.fares.domain.Fare.Estimate;
import dev.amo.fares.domain.Fare.PaymentStatus;
import dev.amo.fares.domain.Fare.Quote;
import dev.amo.fares.domain.Fare.Receipt;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.OffsetDateTime;

/** Converts PostgreSQL fare rows into transport-independent value objects. */
final class FareRows {
  private FareRows() {}

  static Quote quote(ResultSet row, int index) throws SQLException {
    return new Quote(
        row.getLong("id"),
        new Estimate(row.getLong("distance_m"), row.getInt("duration_s")),
        row.getString("tariff_version"),
        row.getLong("amount_minor"),
        row.getString("currency_code"),
        instant(row, "quoted_at"),
        instant(row, "expires_at"));
  }

  static Attempt attempt(ResultSet row, int index) throws SQLException {
    return new Attempt(
        row.getLong("quote_id"),
        row.getString("attempt_key"),
        row.getLong("amount_minor"),
        PaymentStatus.valueOf(row.getString("result")),
        instant(row, "attempted_at"));
  }

  static Receipt receipt(ResultSet row, int index) throws SQLException {
    return new Receipt(
        row.getLong("trip_id"),
        row.getLong("quote_id"),
        row.getLong("amount_minor"),
        row.getString("currency_code"),
        row.getString("receipt_ref"),
        instant(row, "finalized_at"));
  }

  private static Instant instant(ResultSet row, String name) throws SQLException {
    return row.getObject(name, OffsetDateTime.class).toInstant();
  }
}
