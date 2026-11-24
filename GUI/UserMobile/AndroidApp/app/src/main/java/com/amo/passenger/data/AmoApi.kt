package com.amo.passenger.data

import com.amo.passenger.domain.Passenger
import com.amo.passenger.domain.Ride
import com.amo.passenger.domain.RideRequest
import com.amo.passenger.domain.Session
import java.time.Instant
import org.json.JSONObject

/** Translates the passenger API to domain data. Authenticated calls require an AMO access token. */
internal class AmoApi(base: String) {
    private val http = JsonHttp(base)
    val fares = PassengerFareApi(http)

    suspend fun health() {
        http.send("/api/health")
    }

    suspend fun signIn(email: String, password: String): Session =
        parseSession(http.send("/api/auth/login", body = credentials(email, password)))

    suspend fun register(name: String, email: String, password: String): Session {
        val body = credentials(email, password).put("name", name)
        return parseSession(http.send("/api/auth/register", body = body))
    }

    suspend fun googleClientId(): String = parseGoogleClientId(http.send("/api/auth/google/config"))

    suspend fun signInGoogle(credential: String): Session = parseSession(
        http.send("/api/auth/google", body = JSONObject().put("credential", credential))
    )

    suspend fun linkGoogle(token: String, credential: String) {
        http.send("/api/auth/google/link", token, JSONObject().put("credential", credential))
    }

    suspend fun profile(token: String): Passenger = parsePassenger(http.send("/api/auth/me", token))

    suspend fun signOut(token: String) {
        http.send("/api/auth/logout", token, post = true)
    }

    suspend fun trips(token: String): List<Ride> = parseRides(http.send("/api/me/trips", token))

    suspend fun requestRide(
        token: String,
        ride: RideRequest,
        key: String,
        calledAt: Instant
    ): Ride {
        val body = JSONObject()
            .put("pickup", ride.pickup.name)
            .put("destination", ride.destination.name)
            .put("idempotencyKey", key)
            .put("calledAt", calledAt.toString())
        return parseRide(http.send("/api/rides", token, body))
    }

    private fun credentials(email: String, password: String): JSONObject =
        JSONObject().put("email", email).put("password", password)
}
