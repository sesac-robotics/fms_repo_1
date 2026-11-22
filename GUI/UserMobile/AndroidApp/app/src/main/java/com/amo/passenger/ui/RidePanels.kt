package com.amo.passenger.ui

import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import com.amo.passenger.R
import com.amo.passenger.application.AmoUiState
import com.amo.passenger.domain.Ride
import com.amo.passenger.domain.RidePhase
import com.amo.passenger.domain.Stop
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException
import java.time.format.FormatStyle

/** Renders the approved map, call inputs, history, and explicit server ride updates. */
internal class RidePanels(private val widgets: AmoWidgets) {
    fun home(
        state: AmoUiState,
        language: String,
        choose: (Boolean, Stop) -> Unit,
        request: () -> Unit,
        refresh: () -> Unit,
        prepare: () -> Unit
    ): LinearLayout = with(widgets) {
        column().apply {
            val current = state.latestRide
            if (current == null) {
                add(text(string(R.string.one_way), 14, palette.accent, true))
                add(text(string(R.string.heading_call), 26, bold = true), 3)
                add(pickupForm(state, choose, request), 12)
            } else {
                add(text(string(R.string.latest_request), 26, bold = true))
                val actions = listOfNotNull(
                    refreshButton(state.busy, refresh),
                    if (current.phase in terminalPhases) {
                        button(string(R.string.request_another), action = prepare).apply {
                            isEnabled = !state.busy
                        }
                    } else {
                        null
                    }
                )
                add(rideCard(current, actions), 10)
            }
            add(map(language), 14)
        }
    }

    fun history(state: AmoUiState, refresh: () -> Unit): LinearLayout = with(widgets) {
        column().apply {
            add(text(string(R.string.history), 28, bold = true))
            add(refreshButton(state.busy, refresh), 12)
            if (state.trips.isEmpty() && !state.busy && state.issue == null) {
                add(text(string(R.string.history_empty), 16, palette.muted), 18)
            }
            state.trips.forEach { add(rideCard(it), 12) }
        }
    }

    private fun refreshButton(busy: Boolean, refresh: () -> Unit) = with(widgets) {
        button(string(R.string.refresh), action = refresh).apply { isEnabled = !busy }
    }

    private fun map(language: String): LinearLayout = with(widgets) {
        card().apply {
            add(text(string(R.string.map_plan), 14, palette.ink, true))
            val mode = if (palette.dark) "dark" else "light"
            val plan =
                image(
                    "amode-map-v02-passenger-$language-$mode.png",
                    string(R.string.map_description),
                    232
                )
            if (plan == null) {
                add(text(string(R.string.map_unavailable), color = palette.error), 10)
            } else {
                (plan.layoutParams as LinearLayout.LayoutParams).topMargin = dp(10)
                addView(plan)
            }
        }
    }

    private fun pickupForm(
        state: AmoUiState,
        choose: (Boolean, Stop) -> Unit,
        request: () -> Unit
    ): LinearLayout = with(widgets) {
        card().apply {
            add(text(string(R.string.pickup), 14, palette.muted, true))
            add(stopButton(R.string.pickup, state.pickup) { choose(true, it) }, 6)
            add(text(string(R.string.destination), 14, palette.muted, true), 12)
            add(stopButton(R.string.destination, state.destination) { choose(false, it) }, 6)
            add(
                button(string(R.string.request_ride), primary = true, action = request).apply {
                    isEnabled = !state.busy
                },
                16
            )
        }
    }

    private fun stopButton(heading: Int, selected: Stop?, choose: (Stop) -> Unit) = with(widgets) {
        val choices = Stop.entries
        button(string(selected?.label() ?: R.string.choose_stop)) {
            dialog()
                .setTitle(heading)
                .setSingleChoiceItems(
                    choices.map { string(it.label()) }.toTypedArray(),
                    selected?.ordinal ?: -1
                ) { dialog, index ->
                    choose(choices[index])
                    dialog.dismiss()
                }
                .setNegativeButton(R.string.close, null)
                .show()
        }.apply { contentDescription = "${string(heading)}. $text" }
    }

    private fun rideCard(ride: Ride, actions: List<View> = emptyList()): LinearLayout =
        with(widgets) {
            card().apply {
                add(
                    text(
                        string(
                            R.string.ride_route,
                            stopName(ride.pickup),
                            stopName(ride.destination)
                        ),
                        19,
                        bold = true
                    )
                )
                add(
                    text(string(ride.phase.label()), 17, palette.accent, true).apply {
                        accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
                    },
                    6
                )
                actions.forEach { add(it, 8) }
                add(field(R.string.ride_id, ride.id), 10)
                ride.vehicleNo?.let { add(field(R.string.vehicle, it), 6) }
                ride.calledAt?.let { add(field(R.string.requested_at, displayTime(it)), 6) }
                ride.receivedAt?.let { add(field(R.string.received_at, displayTime(it)), 6) }
                ride.pickupEtaAt?.let { add(field(R.string.pickup_eta, displayTime(it)), 6) }
                ride.remainingDistanceMeters?.let {
                    add(field(R.string.remaining_distance, string(R.string.distance_m, it)), 6)
                }
                add(text(string(R.string.send_status), 14, palette.muted), 8)
            }
        }

    private fun field(label: Int, value: String): TextView = with(widgets) {
        text("${string(label)} · $value", 14, palette.muted)
    }

    private fun stopName(stop: Stop?): String =
        widgets.string(stop?.label() ?: R.string.unknown_stop)

    private fun displayTime(value: String): String {
        val locale = widgets.context.resources.configuration.locales[0]
        val formatter = DateTimeFormatter.ofLocalizedDateTime(FormatStyle.MEDIUM, FormatStyle.SHORT)
            .withLocale(locale)
            .withZone(ZoneId.systemDefault())
        return try {
            formatter.format(Instant.parse(value))
        } catch (_: DateTimeParseException) {
            value
        }
    }

    private companion object {
        val terminalPhases = setOf(RidePhase.COMPLETE, RidePhase.CANCELLED, RidePhase.FAILED)
    }
}
