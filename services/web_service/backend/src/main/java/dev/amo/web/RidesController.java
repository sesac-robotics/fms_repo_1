package dev.amo.web;

import dev.amo.auth.AuthService;
import dev.amo.maincontrol.Ride;
import dev.amo.maincontrol.RideService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Accepts Android passenger requests and exposes only the authenticated passenger's history. */
@RestController
class RidesController {
  private final AuthService auth;
  private final RideService rides;

  RidesController(AuthService auth, RideService rides) {
    this.auth = auth;
    this.rides = rides;
  }

  @PostMapping("/api/rides")
  Ride submit(@AuthenticationPrincipal Jwt token, @Valid @RequestBody Request body) {
    return rides.accept(passenger(token), body.pickup(), body.destination(), body.idempotencyKey());
  }

  @GetMapping("/api/me/trips")
  List<Ride> history(@AuthenticationPrincipal Jwt token) {
    return rides.history(passenger(token));
  }

  private long passenger(Jwt token) {
    return auth.passengerId(Long.parseLong(token.getSubject()));
  }

  record Request(
      @NotBlank @Pattern(regexp = "S[1-4]") String pickup,
      @NotBlank @Pattern(regexp = "S[1-4]") String destination,
      @NotBlank @Size(max = 128) String idempotencyKey) {}
}
