package dev.amo.auth;

import dev.amo.ApiError;
import dev.amo.auth.Identity.Access;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.CacheControl;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Staff session handoff from a CSRF-checked Web session to a native PKCE client. */
@RestController
@RequestMapping("/api/auth/desktop")
class DesktopAuthController {
  private static final String CODE_PATTERN = "[A-Za-z0-9_-]{43}";
  private static final String VERIFIER_PATTERN = "[A-Za-z0-9._~-]{43,128}";
  private final DesktopAuthService desktop;

  DesktopAuthController(DesktopAuthService desktop) {
    this.desktop = desktop;
  }

  @PostMapping("/authorize")
  ResponseEntity<Authorized> authorize(
      @AuthenticationPrincipal Jwt browser,
      @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false) String authorization,
      @Valid @RequestBody Authorize body) {
    if (authorization != null) {
      throw new ApiError(HttpStatus.FORBIDDEN, "WEB_SESSION_REQUIRED");
    }
    var authorized = new Authorized(desktop.authorize(browser, body.port(), body.challenge()));
    return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(authorized);
  }

  @PostMapping("/token")
  ResponseEntity<Access> exchange(@Valid @RequestBody Exchange body) {
    var access = desktop.exchange(body.port(), body.code(), body.verifier());
    return ResponseEntity.ok().cacheControl(CacheControl.noStore()).body(access);
  }

  record Authorize(
      @Min(1024) @Max(65535) int port, @NotNull @Pattern(regexp = CODE_PATTERN) String challenge) {}

  record Exchange(
      @Min(1024) @Max(65535) int port,
      @NotNull @Pattern(regexp = CODE_PATTERN) String code,
      @NotNull @Pattern(regexp = VERIFIER_PATTERN) String verifier) {}

  record Authorized(String code) {}
}
