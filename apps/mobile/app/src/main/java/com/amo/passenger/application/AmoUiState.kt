package com.amo.passenger.application

import com.amo.passenger.domain.Ride
import com.amo.passenger.domain.Session
import com.amo.passenger.domain.Stop

internal enum class Screen {
    SIGN_IN,
    REGISTER,
    HOME,
    HISTORY,
    PROFILE,
    SETTINGS
}

internal enum class UiIssue {
    MISSING_FIELDS,
    INVALID_CREDENTIALS,
    EMAIL_IN_USE,
    INVALID_RIDE,
    EXPIRED,
    NOT_ALLOWED,
    NETWORK,
    SERVER,
    GOOGLE_UNAVAILABLE,
    GOOGLE_FAILED,
    GOOGLE_LINKED,
    GOOGLE_LINK_REQUIRED
}

internal data class AmoUiState(
    val screen: Screen = Screen.SIGN_IN,
    val session: Session? = null,
    val trips: List<Ride> = emptyList(),
    val selectedRideId: String? = null,
    val pickup: Stop? = null,
    val destination: Stop? = null,
    val busy: Boolean = false,
    val online: Boolean? = null,
    val issue: UiIssue? = null
) {
    fun allowedScreen(requested: Screen): Screen = when {
        session != null -> requested
        requested == Screen.REGISTER || requested == Screen.SETTINGS -> requested
        else -> Screen.SIGN_IN
    }

    val latestRide: Ride?
        get() = trips.firstOrNull { it.id == selectedRideId }
}
