package com.knockknock.core.vision
import org.junit.Assert.*
import org.junit.Test

class SimilarityMatcherTest {
    @Test fun unknownWithoutReferencesOrInvalidVectors() {
        assertNull(SimilarityMatcher.suggest(floatArrayOf(1f, 0f), emptyList()))
        assertEquals(-1.0, SimilarityMatcher.cosine(floatArrayOf(Float.NaN), floatArrayOf(1f)), 0.0)
        assertEquals(-1.0, SimilarityMatcher.cosine(floatArrayOf(0f), floatArrayOf(1f)), 0.0)
        assertNull(SimilarityMatcher.suggest(floatArrayOf(1f), listOf(FaceReference("a", floatArrayOf(-1f)))))
    }
    @Test fun ambiguousProfilesStayUnknownButRepeatedReferencesDoNotCompete() {
        val query = floatArrayOf(1f, 0f)
        assertNull(SimilarityMatcher.suggest(query, listOf(FaceReference("a", query), FaceReference("b", query))))
        assertEquals("a", SimilarityMatcher.suggest(query, listOf(FaceReference("a", query), FaceReference("a", query)))?.profileId)
    }
    @Test fun matchingIsScaleIndependentAndRejectsBelowThreshold() {
        assertEquals(1.0, SimilarityMatcher.cosine(floatArrayOf(2f, 0f), floatArrayOf(1f, 0f)), 0.0001)
        assertNull(SimilarityMatcher.suggest(floatArrayOf(1f, 0f), listOf(FaceReference("b", floatArrayOf(0f, 1f)))))
    }
}
