package com.knockknock.core.database

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class EntityMappingTest {
    @Test
    fun offlineFixtureRoundTripsThroughRoomEntities() {
        val fixture = offlineDemoVisit()
        val roundTrip = fixture.toEntity().toDomain()

        assertEquals(fixture, roundTrip)
        assertTrue(roundTrip.hasExpiredPhoto)
        assertTrue(roundTrip.hasSavedPhoto)
    }
}
