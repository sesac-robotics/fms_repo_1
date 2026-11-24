package dev.amo.fares.adapters;

import dev.amo.fares.application.FareStore;
import dev.amo.fares.domain.DemoTariff;
import dev.amo.fares.domain.Fare.Attempt;
import dev.amo.fares.domain.Fare.Estimate;
import dev.amo.fares.domain.Fare.PaymentStatus;
import dev.amo.fares.domain.Fare.Quote;
import dev.amo.fares.domain.Fare.Receipt;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class FareRepository implements FareStore {
  private final JdbcClient jdbc;
  private final FareEvents events;

  FareRepository(JdbcClient jdbc, FareEvents events) {
    this.jdbc = jdbc;
    this.events = events;
  }

  @Override
  public Optional<Request> lock(long requestId, long passengerId) {
    return jdbc.sql(
            """
            SELECT r.id, r.status, d.place_key, u.mock_payment_method_ref,
                   sqrt(power(p.x_m - d.x_m, 2) + power(p.y_m - d.y_m, 2)) AS schematic_m
            FROM service_requests r
            JOIN users u ON r.user_id = u.id
            JOIN places p ON r.pickup_place_id = p.id
            JOIN places d ON r.destination_place_id = d.id AND p.map_version_id = d.map_version_id
            WHERE r.id = ? AND r.user_id = ? AND r.service_type = 'ONE_WAY'
            FOR UPDATE OF r
            """)
        .param(requestId)
        .param(passengerId)
        .query(
            (row, index) ->
                new Request(
                    row.getLong("id"),
                    row.getString("status"),
                    row.getString("place_key"),
                    row.getString("mock_payment_method_ref"),
                    DemoTariff.schematicEstimate(row.getDouble("schematic_m"))))
        .optional();
  }

  @Override
  public Optional<Quote> initialQuote(long requestId) {
    return jdbc.sql(
            "SELECT * FROM ride_fare_quotes WHERE request_id = ? AND route_revision_id IS NULL")
        .param(requestId)
        .query(FareRows::quote)
        .optional();
  }

  @Override
  public Quote saveInitialQuote(long requestId, Estimate estimate, Instant now) {
    Instant quotedAt = now.truncatedTo(ChronoUnit.MICROS);
    return jdbc.sql(
            """
            INSERT INTO ride_fare_quotes (request_id, distance_m, duration_s, tariff_version,
                amount_minor, currency_code, quoted_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING *
            """)
        .params(
            requestId,
            estimate.distanceMeters(),
            estimate.durationSeconds(),
            DemoTariff.VERSION,
            DemoTariff.price(estimate),
            DemoTariff.CURRENCY,
            quotedAt.atOffset(ZoneOffset.UTC),
            quotedAt.plus(DemoTariff.VALIDITY).atOffset(ZoneOffset.UTC))
        .query(FareRows::quote)
        .single();
  }

  @Override
  public Optional<Attempt> attempt(long quoteId, String key) {
    return jdbc.sql("SELECT * FROM ride_payment_attempts WHERE quote_id = ? AND attempt_key = ?")
        .params(quoteId, key)
        .query(FareRows::attempt)
        .optional();
  }

  @Override
  public Optional<Attempt> latestAttempt(long quoteId) {
    return jdbc.sql(
            """
            SELECT * FROM ride_payment_attempts WHERE quote_id = ?
            ORDER BY (result = 'SUCCEEDED') DESC, id DESC LIMIT 1
            """)
        .param(quoteId)
        .query(FareRows::attempt)
        .optional();
  }

  @Override
  public Attempt saveAttempt(
      Quote quote,
      String key,
      String method,
      long amountMinor,
      PaymentStatus outcome,
      Instant now) {
    Attempt attempt =
        jdbc.sql(
                """
                INSERT INTO ride_payment_attempts
                  (quote_id, attempt_key, method_ref, amount_minor, result, attempted_at)
                VALUES (?, ?, ?, ?, ?, ?) RETURNING *
                """)
            .params(
                quote.id(), key, method, amountMinor, outcome.name(), now.atOffset(ZoneOffset.UTC))
            .query(FareRows::attempt)
            .single();
    events.payment(quote.id(), key, outcome.name());
    return attempt;
  }

  @Override
  public Optional<Receipt> receipt(long requestId) {
    return jdbc.sql("SELECT * FROM ride_fare_settlements WHERE request_id = ?")
        .param(requestId)
        .query(FareRows::receipt)
        .optional();
  }

  @Override
  public Optional<CloseEvidence> closeEvidence(long requestId, long tripId) {
    return jdbc.sql(
            """
            SELECT t.id, t.dispatch_id, pc.id AS check_id
            FROM trips t JOIN dispatches d ON t.dispatch_id = d.id
            JOIN passenger_checks pc ON pc.trip_id = t.id
            WHERE d.request_id = ? AND t.id = ? AND t.status = 'COMPLETED'
              AND t.ended_at IS NOT NULL AND pc.check_kind = 'ALIGHTING' AND pc.result = 'CONFIRMED'
              AND EXISTS (
                SELECT 1 FROM operation_events e
                WHERE e.dispatch_id = d.id AND e.vehicle_id = d.vehicle_id
                  AND e.producer = 'DEMO_REPLAY' AND e.event_type = 'DEMO_DESTINATION_STOP_CONFIRMED'
                  AND e.place_id IS NOT NULL AND e.occurred_at <= pc.checked_at
              )
            ORDER BY pc.received_at, pc.id LIMIT 1
            """)
        .params(requestId, tripId)
        .query((row, index) -> new CloseEvidence(row.getLong(1), row.getLong(2), row.getLong(3)))
        .optional();
  }

  @Override
  public Receipt settle(long requestId, CloseEvidence evidence, Quote quote, Instant now) {
    Receipt receipt =
        jdbc.sql(
                """
                INSERT INTO ride_fare_settlements (trip_id, request_id, quote_id, alighting_check_id,
                    amount_minor, currency_code, receipt_ref, finalized_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING *
                """)
            .params(
                evidence.tripId(),
                requestId,
                quote.id(),
                evidence.alightingCheckId(),
                quote.amountMinor(),
                quote.currencyCode(),
                "AMO-DEMO-" + evidence.tripId(),
                now.atOffset(ZoneOffset.UTC))
            .query(FareRows::receipt)
            .single();
    events.append(
        requestId,
        evidence.dispatchId(),
        "fare-finalized:" + evidence.tripId(),
        "FARE_FINALIZED",
        "SUCCEEDED");
    return receipt;
  }
}
