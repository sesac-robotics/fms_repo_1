package dev.amo.auth;

import dev.amo.auth.Identity.Account;
import dev.amo.auth.Identity.Member;
import dev.amo.auth.Identity.Role;
import dev.amo.auth.Identity.Status;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** PostgreSQL account and provider identity adapter. */
@Repository
class AccountRepository {
  private final JdbcClient db;

  AccountRepository(JdbcClient jdbc) {
    this.db = jdbc;
  }

  Optional<Account> findByEmail(String email) {
    return db.sql("SELECT * FROM amo_accounts WHERE email = ?")
        .param(email)
        .query(AccountRepository::account)
        .optional();
  }

  Optional<Account> findById(long id) {
    return db.sql("SELECT * FROM amo_accounts WHERE id = ?")
        .param(id)
        .query(AccountRepository::account)
        .optional();
  }

  Optional<Account> findGoogle(String subject) {
    return db.sql(
            """
        SELECT a.* FROM amo_accounts a
        JOIN amo_provider_links p ON a.id = p.account_id
        WHERE p.issuer = 'https://accounts.google.com' AND p.subject = ?
        """)
        .param(subject)
        .query(AccountRepository::account)
        .optional();
  }

  long createPassengerProfile(String name, String email) {
    return db.sql(
            """
        INSERT INTO users (id, name, contact, registered_at)
        VALUES (nextval('amo_record_id'), ?, ?, CURRENT_TIMESTAMP) RETURNING id
        """)
        .param(name)
        .param(email)
        .query(Long.class)
        .single();
  }

  Account insert(String email, String name, String hash, Role role, Status status, Long userId) {
    return db.sql(
            """
        INSERT INTO amo_accounts (email, name, password_hash, role, status, profile_user_id)
        VALUES (?, ?, ?, ?, ?, ?) RETURNING *
        """)
        .param(email)
        .param(name)
        .param(hash)
        .param(role.name())
        .param(status.name())
        .param(userId)
        .query(AccountRepository::account)
        .single();
  }

  void linkGoogle(long accountId, String subject) {
    db.sql(
            """
        INSERT INTO amo_provider_links (issuer, subject, account_id)
        VALUES ('https://accounts.google.com', ?, ?)
        """)
        .param(subject)
        .param(accountId)
        .update();
  }

  List<Member> members() {
    return db
        .sql("SELECT * FROM amo_accounts ORDER BY id LIMIT 250")
        .query(AccountRepository::account)
        .list()
        .stream()
        .map(Account::member)
        .toList();
  }

  void lockActiveAdmins() {
    db.sql(
            "SELECT id FROM amo_accounts WHERE role = 'ADMIN' AND status = 'ACTIVE' ORDER BY id FOR UPDATE")
        .query(Long.class)
        .list();
  }

  Optional<Member> changeStaff(long id, Role role, Status status) {
    return db.sql(
            """
        UPDATE amo_accounts SET role = ?, status = ?
        WHERE id = ? AND role <> 'PASSENGER' RETURNING *
        """)
        .param(role.name())
        .param(status.name())
        .param(id)
        .query(AccountRepository::account)
        .optional()
        .map(Account::member);
  }

  void audit(long actorId, long memberId, String action) {
    db.sql("INSERT INTO amo_admin_audit (actor_id, member_id, action) VALUES (?, ?, ?)")
        .param(actorId)
        .param(memberId)
        .param(action)
        .update();
  }

  static Account account(ResultSet row, int unused) throws SQLException {
    return new Account(
        new Member(
            row.getLong("id"),
            row.getString("name"),
            row.getString("email"),
            Role.valueOf(row.getString("role")),
            Status.valueOf(row.getString("status"))),
        row.getString("password_hash"),
        row.getObject("profile_user_id", Long.class));
  }
}
