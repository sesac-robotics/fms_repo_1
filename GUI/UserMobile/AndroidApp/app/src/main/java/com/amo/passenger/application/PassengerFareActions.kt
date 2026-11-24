package com.amo.passenger.application

import com.amo.passenger.data.PassengerFareApi
import com.amo.passenger.domain.RideFares
import com.amo.passenger.domain.Stop
import java.util.UUID
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update

/** Routes the local quote, replay-safe payment and destination intents from the ride screen. */
internal class PassengerFareActions(
    private val api: PassengerFareApi,
    private val state: MutableStateFlow<AmoUiState>,
    private val perform: (suspend () -> Unit) -> Unit
) {
    private var pending: Pending? = null

    /** Runs only against the current authenticated ride. */
    fun dispatch(action: FareAction) {
        val current = state.value
        val token = current.session?.token ?: return
        val rideId = current.selectedRideId ?: return
        val fare = current.fare?.takeIf { it.rideId == rideId } ?: return
        perform {
            when (action) {
                FareAction.Quote -> refresh(token, rideId, createQuote = true)
                FareAction.Prepay -> {
                    val quote = fare.initial.quote ?: return@perform
                    val key = attemptKey(quote.id)
                    val outcome = api.prepay(token, rideId, quote.id, key)
                    pending = null
                    publish(token, fare.copy(initial = outcome))
                }
                FareAction.AcceptChange -> {
                    val route = fare.route ?: return@perform
                    val key = attemptKey(route.quote.id)
                    val outcome = api.accept(token, rideId, route.quote.id, key)
                    pending = null
                    publish(token, fare.copy(route = outcome))
                }
                is FareAction.Propose -> publish(
                    token,
                    fare.copy(route = api.propose(token, rideId, action.destination))
                )
            }
        }
    }

    suspend fun refresh(token: String, rideId: String, createQuote: Boolean) {
        if (createQuote) {
            val quote = api.quote(token, rideId) ?: return
            publish(token, RideFares(rideId, quote, null))
        } else {
            api.load(token, rideId)?.let { publish(token, it) }
        }
    }

    /** Opens a recorded request and loads its saved fare and receipt. */
    fun openRide(rideId: String) {
        val token = state.value.session?.token ?: return
        perform {
            state.update { it.copy(selectedRideId = rideId, fare = null, screen = Screen.HOME) }
            refresh(token, rideId, createQuote = false)
        }
    }

    fun clear() {
        pending = null
    }

    private fun publish(token: String, snapshot: RideFares) {
        state.update { current ->
            if (current.session?.token == token && current.selectedRideId == snapshot.rideId) {
                current.copy(fare = snapshot)
            } else {
                current
            }
        }
    }

    private fun attemptKey(quoteId: Long): String = pending?.takeIf { it.quoteId == quoteId }?.key
        ?: UUID.randomUUID().toString().also { pending = Pending(quoteId, it) }

    private data class Pending(val quoteId: Long, val key: String)
}

internal sealed interface FareAction {
    data object Quote : FareAction
    data object Prepay : FareAction
    data object AcceptChange : FareAction
    data class Propose(val destination: Stop) : FareAction
}
