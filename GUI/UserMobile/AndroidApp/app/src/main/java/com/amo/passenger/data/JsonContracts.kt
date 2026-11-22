package com.amo.passenger.data

import com.amo.passenger.domain.Passenger
import com.amo.passenger.domain.Ride
import com.amo.passenger.domain.RidePhase
import com.amo.passenger.domain.Session
import com.amo.passenger.domain.Stop
import java.time.Instant
import java.time.format.DateTimeParseException
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

internal fun parseSession(json: String): Session = decode {
    val obj = JSONObject(json)
    Session(
        obj.optText("token") ?: throw ContractFailure(),
        expiry(obj),
        passenger(obj.getJSONObject("user"))
    )
}

internal fun parsePassenger(json: String): Passenger = decode {
    val obj = JSONObject(json)
    passenger(obj.optJSONObject("user") ?: obj)
}

internal fun parseGoogleClientId(json: String): String = decode {
    JSONObject(json).optText("clientId") ?: throw ApiFailure(503)
}

internal fun parseRide(json: String): Ride = decode {
    val obj = JSONObject(json)
    ride(obj.optJSONObject("ride") ?: obj)
}

internal fun parseRides(json: String): List<Ride> = decode {
    val items = if (json.trimStart().startsWith("[")) {
        JSONArray(json)
    } else {
        val obj = JSONObject(json)
        obj.optJSONArray("trips") ?: obj.optJSONArray("items") ?: throw ContractFailure()
    }
    List(items.length()) { ride(items.getJSONObject(it)) }
}

private fun ride(obj: JSONObject): Ride = Ride(
    obj.optText("id") ?: throw ContractFailure(),
    obj.optText("pickup")?.let(Stop::parse),
    obj.optText("destination")?.let(Stop::parse),
    RidePhase.from(obj.getString("status"), obj.optText("tripStatus")),
    obj.optText("vehicleNo"),
    obj.optText("calledAt"),
    obj.optText("receivedAt") ?: obj.optText("requestedAt"),
    obj.optText("pickupEtaAt"),
    obj.optDouble("remainingDistanceMeters").takeIf { it.isFinite() && it >= 0 }
)

private fun passenger(obj: JSONObject): Passenger {
    if (obj.optText("role") != "PASSENGER") throw RoleFailure()
    return Passenger(obj.optText("profileUserId"), obj.getString("name"), obj.getString("email"))
}

private fun expiry(obj: JSONObject): Instant {
    val value = obj.get("expiresAt")
    return if (value is Number) {
        Instant.ofEpochSecond(value.toLong())
    } else {
        Instant.parse(value.toString())
    }
}

private fun JSONObject.optText(field: String): String? =
    if (isNull(field)) null else optString(field).takeIf { it.isNotBlank() }

private inline fun <T> decode(block: () -> T): T = try {
    block()
} catch (_: JSONException) {
    throw ContractFailure()
} catch (_: DateTimeParseException) {
    throw ContractFailure()
}
