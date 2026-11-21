package dev.amo.auth;

import dev.amo.auth.Identity.Account;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Stores revocable JWT session identifiers and checks current account status. */
@Repository
class SessionRepository {
  private final JdbcClient db;

  SessionRepository(JdbcClient jdbc) {
    this.db = jdbc;
  }

  void create(UUID id, long accountId, Instant expiration) {
    db.sql("INSERT INTO amo_sessions (id, account_id, expires_at) VALUES (?, ?, ?)")
        .param(id)
        .param(accountId)
        .param(OffsetDateTime.ofInstant(expiration, ZoneOffset.UTC))
        .update();
  }

  Optional<Account> active(UUID sessionId, long accountId) {
    return db.sql(
            """
        SELECT a.* FROM amo_accounts a
        JOIN amo_sessions s ON a.id = s.account_id
        WHERE s.id = ? AND a.id = ? AND s.revoked_at IS NULL
          AND s.expires_at > CURRENT_TIMESTAMP AND a.status = 'ACTIVE'
        """)
        .param(sessionId)
        .param(accountId)
        .query(AccountRepository::account)
        .optional();
  }

  boolean lockActive(UUID sessionId, long accountId) {
    return db.sql(
            """
        SELECT id FROM amo_sessions
        WHERE id = ? AND account_id = ? AND revoked_at IS NULL AND expires_at > clock_timestamp()
        FOR UPDATE
        """)
        .param(sessionId)
        .param(accountId)
        .query(UUID.class)
        .optional()
        .isPresent();
  }

  void revoke(UUID sessionId, long accountId) {
    db.sql(
            """
        UPDATE amo_sessions SET revoked_at = CURRENT_TIMESTAMP
        WHERE id = ? AND account_id = ? AND revoked_at IS NULL
        """)
        .param(sessionId)
        .param(accountId)
        .update();
  }

  void revokeAccount(long accountId) {
    db.sql(
            """
        UPDATE amo_sessions SET revoked_at = CURRENT_TIMESTAMP
        WHERE account_id = ? AND revoked_at IS NULL
        """)
        .param(accountId)
        .update();
  }
}
