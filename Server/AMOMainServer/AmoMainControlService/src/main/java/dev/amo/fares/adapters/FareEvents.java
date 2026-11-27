package dev.amo.fares.adapters;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

/** Appends demo fare audit events within the caller's database transaction. */
@Component
class FareEvents {
  private final JdbcClient jdbc;

  FareEvents(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  void payment(long quoteId, String key, String outcome) {
    jdbc.sql(
            """
            INSERT INTO operation_events
              (id, request_id, dispatch_id, producer, event_key, event_type, result_code,
               occurred_at, received_at)
            SELECT nextval('amo_record_id'), q.request_id, t.dispatch_id, 'MAIN_CONTROL', :key,
                   CASE WHEN q.trip_id IS NULL THEN 'MOCK_PREPAYMENT_ATTEMPTED'
                        ELSE 'MOCK_DIFFERENCE_ATTEMPTED' END,
                   :result, statement_timestamp(), statement_timestamp()
            FROM ride_fare_quotes q LEFT JOIN trips t ON t.id = q.trip_id WHERE q.id = :quote
            """)
        .param("quote", quoteId)
        .param("key", "mock-fare:" + quoteId + ":" + key)
        .param("result", outcome)
        .update();
  }

  void hold(long requestId, Long quoteId, String reason) {
    jdbc.sql(
            """
            INSERT INTO operation_events
              (id, request_id, producer, event_key, event_type, result_code, occurred_at, received_at)
            VALUES (nextval('amo_record_id'), ?, 'MAIN_CONTROL', ?, 'MOCK_FARE_HELD', ?,
                    statement_timestamp(), statement_timestamp())
            ON CONFLICT (producer, event_key) DO NOTHING
            """)
        .params(requestId, "mock-hold:" + requestId + ":" + quoteId + ":" + reason, reason)
        .update();
  }

  void append(long requestId, Long dispatchId, String eventKey, String type, String result) {
    jdbc.sql(
            """
            INSERT INTO operation_events
              (id, request_id, dispatch_id, producer, event_key, event_type, result_code,
               occurred_at, received_at)
            VALUES (nextval('amo_record_id'), :request, :dispatch, 'MAIN_CONTROL',
                    :key, :type, :result, statement_timestamp(), statement_timestamp())
            """)
        .param("request", requestId)
        .param("dispatch", dispatchId, java.sql.Types.BIGINT)
        .param("key", eventKey)
        .param("type", type)
        .param("result", result)
        .update();
  }
}
