package com.amo.passenger.ui

import android.widget.LinearLayout
import com.amo.passenger.R
import com.amo.passenger.application.AmoUiState

/** Displays the current passenger's own account. */
internal class AccountPanel(private val widgets: AmoWidgets) {
    fun profile(
        state: AmoUiState,
        refresh: () -> Unit,
        linkGoogle: () -> Unit,
        signOut: () -> Unit
    ): LinearLayout = with(widgets) {
        column().apply {
            add(text(string(R.string.profile), 28, bold = true))
            val account = state.session?.passenger
            if (account != null) {
                add(
                    card().apply {
                        listOfNotNull(
                            R.string.name to string(R.string.passenger_display_name),
                            R.string.email to account.email,
                            account.profileUserId?.let { R.string.member_id to it }
                        ).forEach { (label, value) ->
                            add(text(string(label), 14, palette.muted, true), 8)
                            add(text(value), 4)
                        }
                    },
                    16
                )
            }
            add(
                button(string(R.string.refresh), action = refresh).apply {
                    isEnabled =
                        !state.busy
                },
                12
            )
            add(
                button(string(R.string.google_link), action = linkGoogle).apply {
                    isEnabled =
                        !state.busy
                },
                8
            )
            add(
                button(string(R.string.sign_out), primary = true, action = signOut).apply {
                    isEnabled = !state.busy
                },
                8
            )
        }
    }
}
