package dev.amo.web;

import dev.amo.ApiError;
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

  @ExceptionHandler({MethodArgumentNotValidException.class, HttpMessageNotReadableException.class})
  ResponseEntity<ErrorBody> invalid(Exception failure) {
    return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(new ErrorBody("INVALID_INPUT"));
  }

  record ErrorBody(String code) {}
}
