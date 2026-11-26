package dev.amo.web;

import dev.amo.ApiError;
import dev.amo.vision.application.RecordVisionObservation;
import dev.amo.vision.domain.VisionObservation;
import dev.amo.vision.domain.VisionObservation.Outcome;
import dev.amo.vision.domain.VisionObservation.Source;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/** Adapts the internal AI Interface JSON contract to the observation use case. */
@RestController
class VisionObservationController {
  private final RecordVisionObservation recorder;

  VisionObservationController(RecordVisionObservation recorder) {
    this.recorder = recorder;
  }

  @PostMapping(path = "/internal/vision/observations", consumes = "application/json")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  void record(@Valid @RequestBody Input input) {
    switch (recorder.record(input.observation(), Instant.now())) {
      case ACCEPTED -> {}
      case INVALID_OBSERVATION ->
          throw new ApiError(HttpStatus.BAD_REQUEST, "INVALID_VISION_OBSERVATION");
      case UNKNOWN_VEHICLE -> throw new ApiError(HttpStatus.NOT_FOUND, "VEHICLE_NOT_FOUND");
    }
  }

  record Input(
      @NotNull UUID resultId,
      @NotNull @Pattern(regexp = "[A-Za-z0-9_-]{1,64}") String vehicleNo,
      @NotNull Source source,
      @NotNull @Pattern(regexp = "[A-Za-z0-9_.:-]{1,96}") String frameId,
      @NotNull Instant capturedAt,
      @NotNull Instant processedAt,
      @NotNull Outcome outcome,
      @Pattern(regexp = "[A-Z0-9_]{1,40}") String label,
      Double confidence) {
    VisionObservation observation() {
      return new VisionObservation(
          resultId,
          vehicleNo,
          source,
          frameId,
          capturedAt.truncatedTo(ChronoUnit.MICROS),
          processedAt.truncatedTo(ChronoUnit.MICROS),
          outcome,
          label,
          confidence);
    }
  }
}
