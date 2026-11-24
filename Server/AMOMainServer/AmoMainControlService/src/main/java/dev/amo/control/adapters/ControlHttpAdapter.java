package dev.amo.control.adapters;

import dev.amo.control.adapters.ControlWire.Request;
import dev.amo.control.adapters.ControlWire.Response;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/** Adapts development TCP exchanges to the service's existing private API and authorization. */
final class ControlHttpAdapter {
  private static final int MAX_BODY = 768_000;
  private static final Set<String> REQUEST_HEADERS =
      Set.of("accept", "authorization", "content-type", "cookie", "origin", "x-xsrf-token");
  private static final Set<String> RESPONSE_HEADERS =
      Set.of("cache-control", "content-type", "pragma", "set-cookie", "www-authenticate");
  private static final Set<String> READ_PATHS =
      Set.of(
          "/api/health",
          "/api/operations",
          "/api/operations/trip-history",
          "/api/operations/test-history",
          "/api/menu",
          "/api/admin/menu",
          "/api/admin/members",
          "/api/admin/members/page",
          "/api/auth/me",
          "/api/auth/csrf",
          "/api/auth/google/config",
          "/api/me/trips");
  private static final Set<String> WRITE_PATHS =
      Set.of(
          "/api/rides",
          "/api/auth/login",
          "/api/auth/logout",
          "/api/auth/register",
          "/api/auth/register/admin",
          "/api/auth/google",
          "/api/auth/google/link",
          "/api/auth/desktop/authorize",
          "/api/auth/desktop/token");

  private final HttpClient http =
      HttpClient.newBuilder()
          .connectTimeout(Duration.ofSeconds(2))
          .followRedirects(HttpClient.Redirect.NEVER)
          .build();
  private final String privateOrigin;

  ControlHttpAdapter(int privatePort) {
    privateOrigin = "http://127.0.0.1:" + privatePort;
  }

  Response handle(Request request, boolean adminPort) throws IOException, InterruptedException {
    if (request == null
        || request.method() == null
        || request.path() == null
        || request.headers() == null
        || request.body() == null) {
      return Response.error(400, "INVALID_CONTROL_REQUEST");
    }
    URI route = URI.create(request.path());
    String path = route.getRawPath();
    if (route.isAbsolute()
        || route.getRawAuthority() != null
        || route.getRawFragment() != null
        || path == null
        || (adminPort && route.getRawQuery() != null)
        || !allowed(request.method(), path, adminPort)) {
      return Response.error(404, "CONTROL_PATH_NOT_FOUND");
    }

    Map<String, List<String>> headers = request.headers();
    if (adminPort
        && headers.entrySet().stream()
            .noneMatch(
                entry ->
                    entry.getKey().equalsIgnoreCase("authorization")
                        && entry.getValue() != null
                        && entry.getValue().size() == 1
                        && entry.getValue().getFirst() != null
                        && entry.getValue().getFirst().startsWith("Bearer "))) {
      return Response.error(401, "AUTHENTICATION_REQUIRED");
    }

    byte[] body = ControlWire.decode(request.body());
    if (body.length > MAX_BODY || (request.method().equals("GET") && body.length != 0)) {
      return Response.error(400, "INVALID_CONTROL_BODY");
    }
    var builder =
        HttpRequest.newBuilder(URI.create(privateOrigin + route.toASCIIString()))
            .timeout(Duration.ofSeconds(8))
            .method(request.method(), HttpRequest.BodyPublishers.ofByteArray(body));
    for (var header : headers.entrySet()) {
      String name = header.getKey().toLowerCase(Locale.ROOT);
      if (REQUEST_HEADERS.contains(name) && (!adminPort || name.equals("authorization"))) {
        if (header.getValue() == null || header.getValue().stream().anyMatch(v -> v == null)) {
          return Response.error(400, "INVALID_CONTROL_HEADER");
        }
        for (String value : header.getValue()) {
          builder.header(name, value);
        }
      }
    }

    var response = http.send(builder.build(), HttpResponse.BodyHandlers.ofInputStream());
    try (InputStream input = response.body()) {
      byte[] payload = input.readNBytes(MAX_BODY + 1);
      if (payload.length > MAX_BODY) {
        return Response.error(502, "CONTROL_RESPONSE_TOO_LARGE");
      }
      Map<String, List<String>> responseHeaders = new LinkedHashMap<>();
      response
          .headers()
          .map()
          .forEach(
              (name, values) -> {
                if (RESPONSE_HEADERS.contains(name)) {
                  responseHeaders.put(name, values);
                }
              });
      return new Response(response.statusCode(), responseHeaders, ControlWire.encode(payload));
    }
  }

  private static boolean allowed(String method, String path, boolean adminPort) {
    if (adminPort) {
      return method.equals("GET") && path.equals("/api/operations");
    }
    return switch (method) {
      case "GET" ->
          READ_PATHS.contains(path)
              || path.matches("/api/operations/requests/[0-9]+/route")
              || path.matches("/api/rides/[0-9]+/fare");
      case "POST" ->
          WRITE_PATHS.contains(path)
              || path.matches("/api/rides/[0-9]+/mock-(quote|prepayment)")
              || path.matches("/api/admin/demo/rides/[0-9]+/observe");
      case "PUT" -> path.matches("/api/admin/(?:members/[0-9]+/approval|menu/[a-zA-Z0-9_-]+)");
      default -> false;
    };
  }
}
