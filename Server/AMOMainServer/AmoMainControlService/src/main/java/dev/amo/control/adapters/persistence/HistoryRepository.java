package dev.amo.control.adapters.persistence;

import dev.amo.control.application.HistoryQuery;
import dev.amo.control.application.HistoryQuery.Result;
import dev.amo.control.application.HistoryQuery.Ride;
import dev.amo.control.application.HistoryQuery.Trial;
import dev.amo.control.application.HistoryStore;
import java.time.OffsetDateTime;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Parameterized PostgreSQL queries for staff history. */
@Repository
class HistoryRepository implements HistoryStore {
  private static final String RIDES =
      """
      FROM service_requests
      WHERE received_at >= :from AND received_at < :until
        AND NOT EXISTS (
          SELECT 1 FROM operation_events review
          WHERE review.request_id = service_requests.id AND review.producer = 'DEMO_REVIEW'
        )
        AND (:text = '' OR strpos(lower(service_type), lower(:text)) > 0
          OR strpos(lower(status), lower(:text)) > 0 OR id::text = :text)
      """;
  private static final String TRIALS =
      """
      FROM amo_trial_history
      WHERE recorded_at >= :from AND recorded_at < :until
        AND (:text = '' OR strpos(lower(name), lower(:text)) > 0)
      """;

  private final JdbcClient db;

  HistoryRepository(JdbcClient db) {
    this.db = db;
  }

  @Override
  public Result<Ride> rides(HistoryQuery query) {
    var rows =
        bind(
                """
            SELECT r.*, initial.status AS prepayment, changed.status AS route_status,
                   changed.payment AS difference, applied.target, applied.revision_id,
                   fare.amount_minor, fare.currency_code, fare.receipt_ref, depot.phase
            FROM (
              SELECT id, service_type, status, received_at
            """
                    + RIDES
                    + " ORDER BY received_at DESC, id DESC LIMIT :rows OFFSET :offset) r "
                    + RideProgressReads.APPLIED_ROUTE
                    + RideProgressReads.HISTORY
                    + " ORDER BY r.received_at DESC, r.id DESC",
                query)
            .param("rows", query.rows())
            .param("offset", query.offset())
            .query(
                (row, index) ->
                    new Ride(
                        row.getLong("id"),
                        row.getString("service_type"),
                        row.getString("status"),
                        row.getObject("received_at", OffsetDateTime.class),
                        row.getString("prepayment"),
                        row.getString("route_status"),
                        row.getObject("revision_id", Long.class),
                        row.getString("target"),
                        row.getString("difference"),
                        row.getObject("amount_minor", Long.class),
                        row.getString("currency_code"),
                        row.getString("receipt_ref"),
                        row.getString("phase")))
            .list();
    long matching = bind("SELECT count(*) " + RIDES, query).query(Long.class).single();
    return new Result<>(rows, matching);
  }

  @Override
  public Result<Trial> trials(HistoryQuery query) {
    return browse(
        "id, name, recorded_at, passed, total, latency_ms",
        TRIALS,
        "recorded_at",
        query,
        (row, index) ->
            new Trial(
                row.getLong("id"),
                row.getString("name"),
                row.getObject("recorded_at", OffsetDateTime.class),
                row.getInt("passed"),
                row.getInt("total"),
                row.getInt("latency_ms")));
  }

  private <T> Result<T> browse(
      String columns, String source, String time, HistoryQuery query, RowMapper<T> mapper) {
    var rows =
        bind(
                "SELECT "
                    + columns
                    + " "
                    + source
                    + " ORDER BY "
                    + time
                    + " DESC, id DESC LIMIT :rows OFFSET :offset",
                query)
            .param("rows", query.rows())
            .param("offset", query.offset())
            .query(mapper)
            .list();
    long matching = bind("SELECT count(*) " + source, query).query(Long.class).single();
    return new Result<>(rows, matching);
  }

  private JdbcClient.StatementSpec bind(String sql, HistoryQuery query) {
    return db.sql(sql)
        .param("text", query.text())
        .param("from", query.from())
        .param("until", query.until());
  }
}
