package com.amo.passenger.data

import com.amo.passenger.domain.FareReceipt
import com.amo.passenger.domain.FareTerms
import com.amo.passenger.domain.InitialFare
import com.amo.passenger.domain.RideFares
import com.amo.passenger.domain.RouteFare
import com.amo.passenger.domain.Stop
import org.json.JSONObject

/** Reads server-authoritative fare evidence and submits only passenger intents. */
internal class PassengerFareApi(private val http: JsonHttp) {
    suspend fun load(token: String, rideId: String): RideFares? {
        val initial = unsupported {
            initial(http.send(path(rideId, "fare"), token))
        } ?: return null
        val route = unsupported {
            route(http.send(path(rideId, "route-change"), token))
        }
        return RideFares(rideId, initial, route)
    }

    suspend fun quote(token: String, rideId: String): InitialFare? = unsupported {
        initial(http.send(path(rideId, "mock-quote"), token, JSONObject()))
    }

    suspend fun prepay(token: String, rideId: String, quoteId: Long, key: String): InitialFare =
        initial(http.send(path(rideId, "mock-prepayment"), token, payment(quoteId, key)))

    suspend fun accept(token: String, rideId: String, quoteId: Long, key: String): RouteFare =
        route(http.send(path(rideId, "mock-change-accept"), token, payment(quoteId, key)))

    suspend fun propose(token: String, rideId: String, stop: Stop): RouteFare = route(
        http.send(
            path(rideId, "mock-change-propose"),
            token,
            JSONObject().put("destination", stop.name)
        )
    )

    private fun payment(quoteId: Long, key: String): JSONObject =
        JSONObject().put("quoteId", quoteId).put("key", key)

    private fun path(rideId: String, action: String): String {
        if (rideId.toLongOrNull()?.let { it > 0 } != true) throw ContractFailure()
        return "/api/rides/$rideId/$action"
    }

    private suspend fun <T> unsupported(read: suspend () -> T): T? = try {
        read()
    } catch (failure: ApiFailure) {
        if (failure.status != 404) throw failure
        null
    }

    private fun initial(payload: String): InitialFare = decode {
        val json = JSONObject(payload)
        InitialFare(
            json.optJSONObject("quote")?.let(::terms),
            json.getString("paymentStatus"),
            json.optJSONObject("receipt")?.let {
                FareReceipt(
                    it.getLong("amountMinor"),
                    it.getString("currencyCode"),
                    it.getString("reference")
                )
            }
        )
    }

    private fun route(payload: String): RouteFare = decode {
        val json = JSONObject(payload)
        RouteFare(
            terms(json.getJSONObject("quote")),
            Stop.parse(json.getString("proposedDestination")) ?: throw ContractFailure(),
            Stop.parse(json.getString("effectiveDestination")) ?: throw ContractFailure(),
            json.getString("status"),
            json.getLong("deltaMinor"),
            json.getString("paymentStatus")
        )
    }

    private fun terms(json: JSONObject): FareTerms {
        val estimate = json.getJSONObject("estimate")
        return FareTerms(
            json.getLong("id"),
            estimate.getLong("distanceMeters"),
            estimate.getInt("durationSeconds"),
            json.getLong("amountMinor"),
            json.getString("currencyCode")
        )
    }
}
