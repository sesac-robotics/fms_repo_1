package dev.amo.maincontrol;

import java.time.Instant;

/** A passenger's request plus recorded assignment and trip information when available. */
public record Ride(
    long id,
    String pickup,
    String destination,
    String status,
    String vehicleNo,
    Instant requestedAt,
    Instant pickupEtaAt,
    String tripStatus) {}
