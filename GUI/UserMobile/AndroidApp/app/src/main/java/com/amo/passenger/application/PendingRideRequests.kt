package com.amo.passenger.application

import com.amo.passenger.domain.RideRequest
import java.time.Instant
import java.util.UUID

/** Retains the request identity and original call time until the server confirms it. */
internal class PendingRideRequests {
    data class Submission(val key: String, val calledAt: Instant)

    private val pending = mutableMapOf<RideRequest, Submission>()

    fun submissionFor(request: RideRequest, calledAt: Instant): Submission =
        pending.getOrPut(request) { Submission(UUID.randomUUID().toString(), calledAt) }

    fun forget(request: RideRequest) {
        pending.remove(request)
    }

    fun clear() {
        pending.clear()
    }
}
