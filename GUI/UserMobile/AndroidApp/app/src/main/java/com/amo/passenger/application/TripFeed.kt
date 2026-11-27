package com.amo.passenger.application

import com.amo.passenger.data.ApiFailure
import com.amo.passenger.domain.Ride
import com.amo.passenger.domain.RideFares
import java.io.IOException
import java.time.Instant
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive

/** Polls the server for explicit ride updates only while a signed-in ride screen is in use. */
internal class TripFeed(
    private val state: MutableStateFlow<AmoUiState>,
    private val loadTrips: suspend (String) -> List<Ride>,
    private val loadFare: suspend (String, String) -> RideFares?
) {
    suspend fun follow() {
        while (currentCoroutineContext().isActive) {
            delay(5_000)
            poll(Instant.now())
        }
    }

    /** Reads one snapshot for the active ride screen using a caller-supplied UTC instant. */
    suspend fun poll(now: Instant) {
        val snapshot = state.value
        val session = snapshot.session ?: return
        if (snapshot.busy || snapshot.screen !in rideScreens) return
        if (snapshot.screen == Screen.HOME && snapshot.latestRide?.phase?.isOpen != true) return
        if (session.hasExpired(now)) {
            expire(snapshot)
            return
        }

        try {
            val trips = loadTrips(session.token)
            val fare = snapshot.selectedRideId?.let { loadFare(session.token, it) }
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
