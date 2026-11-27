package dev.amo.auth;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/** Checks the dedicated machine credential without using an AMO staff session. */
final class VisionIngressKey {
  private VisionIngressKey() {}

  static boolean matches(String configured, String supplied) {
    return configured.length() >= 32
        && supplied != null
        && MessageDigest.isEqual(
            configured.getBytes(StandardCharsets.UTF_8), supplied.getBytes(StandardCharsets.UTF_8));
  }
}
