package com.knockknock.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class TrustPolicyTest {
    @Test
    fun learningPeriodAlwaysUsesGenericAlert() {
        val alert = VisitorTrustPolicy.alert(3, 1, "Morgan", ConfidenceBand.HIGH)
        assertEquals("3 people detected", alert.body)
        assertFalse(alert.includesIdentity)
    }

    @Test
    fun postLearningHighConfidenceIsStillTentative() {
        val alert = VisitorTrustPolicy.alert(1, 31, "Morgan", ConfidenceBand.HIGH)
        assertEquals("Possible match: Morgan", alert.title)
        assertTrue(alert.includesIdentity)
    }

    @Test
    fun onlyOwnerCanDecideProfileProposal() {
        assertTrue(ProfilePermissionPolicy.canDecide(HouseholdRole.OWNER))
        assertFalse(ProfilePermissionPolicy.canDecide(HouseholdRole.MEMBER))
    }

    @Test
    fun deepLinksRejectNestedOrUnrelatedRoutes() {
        assertEquals("visit-1", VisitDeepLink.parse(VisitDeepLink.create("visit-1")))
        assertNull(VisitDeepLink.parse("https://example.com/visits/visit-1"))
        assertNull(VisitDeepLink.parse("knockknock://visits/visit-1/extra"))
    }
}
