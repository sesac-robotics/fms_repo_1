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
