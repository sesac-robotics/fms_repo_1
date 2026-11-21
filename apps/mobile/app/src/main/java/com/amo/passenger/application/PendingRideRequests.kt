package com.amo.passenger.application

import com.amo.passenger.domain.RideRequest
import java.util.UUID

/** Reuses a request key until the server confirms it, including retries after a timeout. */
internal class PendingRideRequests {
    private val keys = mutableMapOf<RideRequest, String>()

    fun keyFor(request: RideRequest): String = keys.getOrPut(request) {
        UUID.randomUUID().toString()
    }

    fun forget(request: RideRequest) {
        keys.remove(request)
    }

    fun clear() {
        keys.clear()
    }
}
