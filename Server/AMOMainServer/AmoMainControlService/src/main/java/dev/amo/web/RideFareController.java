package dev.amo.web;

import dev.amo.auth.AuthService;
import dev.amo.fares.application.FareService;
import dev.amo.fares.domain.Fare.View;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import org.springframework.context.annotation.Profile;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Exchanges local mock fare terms and statuses for the authenticated owner of an existing call. */
@RestController
@Profile("demo")
class RideFareController {
  private final AuthService auth;
  private final FareService fares;

  RideFareController(AuthService auth, FareService fares) {
    this.auth = auth;
    this.fares = fares;
  }

  @GetMapping("/api/rides/{requestId}/fare")
  View read(@AuthenticationPrincipal Jwt token, @PathVariable long requestId) {
    return fares.read(passenger(token), requestId, Instant.now());
  }

  @PostMapping("/api/rides/{requestId}/mock-quote")
  View quote(@AuthenticationPrincipal Jwt token, @PathVariable long requestId) {
    return fares.quote(passenger(token), requestId, Instant.now());
  }

  @PostMapping("/api/rides/{requestId}/mock-prepayment")
  View prepay(
      @AuthenticationPrincipal Jwt token,
      @PathVariable long requestId,
      @Valid @RequestBody Payment body) {
    return fares.prepay(passenger(token), requestId, body.quoteId(), body.key(), Instant.now());
  }

  private long passenger(Jwt token) {
    return auth.passengerId(Long.parseLong(token.getSubject()));
  }

  record Payment(@Positive long quoteId, @NotBlank @Size(max = 128) String key) {}
}
