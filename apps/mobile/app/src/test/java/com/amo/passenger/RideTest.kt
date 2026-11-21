package com.amo.passenger

import com.amo.passenger.application.PendingRideRequests
import com.amo.passenger.domain.RidePhase
import com.amo.passenger.domain.RideRequest
import com.amo.passenger.domain.Stop
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RideTest {
    @Test
    fun assignmentDoesNotConfirmMotion() {
        assertEquals(RidePhase.ASSIGNED, RidePhase.from("ASSIGNED", null))
    }

    @Test
    fun explicitMovementEvidencePromotesAssignment() {
        assertEquals(RidePhase.ON_TRIP, RidePhase.from("ASSIGNED", "DEPARTURE_CONFIRMED"))
    }

    @Test
    fun terminalRequestOverridesStaleMovement() {
        val phase = RidePhase.from("COMPLETED", "ON_TRIP")
        assertEquals(RidePhase.COMPLETE, phase)
        assertFalse(phase.isOpen)
    }

    @Test
    fun unknownStatusNeverStartsMovement() {
        val phase = RidePhase.from("UNRECOGNIZED", null)
        assertEquals(RidePhase.UNKNOWN, phase)
        assertFalse(phase.isOpen)
    }

    @Test
    fun mapUsesOnlyTheFourOfficialStops() {
        assertEquals(listOf("S1", "S2", "S3", "S4"), Stop.entries.map { it.name })
        assertNull(Stop.parse("S5"))
    }

    @Test
    fun retryReusesKeyEvenAfterAnotherRouteWasSelected() {
        val pending = PendingRideRequests()
        val route = RideRequest(Stop.S1, Stop.S2)
        val first = pending.keyFor(route)
        assertNotEquals(first, pending.keyFor(RideRequest(Stop.S3, Stop.S4)))
        assertEquals(first, pending.keyFor(route))
        pending.forget(route)
        assertNotEquals(first, pending.keyFor(route))
    }

    @Test(expected = IllegalArgumentException::class)
    fun pickupAndDestinationMustDiffer() {
        RideRequest(Stop.S1, Stop.S1)
    }
}
