package com.amo.passenger.application

import com.amo.passenger.data.AmoApi
import com.amo.passenger.data.ApiFailure
import com.amo.passenger.domain.Ride
import java.io.IOException
import java.time.Instant
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive

/** Polls the server for explicit ride updates only while a signed-in ride screen is in use. */
internal class TripFeed(private val api: AmoApi, private val state: MutableStateFlow<AmoUiState>) {
    suspend fun follow() {
        while (currentCoroutineContext().isActive) {
            delay(5_000)
            val snapshot = state.value
            val session = snapshot.session ?: continue
            if (snapshot.busy || snapshot.screen !in rideScreens) continue
            if (snapshot.screen == Screen.HOME &&
                snapshot.latestRide?.phase?.isOpen != true
            ) {
                continue
            }
            if (session.hasExpired(Instant.now())) {
                expire(snapshot)
                continue
            }

            try {
                val trips = api.trips(session.token)
                val fare = snapshot.selectedRideId?.let { api.fares.load(session.token, it) }
                state.update { current ->
                    if (current.canApplyPoll(snapshot)) {
                        current.withTrips(trips).copy(online = true, fare = fare)
                    } else {
                        current
                    }
                }
            } catch (failure: ApiFailure) {
                if (failure.status == 401) expire(snapshot)
            } catch (_: IOException) {
                state.update { current ->
                    if (current.canApplyPoll(snapshot)) current.copy(online = false) else current
                }
            }
        }
    }

    private fun expire(snapshot: AmoUiState) {
        state.compareAndSet(snapshot, AmoUiState(online = snapshot.online, issue = UiIssue.EXPIRED))
    }

    private companion object {
        val rideScreens = setOf(Screen.HOME, Screen.HISTORY)
    }
}

/** Preserves a selected request if present and otherwise picks a recorded open request. */
internal fun AmoUiState.withTrips(trips: List<Ride>): AmoUiState {
    val selection = selectedRideId?.takeIf { id -> trips.any { it.id == id } }
        ?: trips.firstOrNull { it.phase.isOpen }?.id
    return copy(trips = trips, selectedRideId = selection)
}

private fun AmoUiState.canApplyPoll(snapshot: AmoUiState): Boolean =
    session == snapshot.session && !busy && selectedRideId == snapshot.selectedRideId &&
        trips === snapshot.trips && fare === snapshot.fare
