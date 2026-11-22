package dev.amo.auth;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import dev.amo.ApiError;
import dev.amo.auth.DesktopCodeRepository.Source;
import dev.amo.auth.Identity.Access;
import dev.amo.auth.Identity.Account;
import dev.amo.auth.Identity.Member;
import dev.amo.auth.Identity.Role;
import dev.amo.auth.Identity.Status;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.security.oauth2.jwt.Jwt;

class DesktopAuthServiceTest {
  // RFC 7636 Appendix B, S256 example.
  private static final String VERIFIER = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk";
  private static final String CHALLENGE = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM";
  private static final String CODE = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFG";
  private static final int PORT = 49152;
  private static final Source SOURCE = new Source(UUID.randomUUID(), 3);
  private static final Account ACCOUNT =
      new Account(
          new Member(3, "Operator", "operator@example.test", Role.OPERATOR, Status.ACTIVE),
          null,
          null);

  private final DesktopCodeRepository codes = mock(DesktopCodeRepository.class);
  private final AccountRepository accounts = mock(AccountRepository.class);
  private final SessionRepository sessions = mock(SessionRepository.class);
  private final AmoJwt jwt = mock(AmoJwt.class);
  private final DesktopAuthService desktop = new DesktopAuthService(codes, accounts, sessions, jwt);

  @Test
  void matchesTheStandardS256Challenge() {
    assertEquals(CHALLENGE, DesktopAuthService.challenge(VERIFIER));
  }

  @Test
  void persistsOnlyTheRandomCodesDigest() throws Exception {
    var browser =
        Jwt.withTokenValue("browser")
            .header("alg", "HS256")
            .claim("jti", SOURCE.sessionId().toString())
            .subject(Long.toString(SOURCE.accountId()))
            .build();
    when(codes.create(any(byte[].class), eq(PORT), eq(CHALLENGE), eq(SOURCE))).thenReturn(true);

    String code = desktop.authorize(browser, PORT, CHALLENGE);

    assertTrue(code.matches("[A-Za-z0-9_-]{43}"));
    var digest = ArgumentCaptor.forClass(byte[].class);
    verify(codes).create(digest.capture(), eq(PORT), eq(CHALLENGE), eq(SOURCE));
    assertArrayEquals(
        MessageDigest.getInstance("SHA-256").digest(code.getBytes(StandardCharsets.US_ASCII)),
        digest.getValue());
  }

  @Test
  void issuesASeparateTokenOnlyAfterAtomicallyConsumingTheCode() {
    var access = new Access("desktop", Instant.now().plusSeconds(1200), ACCOUNT.user());
    when(codes.find(any(byte[].class), eq(PORT), eq(CHALLENGE))).thenReturn(Optional.of(SOURCE));
    when(accounts.lockActiveStaff(SOURCE.accountId())).thenReturn(Optional.of(ACCOUNT));
    when(sessions.lockActive(SOURCE.sessionId(), SOURCE.accountId())).thenReturn(true);
    when(codes.consume(any(byte[].class), eq(PORT), eq(CHALLENGE))).thenReturn(true, false);
    when(jwt.issue(ACCOUNT)).thenReturn(access);

    assertEquals(access, desktop.exchange(PORT, CODE, VERIFIER));
    assertEquals(
        "DESKTOP_CODE_INVALID",
        assertThrows(ApiError.class, () -> desktop.exchange(PORT, CODE, VERIFIER)).code());

    var order = inOrder(codes, accounts, sessions, jwt);
    order.verify(codes).find(any(byte[].class), eq(PORT), eq(CHALLENGE));
    order.verify(accounts).lockActiveStaff(SOURCE.accountId());
    order.verify(sessions).lockActive(SOURCE.sessionId(), SOURCE.accountId());
    order.verify(codes).consume(any(byte[].class), eq(PORT), eq(CHALLENGE));
    order.verify(jwt).issue(ACCOUNT);
    verify(jwt).issue(ACCOUNT);
  }

  @Test
  void deniesTheCodeWhenTheBrowserSessionHasBeenRevoked() {
    when(codes.find(any(byte[].class), eq(PORT), eq(CHALLENGE))).thenReturn(Optional.of(SOURCE));
    when(accounts.lockActiveStaff(SOURCE.accountId())).thenReturn(Optional.of(ACCOUNT));

    assertEquals(
        "DESKTOP_CODE_INVALID",
        assertThrows(ApiError.class, () -> desktop.exchange(PORT, CODE, VERIFIER)).code());
    verifyNoInteractions(jwt);
  }
}
