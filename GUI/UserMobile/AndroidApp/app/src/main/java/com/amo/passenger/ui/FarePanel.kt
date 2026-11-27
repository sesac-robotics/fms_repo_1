package com.amo.passenger.ui

import android.app.AlertDialog
import android.widget.LinearLayout
import com.amo.passenger.R
import com.amo.passenger.application.FareAction
import com.amo.passenger.domain.FareTerms
import com.amo.passenger.domain.Ride
import com.amo.passenger.domain.RideFares
import com.amo.passenger.domain.RidePhase
import com.amo.passenger.domain.Stop

/** Displays mock amounts and keeps proposed destinations distinct from applied destinations. */
internal class FarePanel(private val widgets: AmoWidgets) {
    fun render(
        state: RideFares,
        ride: Ride,
        busy: Boolean,
        dispatch: (FareAction) -> Unit
    ): LinearLayout = with(widgets) {
        card().apply {
            add(text(string(R.string.demo_fare), 18, bold = true))
            val initial = state.initial
            initial.quote?.let { add(text(terms(it), 15), 6) }
            add(text(value(R.string.mock_prepayment_state, status(initial.paymentStatus)), 14), 6)
            val canPay = ride.phase in setOf(RidePhase.RECEIVED, RidePhase.WAITING)
            if (canPay && initial.quote == null) {
                add(action(R.string.mock_get_quote, busy) { dispatch(FareAction.Quote) }, 8)
            }
            if (canPay && initial.quote != null && initial.paymentStatus in payable) {
                add(action(R.string.mock_prepay, busy) { dispatch(FareAction.Prepay) }, 8)
            }
            val route = state.route
            if (route != null) {
                add(
                    text(value(R.string.proposed_destination, route.proposedDestination.name), 14),
                    10
                )
                add(
                    text(
                        value(R.string.effective_destination, route.effectiveDestination.name),
                        14
                    ),
                    4
                )
                add(text(value(R.string.mock_route_state, status(route.phase)), 14), 4)
                add(text(terms(route.quote), 14), 4)
                val delta = value(R.string.mock_amount, route.quote.currencyCode, route.deltaMinor)
                add(
                    text(
                        value(R.string.mock_difference_state, delta, status(route.paymentStatus)),
                        14
                    ),
                    4
                )
                if (route.phase == "PROPOSED" && route.paymentStatus in payable) {
                    add(
                        action(R.string.mock_accept_change, busy) {
                            dispatch(FareAction.AcceptChange)
                        },
                        8
                    )
                }
            }
            if (ride.phase in changeable && (route == null || route.phase == "APPLIED")) {
                add(
                    action(R.string.mock_propose_change, busy) {
                        choose(
                            ride.pickup,
                            route?.effectiveDestination ?: ride.destination,
                            dispatch
                        )
                    },
                    8
                )
            }
            initial.receipt?.let {
                val amount = value(R.string.mock_amount, it.currencyCode, it.amountMinor)
                add(text(value(R.string.mock_receipt, amount, it.reference), 14), 10)
            }
        }
    }

    private fun terms(quote: FareTerms): String = value(
        R.string.mock_estimate,
        quote.distanceMeters,
        quote.durationSeconds,
        value(R.string.mock_amount, quote.currencyCode, quote.amountMinor)
    )

    private fun action(label: Int, busy: Boolean, invoke: () -> Unit) =
        widgets.button(widgets.string(label), action = invoke).apply { isEnabled = !busy }

    private fun choose(pickup: Stop?, effective: Stop?, dispatch: (FareAction) -> Unit) {
        val choices = Stop.entries.filter { it != pickup && it != effective }
        AlertDialog.Builder(widgets.context)
            .setTitle(R.string.mock_propose_change)
            .setItems(choices.map { it.name }.toTypedArray()) { _, selected ->
                dispatch(FareAction.Propose(choices[selected]))
            }
            .show()
    }

    private fun value(id: Int, vararg args: Any): String = widgets.context.getString(id, *args)

    private fun status(code: String): String = widgets.string(
        when (code) {
            "UNQUOTED", "QUOTED" -> R.string.mock_quoted
            "PROPOSED" -> R.string.mock_proposed
            "NOT_REQUIRED" -> R.string.mock_not_required
            "ESTIMATE_MISSING" -> R.string.mock_estimate_missing
            "METHOD_MISSING" -> R.string.mock_method_missing
            "QUOTE_EXPIRED" -> R.string.mock_quote_expired
            "SUCCEEDED" -> R.string.mock_succeeded
            "FAILED" -> R.string.mock_failed
            "ISSUED" -> R.string.mock_issued
            "ACKNOWLEDGED" -> R.string.mock_acknowledged
            "APPLIED" -> R.string.mock_applied
            else -> R.string.r_unknown
        }
    )

    private companion object {
        val payable = setOf("QUOTED", "FAILED", "METHOD_MISSING")
        val changeable = setOf(RidePhase.ON_TRIP, RidePhase.STOPPED_WAIT)
    }
}
