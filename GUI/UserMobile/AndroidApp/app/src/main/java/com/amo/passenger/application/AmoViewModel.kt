package com.amo.passenger.application

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.amo.passenger.BuildConfig
import com.amo.passenger.data.AmoApi
import com.amo.passenger.data.ApiFailure
import com.amo.passenger.data.ContractFailure
import com.amo.passenger.data.RoleFailure
import com.amo.passenger.domain.RideRequest
import com.amo.passenger.domain.Session
import com.amo.passenger.domain.Stop
import java.io.IOException
import java.time.Instant
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** Owns passenger UI state and coordinates use cases with the API. */
internal class AmoViewModel : ViewModel() {
    private val api = AmoApi(BuildConfig.API_BASE_URL)
    private val mutable = MutableStateFlow(AmoUiState())
    val state = mutable.asStateFlow()
    val fares = PassengerFareActions(api.fares, mutable, ::perform)
    private val tracking = TripFeed(mutable, api::trips, api.fares::load)
    private val pending = PendingRideRequests()

    init {
        viewModelScope.launch {
            try {
                api.health()
                mutable.update { it.copy(online = true) }
            } catch (_: IOException) {
                mutable.update { it.copy(online = false) }
            }
        }
    }

    fun navigate(screen: Screen) {
        val target = mutable.value.allowedScreen(screen)
        mutable.update { it.copy(screen = target, issue = null) }
        when (target) {
            Screen.HISTORY -> refreshTrips()
            Screen.PROFILE -> refreshProfile()
            else -> Unit
        }
    }

    fun chooseStop(isPickup: Boolean, stop: Stop) {
        mutable.update { value ->
            if (isPickup) {
                value.copy(pickup = stop, issue = null)
            } else {
                value.copy(destination = stop, issue = null)
            }
        }
    }

    fun signIn(email: String, password: String) {
        if (email.isBlank() || password.isBlank()) return report(UiIssue.MISSING_FIELDS)
        perform { accept(api.signIn(email.trim(), password)) }
    }

    fun register(name: String, email: String, password: String) {
        if (name.isBlank() || email.isBlank() || password.isBlank()) {
            return report(UiIssue.MISSING_FIELDS)
        }
        perform { accept(api.register(name.trim(), email.trim(), password)) }
    }

    suspend fun googleClientId(): String = api.googleClientId()

    fun signInGoogle(credential: String) {
        perform { accept(api.signInGoogle(credential)) }
    }

    fun linkGoogle(credential: String) {
        val token = activeSession()?.token ?: return
        perform {
            api.linkGoogle(token, credential)
            report(UiIssue.GOOGLE_LINKED)
        }
    }

    suspend fun followServerUpdates() = tracking.follow()

    fun report(issue: UiIssue) {
        mutable.update { it.copy(issue = issue) }
    }

    fun requestRide() {
        val token = activeSession()?.token ?: return
        val pickup = mutable.value.pickup
        val destination = mutable.value.destination
        if (pickup == null || destination == null || pickup == destination) {
            return report(UiIssue.INVALID_RIDE)
        }
        val request = RideRequest(pickup, destination)
        val calledAt = Instant.now()
        perform {
            val submission = pending.submissionFor(request, calledAt)
            val ride = api.requestRide(token, request, submission.key, submission.calledAt)
            pending.forget(request)
            mutable.update { current ->
                current.copy(
                    selectedRideId = ride.id,
                    trips = listOf(ride) + current.trips.filterNot { it.id == ride.id }
                )
            }
            fares.refresh(token, ride.id, createQuote = true)
        }
    }

    fun prepareNewRide() {
        mutable.update {
            it.copy(selectedRideId = null, pickup = null, destination = null, issue = null)
        }
    }

    fun refreshTrips() {
        val token = activeSession()?.token ?: return
        perform { loadTrips(token) }
    }

    fun refreshProfile() {
        val session = activeSession() ?: return
        perform {
            val profile = api.profile(session.token)
            mutable.update { it.copy(session = session.copy(passenger = profile)) }
        }
    }

    fun signOut() {
        val token = mutable.value.session?.token ?: return
        perform {
            try {
                api.signOut(token)
            } finally {
                pending.clear()
                fares.clear()
                mutable.value = AmoUiState(online = mutable.value.online)
            }
        }
    }

    private suspend fun accept(session: Session) {
        if (session.hasExpired(Instant.now())) return report(UiIssue.EXPIRED)
        mutable.update { it.copy(session = session, screen = Screen.HOME) }
        loadTrips(session.token)
    }

    private suspend fun loadTrips(token: String) {
        val trips = api.trips(token)
        mutable.update { it.withTrips(trips) }
        mutable.value.selectedRideId?.let { fares.refresh(token, it, createQuote = false) }
    }

    private fun activeSession(): Session? {
        val session = mutable.value.session ?: return null
        if (session.hasExpired(Instant.now())) {
            expire()
            return null
        }
        return session
    }

    private fun expire() {
        pending.clear()
        fares.clear()
        mutable.value = AmoUiState(online = mutable.value.online, issue = UiIssue.EXPIRED)
    }

    private fun perform(action: suspend () -> Unit) {
        if (mutable.value.busy) return
        mutable.update { it.copy(busy = true, issue = null) }
        viewModelScope.launch {
            try {
                action()
                mutable.update { it.copy(online = true) }
            } catch (error: CancellationException) {
                throw error
            } catch (error: ApiFailure) {
                val issue = httpIssue(error, mutable.value)
                if (issue == UiIssue.EXPIRED) expire() else report(issue)
            } catch (_: RoleFailure) {
                report(UiIssue.NOT_ALLOWED)
            } catch (_: ContractFailure) {
                report(UiIssue.SERVER)
            } catch (_: IOException) {
                mutable.update { it.copy(online = false, issue = UiIssue.NETWORK) }
            } finally {
                mutable.update { it.copy(busy = false) }
            }
        }
    }
}
