package dev.amo.web;

import dev.amo.ApiError;
import dev.amo.fares.application.FareFailure;
import dev.amo.maincontrol.MainControlFailure;
import dev.amo.replay.application.TripReplayService.ReplayFailure;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/** Formats expected errors without exposing raw input, credentials, or internal details. */
@RestControllerAdvice
class ApiExceptionHandler {
  @ExceptionHandler(ApiError.class)
  ResponseEntity<ErrorBody> known(ApiError failure) {
    return ResponseEntity.status(failure.status()).body(new ErrorBody(failure.code()));
  }

  @ExceptionHandler(MainControlFailure.class)
  ResponseEntity<ErrorBody> rejected(MainControlFailure failure) {
    HttpStatus status =
        switch (failure.reason()) {
          case IDEMPOTENCY_KEY_CONFLICT -> HttpStatus.CONFLICT;
          case MENU_NOT_FOUND -> HttpStatus.NOT_FOUND;
          case IDENTICAL_STOPS, UNKNOWN_STOP, SETTINGS_MUST_REMAIN_VISIBLE ->
              HttpStatus.BAD_REQUEST;
        };
    return ResponseEntity.status(status).body(new ErrorBody(failure.reason().name()));
  }

  @ExceptionHandler(FareFailure.class)
  ResponseEntity<ErrorBody> fareRejected(FareFailure failure) {
    HttpStatus status =
        failure.reason() == FareFailure.Reason.RIDE_NOT_FOUND
            ? HttpStatus.NOT_FOUND
            : HttpStatus.CONFLICT;
    return ResponseEntity.status(status).body(new ErrorBody(failure.reason().name()));
  }

  @ExceptionHandler(ReplayFailure.class)
  ResponseEntity<ErrorBody> replayRejected(ReplayFailure failure) {
    return ResponseEntity.status(HttpStatus.CONFLICT).body(new ErrorBody(failure.getMessage()));
  }

  @ExceptionHandler({MethodArgumentNotValidException.class, HttpMessageNotReadableException.class})
  ResponseEntity<ErrorBody> invalid(Exception failure) {
    return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(new ErrorBody("INVALID_INPUT"));
  }

  record ErrorBody(String code) {}
}
