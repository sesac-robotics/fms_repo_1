package dev.amo.auth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import com.nimbusds.jose.jwk.source.ImmutableSecret;
import dev.amo.auth.Identity.Account;
import dev.amo.auth.Identity.Member;
import dev.amo.auth.Identity.Role;
import dev.amo.auth.Identity.Status;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.UUID;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.Test;
import org.springframework.mock.env.MockEnvironment;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.security.oauth2.jwt.JwtException;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;

class AmoJwtTest {
  private static final byte[] KEY = new byte[32];
  private static final String ISSUER = "https://amo.local";
  private static final String AUDIENCE = "amo-api";
  private final SessionRepository sessions = mock(SessionRepository.class);
  private final AmoJwt jwt =
      new AmoJwt(Base64.getEncoder().encodeToString(KEY), new MockEnvironment(), sessions);

  @Test
  void roundTripPersistsTheIdentityAndVerifiesTheSignedToken() {
    var account =
        new Account(
            new Member(13, "Operator", "operator@amo.test", Role.OPERATOR, Status.ACTIVE),
            null,
            null);

    var access = jwt.issue(account);
    var result = jwt.decoder().decode(access.token());

    assertThat(result.getSubject()).isEqualTo("13");
    assertThat(result.getAudience()).containsExactly(AUDIENCE);
    assertThat(AmoJwt.sessionId(result)).isNotNull();
    assertThat(Duration.between(result.getIssuedAt(), result.getExpiresAt()))
        .isEqualTo(Duration.ofMinutes(20));
    verify(sessions).create(any(UUID.class), eq(13L), eq(access.expiresAt()));
  }

  @Test
  void demoSessionLastsTwelveHours() {
    var environment = new MockEnvironment();
    environment.setActiveProfiles("demo");
    var demo = new AmoJwt(Base64.getEncoder().encodeToString(KEY), environment, sessions);
    var account =
        new Account(
            new Member(13, "Operator", "operator@amo.test", Role.OPERATOR, Status.ACTIVE),
            null,
            null);
    var access = demo.issue(account);
    var claims = demo.decoder().decode(access.token());

    assertThat(Duration.between(claims.getIssuedAt(), claims.getExpiresAt()))
        .isEqualTo(Duration.ofHours(12));
    verify(sessions).create(any(UUID.class), eq(13L), eq(access.expiresAt()));
  }

  @Test
  void rejectsWrongSignatureIssuerAudienceAndExpiredToken() {
    byte[] wrongKey = KEY.clone();
    wrongKey[0] = 1;
    Instant nextHour = Instant.now().plusSeconds(3600);
    assertInvalid(sign(wrongKey, ISSUER, AUDIENCE, nextHour));
    assertInvalid(sign(KEY, "https://other.invalid", AUDIENCE, nextHour));
    assertInvalid(sign(KEY, ISSUER, "other-api", nextHour));
    assertInvalid(sign(KEY, ISSUER, AUDIENCE, Instant.now().minusSeconds(1)));
  }

  private void assertInvalid(String token) {
    assertThatThrownBy(() -> jwt.decoder().decode(token)).isInstanceOf(JwtException.class);
  }

  private static String sign(byte[] key, String issuer, String audience, Instant expiration) {
    var encoder = new NimbusJwtEncoder(new ImmutableSecret<>(new SecretKeySpec(key, "HmacSHA256")));
    var claims =
        JwtClaimsSet.builder()
            .issuer(issuer)
            .audience(List.of(audience))
            .subject("13")
            .id(UUID.randomUUID().toString())
            .expiresAt(expiration)
            .build();
    return encoder
        .encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(), claims))
        .getTokenValue();
  }
}
