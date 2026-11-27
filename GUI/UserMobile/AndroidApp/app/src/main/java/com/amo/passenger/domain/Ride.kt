package com.amo.passenger.domain

/** Passenger stops defined by the AMoDE v0.2 map. */
enum class Stop {
    S1,
    S2,
    S3,
    S4
    ;

    companion object {
        fun parse(code: String): Stop? = entries.firstOrNull { it.name == code }
    }
}

/** A one-way request with distinct pickup and destination stops. */
data class RideRequest(val pickup: Stop, val destination: Stop) {
    init {
        require(pickup != destination) { "Pickup and destination must differ." }
    }
}

enum class RidePhase {
    RECEIVED,
    WAITING,
    ASSIGNED,
    PICKUP_CONFIRMED,
    BOARDED,
    ON_TRIP,
    STOPPED_WAIT,
    ARRIVAL_CONFIRMED,
    COMPLETE,
    CANCELLED,
    FAILED,
    UNKNOWN
    ;

    val isOpen: Boolean
        get() = this !in setOf(COMPLETE, CANCELLED, FAILED, UNKNOWN)

    companion object {
        /** Maps explicit server reports. A vehicle assignment alone never confirms motion. */
        fun from(requestStatus: String, tripStatus: String?): RidePhase {
            val request = fromCode(requestStatus)
            if (request == COMPLETE || request == CANCELLED || request == FAILED) return request
            val trip = tripStatus?.let(::fromCode)
            return trip?.takeIf { it != UNKNOWN } ?: request
        }

        private fun fromCode(value: String): RidePhase = when (value) {
            "RECEIVED", "REQUESTED" -> RECEIVED
            "WAITING_DISPATCH", "PENDING_DISPATCH", "WAITING" -> WAITING
            "ASSIGNED" -> ASSIGNED
            "PICKUP_CONFIRMED", "PICKUP_STOP_CONFIRMED" -> PICKUP_CONFIRMED
            "BOARDING_CONFIRMED", "BOARDED" -> BOARDED
            "DEPARTURE_CONFIRMED", "IN_PROGRESS", "ON_TRIP" -> ON_TRIP
            "STOPPED_WAIT" -> STOPPED_WAIT
            "ARRIVAL_CONFIRMED", "ARRIVED" -> ARRIVAL_CONFIRMED
            "COMPLETED" -> COMPLETE
            "CANCELLED" -> CANCELLED
            "FAILED" -> FAILED
            else -> UNKNOWN
        }
    }
}

/**
 * A request or trip owned by the signed-in passenger. The source call and the server receipt
 * timestamps are ISO-8601 instants. Distance is measured in meters.
 */
data class Ride(
    val id: String,
    val pickup: Stop?,
    val destination: Stop?,
    val phase: RidePhase,
    val vehicleNo: String?,
    val calledAt: String?,
    val receivedAt: String?,
    val pickupEtaAt: String?,
    val remainingDistanceMeters: Double?
)
