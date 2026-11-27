package com.amo.passenger.ui

import android.text.InputType
import android.view.View
import android.widget.EditText
import android.widget.TextView
import com.amo.passenger.R
import com.amo.passenger.application.AmoUiState

/** Keeps the form controls alive while request status changes so retrying preserves input. */
internal class AuthForm(
    private val widgets: AmoWidgets,
    register: Boolean,
    signIn: (String, String) -> Unit,
    createAccount: (String, String, String) -> Unit,
    google: () -> Unit,
    switch: () -> Unit
) {
    private val name = field(
        R.string.name,
        InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_WORDS
    )
    private val email = field(
        R.string.email,
        InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS
    )
    private val password = field(
        R.string.password,
        InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
    )
    private val message = widgets.text("", 15, widgets.palette.error)
    private val status = widgets.text("", 14, widgets.palette.muted)
    private val submit = widgets.button(
        widgets.string(if (register) R.string.sign_up else R.string.sign_in),
        primary = true
    ) {
        val address = email.text.toString()
        val secret = password.text.toString()
        if (register) {
            createAccount(
                name.text.toString(),
                address,
                secret
            )
        } else {
            signIn(address, secret)
        }
    }
    private val googleButton = widgets.button(
        widgets.string(R.string.google_sign_in),
        action = google
    )
    private val switchButton = widgets.button(
        widgets.string(if (register) R.string.have_account else R.string.sign_up),
        action = switch
    )

    val view = with(widgets) {
        card().apply {
            add(
                text(
                    string(if (register) R.string.create_heading else R.string.auth_heading),
                    26,
                    bold = true
                )
            )
            add(text(string(R.string.auth_intro), 15, palette.muted), 8)
            add(message, 10)
            add(status, 6)
            if (register) add(name, 12)
            add(email, 12)
            add(password, 12)
            add(submit, 18)
            if (!register) add(googleButton, 8)
            add(switchButton, 8)
        }
    }

    fun update(state: AmoUiState, requestingGoogle: Boolean) {
        val busy = state.busy || requestingGoogle
        submit.isEnabled = !busy
        googleButton.isEnabled = !busy
        switchButton.isEnabled = !busy
        show(message, state.issue?.let { widgets.string(it.label()) })
        show(
            status,
            when {
                busy -> widgets.string(R.string.loading)
                state.online == false && state.issue == null -> widgets.string(R.string.offline)
                else -> null
            }
        )
    }

    private fun show(target: TextView, value: String?) {
        target.text = value
        target.visibility = if (value == null) View.GONE else View.VISIBLE
    }

    private fun field(label: Int, kind: Int): EditText = EditText(widgets.context).apply {
        hint = widgets.string(label)
        inputType = kind
        setSingleLine()
        setTextColor(widgets.palette.ink)
        setHintTextColor(widgets.palette.muted)
        textSize = 16f
        minHeight = widgets.dp(50)
        setPadding(widgets.dp(14), widgets.dp(8), widgets.dp(14), widgets.dp(8))
        background = widgets.rounded(widgets.palette.background, 12, widgets.palette.outline)
    }
}
