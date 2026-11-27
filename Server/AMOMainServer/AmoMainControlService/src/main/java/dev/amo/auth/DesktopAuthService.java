package dev.amo.auth;

import dev.amo.ApiError;
import dev.amo.auth.DesktopCodeRepository.Source;
import dev.amo.auth.Identity.Access;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Base64;
import org.springframework.http.HttpStatus;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Exchanges a short-lived, PKCE-bound browser authorization for a separate staff session. */
@Service
class DesktopAuthService {
  private static final Base64.Encoder BASE64_URL = Base64.getUrlEncoder().withoutPadding();

  private final DesktopCodeRepository codes;
  private final AccountRepository accounts;
  private final SessionRepository sessions;
  private final AmoJwt jwt;
  private final SecureRandom random = new SecureRandom();

  DesktopAuthService(
      DesktopCodeRepository codes,
      AccountRepository accounts,
      SessionRepository sessions,
      AmoJwt jwt) {
    this.codes = codes;
    this.accounts = accounts;
    this.sessions = sessions;
    this.jwt = jwt;
  }

  @Transactional
  public String authorize(Jwt browser, int port, String challenge) {
    var source = new Source(AmoJwt.sessionId(browser), Long.parseLong(browser.getSubject()));
    byte[] entropy = new byte[32];
    random.nextBytes(entropy);
    String code = BASE64_URL.encodeToString(entropy);
    codes.deleteExpired();
    if (!codes.create(digest(code), port, challenge, source)) {
      throw new ApiError(HttpStatus.UNAUTHORIZED, "SESSION_INACTIVE");
    }
    return code;
  }

  @Transactional
  public Access exchange(int port, String code, String verifier) {
    byte[] digest = digest(code);
    String challenge = challenge(verifier);
    var source = codes.find(digest, port, challenge).orElseThrow(DesktopAuthService::invalidCode);
    // Staff changes lock the account before revoking sessions. Keep the same order here.
    var account =
        accounts.lockActiveStaff(source.accountId()).orElseThrow(DesktopAuthService::invalidCode);
    if (!sessions.lockActive(source.sessionId(), source.accountId())
        || !codes.consume(digest, port, challenge)) {
      throw invalidCode();
    }
    return jwt.issue(account);
  }

  static String challenge(String verifier) {
    return BASE64_URL.encodeToString(digest(verifier));
  }

  private static byte[] digest(String value) {
    try {
      return MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.US_ASCII));
    } catch (NoSuchAlgorithmException failure) {
      throw new IllegalStateException("SHA-256 unavailable", failure);
    }
  }

  private static ApiError invalidCode() {
    return new ApiError(HttpStatus.UNAUTHORIZED, "DESKTOP_CODE_INVALID");
  }
}
