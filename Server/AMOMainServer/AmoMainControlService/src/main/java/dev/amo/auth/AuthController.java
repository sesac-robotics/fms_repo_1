package dev.amo.auth;

import dev.amo.auth.Identity.Access;
import dev.amo.auth.Identity.Member;
import dev.amo.auth.Identity.User;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.time.Duration;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseCookie;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/** Adapts sign-in for browsers with HttpOnly cookies and native clients with access tokens. */
@RestController
@RequestMapping("/api/auth")
class AuthController {
  private final AuthService auth;
  private final boolean secureCookie;

  AuthController(AuthService auth, @Value("${amo.cookie-secure}") boolean secureCookie) {
    this.auth = auth;
    this.secureCookie = secureCookie;
  }

  @PostMapping("/login")
  ResponseEntity<Access> login(@Valid @RequestBody Credentials body) {
    return signedIn(auth.login(body.email(), body.password()), HttpStatus.OK);
  }

  @PostMapping("/register")
  ResponseEntity<Access> register(@Valid @RequestBody SignUp body) {
    return signedIn(
        auth.registerPassenger(body.name(), body.email(), body.password()), HttpStatus.CREATED);
  }

  @PostMapping("/register/admin")
  @ResponseStatus(HttpStatus.ACCEPTED)
  Member registerAdmin(@Valid @RequestBody SignUp body) {
    return auth.registerStaff(body.name(), body.email(), body.password());
  }

  @GetMapping("/google/config")
  Map<String, String> googleConfig() {
    return Map.of("clientId", auth.googleClientId());
  }

  @PostMapping("/google")
  ResponseEntity<Access> google(@Valid @RequestBody GoogleToken body) {
    return signedIn(auth.loginGoogle(body.credential()), HttpStatus.OK);
  }

  @PostMapping("/google/link")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  void link(@AuthenticationPrincipal Jwt token, @Valid @RequestBody GoogleToken body) {
    auth.linkGoogle(Long.parseLong(token.getSubject()), body.credential());
  }

  @GetMapping("/me")
  User me(@AuthenticationPrincipal Jwt token) {
    return auth.me(Long.parseLong(token.getSubject()));
  }

  @GetMapping("/csrf")
  Map<String, String> csrf(CsrfToken token) {
    return Map.of("token", token.getToken());
  }

  @PostMapping("/logout")
  ResponseEntity<Void> logout(@AuthenticationPrincipal Jwt token) {
    auth.logout(token);
    return ResponseEntity.noContent()
        .header(HttpHeaders.SET_COOKIE, cookie("", Duration.ZERO))
        .build();
  }

  private ResponseEntity<Access> signedIn(Access access, HttpStatus status) {
    return ResponseEntity.status(status)
        .header(HttpHeaders.SET_COOKIE, cookie(access.token(), AmoJwt.TTL))
        .body(access);
  }

  private String cookie(String value, Duration age) {
    return ResponseCookie.from(SecurityConfiguration.ACCESS_COOKIE, value)
        .httpOnly(true)
        .sameSite("Lax")
        .secure(secureCookie)
        .path("/api")
        .maxAge(age)
        .build()
        .toString();
  }

  record Credentials(
      @NotBlank @Email @Size(max = 254) String email, @NotBlank @Size(max = 72) String password) {}

  record SignUp(
      @NotBlank @Size(max = 120) String name,
      @NotBlank @Email @Size(max = 254) String email,
      @NotBlank @Size(min = 10, max = 72) String password) {}

  record GoogleToken(@NotBlank @Size(max = 8192) String credential) {}
}
