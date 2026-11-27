package dev.amo;

import org.springframework.http.HttpStatus;

/** Expected application error with a stable code for translated clients. */
public final class ApiError extends RuntimeException {
  private final HttpStatus status;
  private final String code;

  public ApiError(HttpStatus status, String code) {
    super(code);
    this.status = status;
    this.code = code;
  }

  public HttpStatus status() {
    return status;
  }

  public String code() {
    return code;
  }
}
