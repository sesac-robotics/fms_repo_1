package com.amo.passenger.application

import com.amo.passenger.data.ApiFailure

internal fun httpIssue(error: ApiFailure, state: AmoUiState): UiIssue = when (error.code) {
    "SIGN_IN_AND_LINK_GOOGLE" -> UiIssue.GOOGLE_LINK_REQUIRED
    "GOOGLE_EMAIL_MISMATCH", "GOOGLE_ALREADY_LINKED", "INVALID_GOOGLE_IDENTITY" ->
        UiIssue.GOOGLE_FAILED
    "GOOGLE_LOGIN_NOT_CONFIGURED" -> UiIssue.GOOGLE_UNAVAILABLE
    else -> statusIssue(error.status, state)
}

private fun statusIssue(status: Int, state: AmoUiState): UiIssue = when (status) {
    401 -> if (state.session != null) UiIssue.EXPIRED else UiIssue.INVALID_CREDENTIALS
    403 -> UiIssue.NOT_ALLOWED
    409 -> if (state.screen == Screen.REGISTER) UiIssue.EMAIL_IN_USE else UiIssue.INVALID_RIDE
    400, 422 -> if (state.session != null) UiIssue.INVALID_RIDE else UiIssue.MISSING_FIELDS
    else -> UiIssue.SERVER
}
