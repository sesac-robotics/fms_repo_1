package dev.amo.auth;

import com.nimbusds.jose.jwk.source.ImmutableSecret;
import dev.amo.auth.Identity.Access;
import dev.amo.auth.Identity.Account;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.UUID;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.env.Environment;
import org.springframework.core.env.Profiles;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtClaimValidator;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.security.oauth2.jwt.JwtValidators;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;
import org.springframework.stereotype.Component;

/** Issues 20-minute AMO access tokens and verifies the signed token contract. */
@Component
public class AmoJwt {
  public static final Duration TTL = Duration.ofMinutes(20);
  private static final String ISSUER = "https://amo.local";
  private static final String AUDIENCE = "amo-api";
  private final SecretKey key;
  private final JwtEncoder encoder;
  private final SessionRepository sessions;

  AmoJwt(
      @Value("${amo.jwt-key}") String configured,
      Environment environment,
      SessionRepository sessions) {
    this.sessions = sessions;
    byte[] bytes;
    if (configured.isBlank() && environment.acceptsProfiles(Profiles.of("demo"))) {
      bytes = new byte[32];
      new SecureRandom().nextBytes(bytes);
    } else {
      bytes = Base64.getDecoder().decode(configured);
    }
    if (bytes.length < 32) {
      throw new IllegalStateException(
          "Set AMO_JWT_KEY to a Base64-encoded key of at least 32 bytes");
    }
    key = new SecretKeySpec(bytes, "HmacSHA256");
    encoder = new NimbusJwtEncoder(new ImmutableSecret<>(key));
  }

  Access issue(Account account) {
    Instant now = Instant.now();
    Instant expiration = now.plus(TTL);
    UUID sessionId = UUID.randomUUID();
    sessions.create(sessionId, account.member().id(), expiration);
    JwtClaimsSet claims =
        JwtClaimsSet.builder()
            .issuer(ISSUER)
            .audience(List.of(AUDIENCE))
            .subject(Long.toString(account.member().id()))
            .id(sessionId.toString())
            .issuedAt(now)
            .expiresAt(expiration)
            .build();
    String token =
        encoder
            .encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(), claims))
            .getTokenValue();
    return new Access(token, expiration, account.user());
  }

  JwtDecoder decoder() {
    NimbusJwtDecoder decoder =
        NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
    decoder.setJwtValidator(
        new DelegatingOAuth2TokenValidator<>(
            JwtValidators.createDefaultWithIssuer(ISSUER),
            new JwtClaimValidator<List<String>>(
                "aud", value -> value != null && value.contains(AUDIENCE)),
            new JwtClaimValidator<Instant>(
                "exp", value -> value != null && value.isAfter(Instant.now()))));
    return decoder;
  }

  static UUID sessionId(Jwt jwt) {
    return UUID.fromString(jwt.getId());
  }
}
