package dev.amo.auth;

import dev.amo.auth.Identity.Account;
import dev.amo.auth.Identity.Member;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Persists separately approved staff accounts bound to an existing Google passenger identity. */
@Repository
class GoogleOperators {
  private static final String ISSUER = "https://accounts.google.com";
  private final JdbcClient db;

  GoogleOperators(JdbcClient db) {
    this.db = db;
  }

  Optional<Member> add(long passengerId) {
    return db.sql(
            """
            INSERT INTO amo_accounts (email, name, role, status, google_passenger_id)
            SELECT a.email, a.name, 'OPERATOR', 'ACTIVE', a.id FROM amo_accounts a
            JOIN amo_provider_links p ON p.account_id = a.id AND p.issuer = ?
            WHERE a.id = ? AND a.role = 'PASSENGER' AND a.status = 'ACTIVE'
            ON CONFLICT (google_passenger_id) DO NOTHING
            RETURNING *
            """)
        .params(ISSUER, passengerId)
        .query(AccountRepository::account)
        .optional()
        .map(Account::member);
  }

  Optional<Member> companion(long passengerId) {
    return db.sql("SELECT * FROM amo_accounts WHERE google_passenger_id = ?")
        .param(passengerId)
        .query(AccountRepository::account)
        .optional()
        .map(Account::member);
  }

  boolean isCompanion(long id) {
    return db.sql(
            "SELECT EXISTS (SELECT 1 FROM amo_accounts WHERE id = ? AND google_passenger_id IS NOT NULL)")
        .param(id)
        .query(Boolean.class)
        .single();
  }

  Optional<Account> staffIdentity(String subject, String email) {
    return db.sql(
            """
            SELECT a.* FROM amo_accounts a
            JOIN amo_provider_links p ON p.account_id = COALESCE(a.google_passenger_id, a.id)
            WHERE p.issuer = ? AND p.subject = ? AND a.email = ?
              AND a.role IN ('ADMIN', 'OPERATOR')
            """)
        .params(ISSUER, subject, email)
        .query(AccountRepository::account)
        .optional();
  }
}
