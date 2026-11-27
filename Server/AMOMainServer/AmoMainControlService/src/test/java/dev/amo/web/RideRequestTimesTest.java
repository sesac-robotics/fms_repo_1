package dev.amo.web;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import dev.amo.ApiError;
import dev.amo.maincontrol.Ride;
import java.time.Instant;
import org.junit.jupiter.api.Test;

class RideRequestTimesTest {
  @Test
  void readsOptionalClientCallTimeWithoutSubstitutingReceiptTime() {
    var call = new RidesController.Request("S1", "S2", "test-key", "2026-11-21T12:00:00Z");
    var legacy = new RidesController.Request("S1", "S2", "test-key", null);
    assertThat(call.callTime()).isEqualTo(Instant.parse("2026-11-21T12:00:00Z"));
    assertThat(legacy.callTime()).isNull();
  }

  @Test
  void rejectsInvalidClientCallTime() {
    var call = new RidesController.Request("S1", "S2", "test-key", "2026-11-21T28:00:00Z");
    assertThatThrownBy(call::callTime).isInstanceOf(ApiError.class).hasMessage("INVALID_CALL_TIME");
  }

  @Test
  void preservesReceiptTimeAsLegacyRequestedAt() {
    var calledAt = Instant.parse("2026-11-21T12:00:00Z");
    var receivedAt = calledAt.plusSeconds(2);
    var ride = new Ride(1, "S1", "S2", "RECEIVED", null, calledAt, receivedAt, null, null);
    var response = RidesController.RideResponse.from(ride);
    assertThat(response.calledAt()).isEqualTo(calledAt);
    assertThat(response.receivedAt()).isEqualTo(receivedAt);
    assertThat(response.requestedAt()).isEqualTo(receivedAt);
  }
}
