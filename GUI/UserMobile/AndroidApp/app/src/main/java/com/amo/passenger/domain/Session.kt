package com.amo.passenger.domain

import java.time.Instant

/** Profile fields exposed by the passenger API. */
data class Passenger(val profileUserId: String?, val name: String, val email: String)

/** A passenger access token kept in memory for the lifetime of the app session. */
data class Session(val token: String, val expiresAt: Instant, val passenger: Passenger) {
    fun hasExpired(now: Instant): Boolean = !expiresAt.isAfter(now)
}
