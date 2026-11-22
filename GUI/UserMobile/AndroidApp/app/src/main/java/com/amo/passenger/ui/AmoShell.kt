package com.amo.passenger.ui

import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.ScrollView
import androidx.core.content.ContextCompat
import com.amo.passenger.R
import com.amo.passenger.application.AmoUiState
import com.amo.passenger.application.Screen
import com.amo.passenger.application.UiIssue

/** Keeps the app header, status announcements, and bottom navigation stable. */
internal class AmoShell(
    private val widgets: AmoWidgets,
    private val openSettings: () -> Unit,
    private val closeSettings: () -> Unit,
    private val navigate: (Screen) -> Unit
) {
    private val settings = widgets.button(widgets.string(R.string.settings), action = openSettings)
    private val back = widgets.button(widgets.string(R.string.back), action = closeSettings)
    private val content = widgets.column()
    private val status = widgets.text("", 14).apply {
        accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
        visibility = View.GONE
    }
    private val scroll: ScrollView = widgets.scroll(content)
    private val nav = widgets.row()

    val root = with(widgets) {
        column().apply {
            add(header())
            add(status.apply { setPadding(dp(18), dp(5), dp(18), dp(5)) })
            content.setPadding(dp(18), dp(18), dp(18), dp(20))
            addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
            add(nav.apply { setPadding(dp(7), dp(6), dp(7), dp(7)) })
        }
    }

    fun show(view: View, screenChanged: Boolean) {
        val scrollTop = scroll.scrollY
        content.removeAllViews()
        with(widgets) { content.add(view) }
        scroll.post { scroll.scrollTo(0, if (screenChanged) 0 else scrollTop) }
    }

    fun update(state: AmoUiState) = with(widgets) {
        val onSettings = state.screen == Screen.SETTINGS
        val signedIn = state.session != null
        settings.visibility = if (onSettings) View.GONE else View.VISIBLE
        back.visibility = if (onSettings) View.VISIBLE else View.GONE
        settings.isEnabled = !state.busy
        val statusId = when {
            state.screen in authScreens || onSettings -> null
            state.issue != null -> state.issue.label()
            state.busy -> R.string.loading
            state.online == false -> R.string.offline
            else -> null
        }
        status.setTextColor(
            when (state.issue) {
                UiIssue.GOOGLE_LINKED -> palette.accent
                null -> palette.muted
                else -> palette.error
            }
        )
        status.text = statusId?.let { string(it) }
        status.visibility = if (statusId == null) View.GONE else View.VISIBLE
        nav.visibility = if (signedIn && !onSettings) View.VISIBLE else View.GONE
        if (signedIn && !onSettings) updateNav(state)
    }

    private fun header(): LinearLayout = with(widgets) {
        row().apply {
            setPadding(dp(12), dp(7), dp(12), dp(7))
            setBackgroundColor(palette.header)
            val mode = if (palette.dark) "dark" else "light"
            val brand = image("amo-logo-$mode.png", string(R.string.app_name), 43, 140)
            if (brand != null) {
                brand.background = rounded(palette.badge, 12)
                brand.setPadding(dp(7), dp(4), dp(7), dp(4))
                addView(brand)
            } else {
                addView(text(string(R.string.app_name), 22, bold = true))
            }
            addView(View(context), LinearLayout.LayoutParams(0, 1, 1f))
            addView(settings)
            addView(back)
        }
    }

    private fun updateNav(state: AmoUiState) = with(widgets) {
        nav.removeAllViews()
        nav.setBackgroundColor(palette.header)
        for ((tab, icon) in tabIcons) {
            val selected = state.screen == tab
            val drawable = ContextCompat.getDrawable(context, icon)?.mutate()?.apply {
                setTint(if (selected) palette.actionText else palette.ink)
            }
            val item = button(string(tab.label()), primary = selected) { navigate(tab) }.apply {
                isSelected = selected
                isEnabled = !state.busy
                gravity = Gravity.CENTER
                textSize = 13f
                setPadding(dp(4), dp(4), dp(4), dp(4))
                compoundDrawablePadding = dp(2)
                setCompoundDrawablesRelativeWithIntrinsicBounds(null, drawable, null, null)
            }
            nav.addView(
                item,
                LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply {
                    marginStart = dp(3)
                    marginEnd = dp(3)
                }
            )
        }
    }

    private companion object {
        val authScreens = setOf(Screen.SIGN_IN, Screen.REGISTER)
        val tabIcons = listOf(
            Screen.HOME to R.drawable.nav_ride,
            Screen.HISTORY to R.drawable.nav_history,
            Screen.PROFILE to R.drawable.nav_profile
        )
    }
}
