package dev.amo.auth;

import dev.amo.ApiError;
import java.time.Duration;
import java.time.Instant;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtClaimValidator;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtException;
import org.springframework.security.oauth2.jwt.JwtValidators;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

/** Verifies a Google ID token for an explicitly configured OAuth client audience. */
@Component
class GoogleIdentity {
  private final String webClientId;
  private final Set<String> audiences;
  private final JwtDecoder decoder;

  GoogleIdentity(
      @Value("${amo.google-client-id}") String webClientId,
      @Value("${amo.google-allowed-audiences}") String allowed) {
    this.webClientId = webClientId.strip();
    audiences = new HashSet<>();
    if (!this.webClientId.isBlank()) {
      audiences.add(this.webClientId);
    }
    Arrays.stream(allowed.split(","))
        .map(String::strip)
        .filter(s -> !s.isEmpty())
        .forEach(audiences::add);
    var requests = new SimpleClientHttpRequestFactory();
    requests.setConnectTimeout(Duration.ofSeconds(4));
    requests.setReadTimeout(Duration.ofSeconds(4));
    var google =
        NimbusJwtDecoder.withJwkSetUri("https://www.googleapis.com/oauth2/v3/certs")
            .restOperations(new RestTemplate(requests))
            .build();
    google.setJwtValidator(
        new DelegatingOAuth2TokenValidator<>(
            JwtValidators.createDefault(),
            new JwtClaimValidator<String>(
                "iss",
                value ->
                    "https://accounts.google.com".equals(value)
                        || "accounts.google.com".equals(value)),
            new JwtClaimValidator<List<String>>(
                "aud", value -> value != null && !value.isEmpty() && audiences.containsAll(value)),
            new JwtClaimValidator<String>(
                "azp", value -> value == null || audiences.contains(value)),
            new JwtClaimValidator<Instant>(
                "exp", value -> value != null && value.isAfter(Instant.now()))));
    decoder = google;
  }

  String webClientId() {
    return webClientId;
  }

  VerifiedGoogle verify(String token) {
    if (audiences.isEmpty()) {
      throw new ApiError(HttpStatus.SERVICE_UNAVAILABLE, "GOOGLE_LOGIN_NOT_CONFIGURED");
    }
    try {
      Jwt jwt = decoder.decode(token);
      String subject = jwt.getSubject();
      String email = jwt.getClaimAsString("email");
      String name = jwt.getClaimAsString("name");
      if (!Boolean.TRUE.equals(jwt.getClaims().get("email_verified"))
          || subject == null
          || subject.isBlank()
          || email == null
          || email.isBlank()) {
        throw new ApiError(HttpStatus.UNAUTHORIZED, "INVALID_GOOGLE_IDENTITY");
      }
      return new VerifiedGoogle(subject, email, name == null || name.isBlank() ? email : name);
    } catch (JwtException | IllegalArgumentException e) {
      throw new ApiError(HttpStatus.UNAUTHORIZED, "INVALID_GOOGLE_IDENTITY");
    }
  }

  record VerifiedGoogle(String subject, String email, String name) {}
}
