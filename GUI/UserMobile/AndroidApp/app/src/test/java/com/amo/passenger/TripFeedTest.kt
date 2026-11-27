package com.amo.passenger

import com.amo.passenger.application.AmoUiState
import com.amo.passenger.application.Screen
import com.amo.passenger.application.TripFeed
import com.amo.passenger.application.UiIssue
import com.amo.passenger.data.ApiFailure
import com.amo.passenger.domain.Passenger
import com.amo.passenger.domain.Session
import java.time.Instant
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Test

class TripFeedTest {
    private val now = Instant.parse("2026-11-27T00:00:00Z")
    private val passenger = Passenger("1", "Fixture", "fixture@test.invalid")
    private val session = Session("fixture", now.plusSeconds(60), passenger)

    @Test
    fun discardsAResponseAfterSignOut() = runBlocking {
        val state = MutableStateFlow(AmoUiState(screen = Screen.HISTORY, session = session))
        val signedOut = AmoUiState()
        val feed = TripFeed(state, {
            state.value = signedOut
            emptyList()
        }, { _, _ -> null })

        feed.poll(now)

        assertEquals(signedOut, state.value)
    }

    @Test
    fun expiresTheCurrentSessionOnUnauthorizedResponse() = runBlocking {
        val state = MutableStateFlow(AmoUiState(screen = Screen.HISTORY, session = session))
        val feed = TripFeed(state, { throw ApiFailure(401) }, { _, _ -> null })

        feed.poll(now)

        assertEquals(UiIssue.EXPIRED, state.value.issue)
        assertEquals(null, state.value.session)
    }
}
