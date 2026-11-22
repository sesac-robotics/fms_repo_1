package dev.amo.auth;

import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Stores only the digest of a browser-to-desktop code and its authorized source. */
@Repository
class DesktopCodeRepository {
  private static final String LIVE_CODE =
      """
        WHERE code_digest = ? AND callback_port = ? AND challenge = ?
          AND expires_at > clock_timestamp()
        """;

  private final JdbcClient db;

  DesktopCodeRepository(JdbcClient jdbc) {
    this.db = jdbc;
  }

  void deleteExpired() {
    db.sql("DELETE FROM amo_desktop_codes WHERE expires_at <= clock_timestamp()").update();
  }

  boolean create(byte[] digest, int port, String challenge, Source source) {
    return db.sql(
                """
        INSERT INTO amo_desktop_codes
          (code_digest, callback_port, challenge, source_session_id, account_id, expires_at)
        SELECT ?, ?, ?, s.id, a.id, LEAST(s.expires_at, clock_timestamp() + interval '60 seconds')
        FROM amo_sessions s
        JOIN amo_accounts a ON a.id = s.account_id
        WHERE s.id = ? AND a.id = ? AND s.revoked_at IS NULL
          AND s.expires_at > clock_timestamp()
          AND a.status = 'ACTIVE' AND a.role IN ('ADMIN', 'OPERATOR')
        """)
            .param(digest)
            .param(port)
            .param(challenge)
            .param(source.sessionId())
            .param(source.accountId())
            .update()
        == 1;
  }

  Optional<Source> find(byte[] digest, int port, String challenge) {
    return db.sql("SELECT source_session_id, account_id FROM amo_desktop_codes " + LIVE_CODE)
        .param(digest)
        .param(port)
        .param(challenge)
        .query(
            (row, index) ->
                new Source(
                    row.getObject("source_session_id", UUID.class), row.getLong("account_id")))
        .optional();
  }

  boolean consume(byte[] digest, int port, String challenge) {
    return db.sql("DELETE FROM amo_desktop_codes " + LIVE_CODE)
            .param(digest)
            .param(port)
            .param(challenge)
            .update()
        == 1;
  }

  record Source(UUID sessionId, long accountId) {}
}
