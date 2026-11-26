package dev.amo.auth;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import org.springframework.security.authorization.AuthorizationDecision;
import org.springframework.security.authorization.AuthorizationManager;
import org.springframework.security.web.access.intercept.RequestAuthorizationContext;

/**
 * Checks a dedicated machine credential without using an AMO staff session. Used by the Vision
 * detectors and the SignalKit bridge, each with its own key and header.
 */
final class VisionIngressKey {
  private VisionIngressKey() {}

  /** Allow a request that presents the configured key in the named header. */
  static AuthorizationManager<RequestAuthorizationContext> authorization(
      String configured, String header) {
    return (auth, context) ->
        new AuthorizationDecision(matches(configured, context.getRequest().getHeader(header)));
  }

  static boolean matches(String configured, String supplied) {
    return configured.length() >= 32
        && supplied != null
        && MessageDigest.isEqual(
            configured.getBytes(StandardCharsets.UTF_8), supplied.getBytes(StandardCharsets.UTF_8));
  }
}
