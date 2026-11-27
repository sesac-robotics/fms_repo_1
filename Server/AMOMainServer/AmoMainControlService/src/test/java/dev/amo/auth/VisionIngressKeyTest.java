package dev.amo.auth;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class VisionIngressKeyTest {
  @Test
  void defaultsToDisabledAndRequiresAnExactMachineKey() {
    String configured = "a".repeat(32);
    assertFalse(VisionIngressKey.matches("", ""));
    assertFalse(VisionIngressKey.matches("short", "short"));
    assertFalse(VisionIngressKey.matches(configured, null));
    assertFalse(VisionIngressKey.matches(configured, "b".repeat(32)));
    assertTrue(VisionIngressKey.matches(configured, configured));
  }
}
