package dev.amo.auth;

import dev.amo.ApiError;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import org.springframework.http.HttpStatus;

/** Normalizes email and bounds password bytes to BCrypt's supported input length. */
final class Registration {
  private Registration() {}

  static String email(String value) {
    return value.strip().toLowerCase(Locale.ROOT);
  }

  static boolean validPasswordBytes(String value) {
    return value.getBytes(StandardCharsets.UTF_8).length <= 72;
  }

  static String name(String value) {
    String trimmed = value.strip();
    if (trimmed.isBlank() || trimmed.length() > 120) {
      throw new ApiError(HttpStatus.BAD_REQUEST, "INVALID_NAME");
    }
    return trimmed;
  }
}
