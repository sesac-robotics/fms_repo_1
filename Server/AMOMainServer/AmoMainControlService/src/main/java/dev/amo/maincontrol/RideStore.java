package dev.amo.maincontrol;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

/** Storage operations required to accept and replay one-way ride requests. */
interface RideStore {
  Optional<Long> stop(String key);

  boolean insert(long userId, long pickupId, long destinationId, String key, Instant calledAt);

  StoredRide byKey(long userId, String key);

  void accepted(long requestId);

  List<Ride> history(long userId);

  /** Stored request identity and its current read model are loaded together. */
  record StoredRide(
      Ride ride, String serviceType, long pickupId, Long destinationId, Integer rentalSeconds) {
    boolean matchesOneWay(long pickup, long destination) {
      return "ONE_WAY".equals(serviceType)
          && pickupId == pickup
          && Long.valueOf(destination).equals(destinationId)
          && rentalSeconds == null;
    }
  }
}
