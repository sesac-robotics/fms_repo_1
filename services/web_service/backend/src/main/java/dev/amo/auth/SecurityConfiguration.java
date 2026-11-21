package dev.amo.auth;

import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Arrays;
import java.util.List;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.security.oauth2.server.resource.web.DefaultBearerTokenResolver;
import org.springframework.security.oauth2.server.resource.web.authentication.BearerTokenAuthenticationFilter;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.csrf.CookieCsrfTokenRepository;
import org.springframework.security.web.csrf.CsrfFilter;
import org.springframework.security.web.csrf.CsrfTokenRequestAttributeHandler;

/** Validates native bearer or Web cookie sessions and enforces platform roles on HTTP routes. */
@Configuration
class SecurityConfiguration {
  static final String ACCESS_COOKIE = "AMO_ACCESS";
  private static final String[] PUBLIC_READS = {
    "/api/health", "/api/auth/google/config", "/api/auth/csrf"
  };
  private static final String[] PUBLIC_WRITES = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/register/admin",
    "/api/auth/google",
    "/api/auth/desktop/token"
  };
  private static final Set<String> SAFE_METHODS = Set.of("GET", "HEAD", "OPTIONS", "TRACE");

  @Bean
  PasswordEncoder passwordEncoder() {
    return new BCryptPasswordEncoder();
  }

  @Bean
  SecurityFilterChain security(
      HttpSecurity http,
      AmoJwt jwt,
      SessionRepository sessions,
      @Value("${amo.cookie-secure}") boolean secureCookie)
      throws Exception {
    var bearer = new DefaultBearerTokenResolver();
    return http.sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
        .formLogin(AbstractHttpConfigurer::disable)
        .httpBasic(AbstractHttpConfigurer::disable)
        .logout(AbstractHttpConfigurer::disable)
        .csrf(AbstractHttpConfigurer::disable)
        .addFilterBefore(cookieCsrf(secureCookie), BearerTokenAuthenticationFilter.class)
        .exceptionHandling(
            config ->
                config
                    .authenticationEntryPoint(
                        (request, response, failure) ->
                            error(response, 401, "AUTHENTICATION_REQUIRED"))
                    .accessDeniedHandler(
                        (request, response, failure) -> error(response, 403, "ACCESS_DENIED")))
        .authorizeHttpRequests(
            routes ->
                routes
                    .requestMatchers(HttpMethod.GET, PUBLIC_READS)
                    .permitAll()
                    .requestMatchers(HttpMethod.POST, PUBLIC_WRITES)
                    .permitAll()
                    .requestMatchers(
                        HttpMethod.GET,
                        "/api/operations",
                        "/api/operations/requests/{requestId}/route",
                        "/api/menu")
                    .hasAnyRole("ADMIN", "OPERATOR")
                    .requestMatchers(HttpMethod.POST, "/api/auth/desktop/authorize")
                    .hasAnyRole("ADMIN", "OPERATOR")
                    .requestMatchers("/api/admin/**")
                    .hasRole("ADMIN")
                    .requestMatchers("/api/me/trips", "/api/rides")
                    .hasRole("PASSENGER")
                    .requestMatchers("/api/auth/**")
                    .authenticated()
                    .anyRequest()
                    .denyAll())
        .oauth2ResourceServer(
            auth ->
                auth.authenticationEntryPoint(
                        (request, response, failure) -> error(response, 401, "INVALID_SESSION"))
                    .bearerTokenResolver(
                        request -> {
                          String value = bearer.resolve(request);
                          if (value != null || publicRoute(request)) {
                            return value;
                          }
                          return accessCookie(request);
                        })
                    .jwt(
                        config ->
                            config
                                .decoder(jwt.decoder())
                                .jwtAuthenticationConverter(token -> session(token, sessions))))
        .build();
  }

  private static CsrfFilter cookieCsrf(boolean secureCookie) {
    var repository = new CookieCsrfTokenRepository();
    repository.setCookieCustomizer(
        cookie -> cookie.path("/api").sameSite("Lax").secure(secureCookie));
    var filter = new CsrfFilter(repository);
    filter.setRequestHandler(new CsrfTokenRequestAttributeHandler());
    // The resource server's default bearer exemption would also exempt our authentication cookie.
    filter.setRequireCsrfProtectionMatcher(
        request ->
            !SAFE_METHODS.contains(request.getMethod())
                && accessCookie(request) != null
                && !hasBearerHeader(request));
    filter.setAccessDeniedHandler(
        (request, response, failure) -> error(response, 403, "CSRF_TOKEN_REQUIRED"));
    return filter;
  }

  private static JwtAuthenticationToken session(Jwt jwt, SessionRepository sessions) {
    try {
      var account =
          sessions
              .active(AmoJwt.sessionId(jwt), Long.parseLong(jwt.getSubject()))
              .orElseThrow(() -> new OAuth2AuthenticationException("invalid_token"));
      return new JwtAuthenticationToken(
          jwt,
          List.of(new SimpleGrantedAuthority("ROLE_" + account.member().role().name())),
          jwt.getSubject());
    } catch (IllegalArgumentException | NullPointerException failure) {
      throw new OAuth2AuthenticationException("invalid_token");
    }
  }

  private static boolean hasBearerHeader(HttpServletRequest request) {
    String header = request.getHeader(HttpHeaders.AUTHORIZATION);
    return header != null && header.regionMatches(true, 0, "Bearer ", 0, 7);
  }

  private static boolean publicRoute(HttpServletRequest request) {
    String path = request.getRequestURI().substring(request.getContextPath().length());
    return switch (request.getMethod()) {
      case "GET" -> Arrays.asList(PUBLIC_READS).contains(path);
      case "POST" -> Arrays.asList(PUBLIC_WRITES).contains(path);
      default -> false;
    };
  }

  private static String accessCookie(HttpServletRequest request) {
    Cookie[] cookies = request.getCookies();
    return cookies == null
        ? null
        : Arrays.stream(cookies)
            .filter(cookie -> ACCESS_COOKIE.equals(cookie.getName()))
            .map(Cookie::getValue)
            .filter(value -> !value.isBlank())
            .findFirst()
            .orElse(null);
  }

  private static void error(HttpServletResponse response, int status, String code)
      throws IOException {
    response.setStatus(status);
    response.setContentType(MediaType.APPLICATION_JSON_VALUE);
    response.getWriter().print("{\"code\":\"" + code + "\"}");
  }
}
