package com.amo.passenger.ui

import androidx.annotation.StringRes
import com.amo.passenger.R
import com.amo.passenger.application.Screen
import com.amo.passenger.application.UiIssue
import com.amo.passenger.data.Language
import com.amo.passenger.data.ThemeMode
import com.amo.passenger.domain.RidePhase
import com.amo.passenger.domain.Stop

@StringRes
internal fun Screen.label(): Int = when (this) {
    Screen.SIGN_IN -> R.string.sign_in
    Screen.REGISTER -> R.string.sign_up
    Screen.HOME -> R.string.home
    Screen.HISTORY -> R.string.history
    Screen.PROFILE -> R.string.profile
    Screen.SETTINGS -> R.string.settings
}

@StringRes
internal fun Stop?.label(): Int = when (this) {
    Stop.S1 -> R.string.stop_s1
    Stop.S2 -> R.string.stop_s2
    Stop.S3 -> R.string.stop_s3
    Stop.S4 -> R.string.stop_s4
    null -> R.string.unknown_stop
}

@StringRes
internal fun RidePhase.label(): Int = when (this) {
    RidePhase.RECEIVED -> R.string.r_received
    RidePhase.WAITING -> R.string.r_waiting
    RidePhase.ASSIGNED -> R.string.r_assigned
    RidePhase.PICKUP_CONFIRMED -> R.string.r_pickup
    RidePhase.BOARDED -> R.string.r_boarded
    RidePhase.ON_TRIP -> R.string.r_on_trip
    RidePhase.ARRIVAL_CONFIRMED -> R.string.r_arrived
    RidePhase.COMPLETE -> R.string.r_complete
    RidePhase.CANCELLED -> R.string.r_cancelled
    RidePhase.FAILED -> R.string.r_failed
    RidePhase.UNKNOWN -> R.string.r_unknown
}

@StringRes
internal fun UiIssue.label(): Int = when (this) {
    UiIssue.MISSING_FIELDS -> R.string.missing_fields
    UiIssue.INVALID_CREDENTIALS -> R.string.invalid_credentials
    UiIssue.EMAIL_IN_USE -> R.string.email_in_use
    UiIssue.INVALID_RIDE -> R.string.invalid_ride
    UiIssue.EXPIRED -> R.string.session_expired
    UiIssue.NOT_ALLOWED -> R.string.not_allowed
    UiIssue.NETWORK -> R.string.offline
    UiIssue.SERVER -> R.string.server_error
    UiIssue.GOOGLE_UNAVAILABLE -> R.string.google_unavailable
    UiIssue.GOOGLE_FAILED -> R.string.google_failed
    UiIssue.GOOGLE_LINKED -> R.string.google_linked
    UiIssue.GOOGLE_LINK_REQUIRED -> R.string.google_link_required
}

@StringRes
internal fun Language.label(): Int = when (this) {
    Language.KOREAN -> R.string.language_korean
    Language.ENGLISH -> R.string.language_english
    Language.CHINESE -> R.string.language_chinese
}

@StringRes
internal fun ThemeMode.label(): Int = when (this) {
    ThemeMode.SYSTEM -> R.string.theme_system
    ThemeMode.LIGHT -> R.string.theme_light
    ThemeMode.DARK -> R.string.theme_dark
}
