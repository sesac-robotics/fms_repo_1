package dev.amo.auth;

import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/** Creates only fictional users on the explicit demo profile. */
@Component
@Profile("demo")
class DemoAccounts implements ApplicationRunner {
  private final JdbcClient jdbc;
  private final PasswordEncoder passwords;

  DemoAccounts(JdbcClient jdbc, PasswordEncoder passwords) {
    this.jdbc = jdbc;
    this.passwords = passwords;
  }

  @Override
  @Transactional
  public void run(ApplicationArguments args) {
    String hash = passwords.encode("AmoDemo!2026");
    jdbc.sql(
            """
        INSERT INTO amo_accounts (email, name, password_hash, role, status, profile_user_id)
        VALUES ('admin@amo.test', 'Demo Administrator', ?, 'ADMIN', 'ACTIVE', NULL),
               ('operator@amo.test', 'Demo Operator', ?, 'OPERATOR', 'ACTIVE', NULL),
               ('passenger@amo.test', 'Demo Passenger', ?, 'PASSENGER', 'ACTIVE', 1)
        ON CONFLICT DO NOTHING
        """)
        .param(hash)
        .param(hash)
        .param(hash)
        .update();
  }
}
