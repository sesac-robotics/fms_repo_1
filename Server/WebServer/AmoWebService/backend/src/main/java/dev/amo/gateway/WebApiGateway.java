package dev.amo.gateway;

import dev.amo.gateway.MainControlLink.Request;
import dev.amo.gateway.MainControlLink.Response;
import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;
import org.springframework.http.CacheControl;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Relays browser and Android API requests to Main Control, which verifies access and acts. */
@RestController
final class WebApiGateway {
  private static final int MAX_BODY_BYTES = 750 * 1024;
  private static final int MAX_PATH_LENGTH = 4_096;
  private static final Pattern API_PATH = Pattern.compile("/api(?:/[A-Za-z0-9_-]+)+");
  private static final Set<String> REQUEST_HEADERS =
      Set.of(
          "accept",
          "authorization",
          "content-type",
          "cookie",
          "x-xsrf-token",
          "origin",
          "access-control-request-method",
          "access-control-request-headers");
  private static final Set<String> RESPONSE_HEADERS =
      Set.of(
          "allow",
          "cache-control",
          "content-language",
          "content-security-policy",
          "content-type",
          "expires",
          "pragma",
          "referrer-policy",
          "retry-after",
          "set-cookie",
          "strict-transport-security",
          "vary",
          "www-authenticate",
          "x-content-type-options",
          "x-frame-options",
          "access-control-allow-origin",
          "access-control-allow-credentials",
          "access-control-allow-methods",
          "access-control-allow-headers",
          "access-control-expose-headers",
          "access-control-max-age");

  private final MainControlLink mainControl;

  WebApiGateway(MainControlLink mainControl) {
    this.mainControl = mainControl;
  }

  @RequestMapping("/api/**")
  ResponseEntity<byte[]> forward(HttpServletRequest request) {
    String path = request.getRequestURI();
    String query = request.getQueryString();
    String target = query == null ? path : path + "?" + query;
    if (!API_PATH.matcher(path).matches()
        || target.length() > MAX_PATH_LENGTH
        || target.chars().anyMatch(c -> c < 32 || c == 127 || c == '#')) {
      return error(HttpStatus.BAD_REQUEST, "INVALID_API_PATH");
    }

    try {
      if (request.getContentLengthLong() > MAX_BODY_BYTES) {
        return error(HttpStatus.PAYLOAD_TOO_LARGE, "REQUEST_TOO_LARGE");
      }
      byte[] body = request.getInputStream().readNBytes(MAX_BODY_BYTES + 1);
      if (body.length > MAX_BODY_BYTES) {
        return error(HttpStatus.PAYLOAD_TOO_LARGE, "REQUEST_TOO_LARGE");
      }

      var response =
          mainControl.exchange(
              new Request(request.getMethod(), target, requestHeaders(request), body));
      return ResponseEntity.status(response.status())
          .headers(responseHeaders(response))
          .body(response.body());
    } catch (MainControlLink.RequestTooLarge tooLarge) {
      return error(HttpStatus.PAYLOAD_TOO_LARGE, "REQUEST_TOO_LARGE");
    } catch (SocketTimeoutException timeout) {
      return error(HttpStatus.GATEWAY_TIMEOUT, "MAIN_CONTROL_TIMEOUT");
    } catch (IOException failure) {
      return error(HttpStatus.BAD_GATEWAY, "MAIN_CONTROL_UNAVAILABLE");
    }
  }

  private static Map<String, List<String>> requestHeaders(HttpServletRequest request) {
    Map<String, List<String>> selected = new LinkedHashMap<>();
    for (String name : Collections.list(request.getHeaderNames())) {
      String normalized = name.toLowerCase(Locale.ROOT);
      if (REQUEST_HEADERS.contains(normalized)) {
        selected.put(normalized, Collections.list(request.getHeaders(name)));
      }
    }
    return selected;
  }

  private static HttpHeaders responseHeaders(Response response) {
    var selected = new HttpHeaders();
    if (response.headers() != null) {
      response
          .headers()
          .forEach(
              (name, values) -> {
                if (RESPONSE_HEADERS.contains(name.toLowerCase(Locale.ROOT)) && values != null) {
                  values.stream()
                      .filter(WebApiGateway::validHeaderValue)
                      .forEach(value -> selected.add(name, value));
                }
              });
    }
    return selected;
  }

  private static boolean validHeaderValue(String value) {
    return value != null && value.chars().noneMatch(c -> c < 32 && c != '\t' || c == 127);
  }

  private static ResponseEntity<byte[]> error(HttpStatus status, String code) {
    return ResponseEntity.status(status)
        .cacheControl(CacheControl.noStore())
        .contentType(MediaType.APPLICATION_JSON)
        .body(("{\"code\":\"" + code + "\"}").getBytes(StandardCharsets.UTF_8));
  }
}
