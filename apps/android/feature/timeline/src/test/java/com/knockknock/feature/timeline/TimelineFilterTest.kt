package com.knockknock.feature.timeline

import com.knockknock.core.database.offlineDemoVisit
import com.knockknock.core.database.offlineDeliveryVisit
import com.knockknock.core.database.offlineUnknownVisit
import com.knockknock.core.model.TimelineFilter
import org.junit.Assert.assertEquals
import org.junit.Test

class TimelineFilterTest {
    private val visit = offlineDemoVisit()

    @Test
    fun filtersCoverUnknownFaceUndetectedUnresolvedAndSavedStates() {
        val visits = listOf(visit)

        assertEquals(1, filterVisits(visits, TimelineFilter.UNKNOWN).size)
        assertEquals(1, filterVisits(visits, TimelineFilter.FACE_UNDETECTED).size)
        assertEquals(1, filterVisits(visits, TimelineFilter.UNRESOLVED).size)
        assertEquals(1, filterVisits(visits, TimelineFilter.SAVED).size)
        assertEquals(0, filterVisits(visits, TimelineFilter.FAMILIAR).size)
    }

    @Test
    fun deliveryFilterOnlyReturnsDeliveryScenario() {
        val visits = listOf(visit, offlineDeliveryVisit(), offlineUnknownVisit())

        assertEquals("offline-demo-delivery", filterVisits(visits, TimelineFilter.DELIVERIES).single().id)
    }
}
