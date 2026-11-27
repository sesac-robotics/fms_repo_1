package com.amo.passenger.domain

/** Server-provided demo terms, with whole meters, seconds and currency minor units. */
internal data class FareTerms(
    val id: Long,
    val distanceMeters: Long,
    val durationSeconds: Int,
    val amountMinor: Long,
    val currencyCode: String
)

/** A single finalized mock charge associated with its receipt reference. */
internal data class FareReceipt(
    val amountMinor: Long,
    val currencyCode: String,
    val reference: String
)

internal data class InitialFare(
    val quote: FareTerms?,
    val paymentStatus: String,
    val receipt: FareReceipt?
)

internal data class RouteFare(
    val quote: FareTerms,
    val proposedDestination: Stop,
    val effectiveDestination: Stop,
    val phase: String,
    val deltaMinor: Long,
    val paymentStatus: String
)

/** Latest snapshots of the same passenger request, with independent payment and route states. */
internal data class RideFares(val rideId: String, val initial: InitialFare, val route: RouteFare?)
