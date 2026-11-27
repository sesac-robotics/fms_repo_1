package com.amo.passenger

import com.amo.passenger.data.ContractFailure
import com.amo.passenger.data.readBoundedUtf8
import java.io.ByteArrayInputStream
import org.junit.Assert.assertEquals
import org.junit.Test

class BoundedResponseTest {
    @Test
    fun acceptsUtf8AtTheByteLimit() {
        val json = "\"승객\""
        val body = json.toByteArray()
        assertEquals(json, ByteArrayInputStream(body).readBoundedUtf8(body.size) {})
    }

    @Test(expected = ContractFailure::class)
    fun rejectsMoreThanTheByteLimit() {
        ByteArrayInputStream(ByteArray(10_001)).readBoundedUtf8(10_000) {}
    }
}
