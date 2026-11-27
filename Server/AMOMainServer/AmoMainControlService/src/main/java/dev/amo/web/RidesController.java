package dev.amo.web;

import dev.amo.ApiError;
import dev.amo.auth.AuthService;
import dev.amo.maincontrol.Ride;
import dev.amo.maincontrol.RideService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.List;
import org.springframework.http.HttpStatus;
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
  RideResponse submit(@AuthenticationPrincipal Jwt token, @Valid @RequestBody Request body) {
    return RideResponse.from(
        rides.accept(
            passenger(token),
            body.pickup(),
            body.destination(),
            body.idempotencyKey(),
            body.callTime()));
  }

  @GetMapping("/api/me/trips")
  List<RideResponse> history(@AuthenticationPrincipal Jwt token) {
    return rides.history(passenger(token)).stream().map(RideResponse::from).toList();
  }

  private long passenger(Jwt token) {
    return auth.passengerId(Long.parseLong(token.getSubject()));
  }

  /** Presents stored times and keeps the legacy receipt time field in the HTTP response. */
  record RideResponse(
      long id,
      String pickup,
      String destination,
      String status,
      String vehicleNo,
      Instant calledAt,
      Instant receivedAt,
      Instant pickupEtaAt,
      String tripStatus,
      Instant requestedAt) {
    static RideResponse from(Ride ride) {
      return new RideResponse(
          ride.id(),
          ride.pickup(),
          ride.destination(),
          ride.status(),
          ride.vehicleNo(),
          ride.calledAt(),
          ride.receivedAt(),
          ride.pickupEtaAt(),
          ride.tripStatus(),
          ride.requestedAt());
    }
  }

  record Request(
      @NotBlank @Pattern(regexp = "S[1-4]") String pickup,
      @NotBlank @Pattern(regexp = "S[1-4]") String destination,
      @NotBlank @Size(max = 128) String idempotencyKey,
      @Size(max = 40) @Pattern(regexp = "[0-9]{4}-.+") String calledAt) {
    Instant callTime() {
      if (calledAt == null) {
        return null;
      }
      try {
        return Instant.parse(calledAt);
      } catch (DateTimeParseException invalid) {
        throw new ApiError(HttpStatus.BAD_REQUEST, "INVALID_CALL_TIME");
      }
    }
  }
}
