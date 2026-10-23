package com.knockknock.core.vision

import kotlin.math.sqrt

data class FaceReference(val profileId: String, val embedding: FloatArray)
data class MatchSuggestion(val profileId: String, val similarity: Double)

/** Suggestions always need owner confirmation; scores are not probabilities. */
object SimilarityMatcher {
    fun cosine(a: FloatArray, b: FloatArray): Double {
        if (a.size != b.size || a.isEmpty() || a.any { !it.isFinite() } || b.any { !it.isFinite() }) return -1.0
        var dot = 0.0; var aa = 0.0; var bb = 0.0
        for (i in a.indices) { dot += a[i].toDouble() * b[i]; aa += a[i].toDouble() * a[i]; bb += b[i].toDouble() * b[i] }
        if (aa == 0.0 || bb == 0.0) return -1.0
        return (dot / sqrt(aa * bb)).coerceIn(-1.0, 1.0)
    }

    fun suggest(embedding: FloatArray, references: List<FaceReference>, threshold: Double = 0.55,
                minimumMargin: Double = 0.08): MatchSuggestion? {
        require(threshold in 0.0..1.0 && minimumMargin in 0.0..1.0)
        val ranked = references.groupBy { it.profileId }.map { (id, samples) ->
            MatchSuggestion(id, samples.maxOf { cosine(embedding, it.embedding) })
        }.sortedByDescending { it.similarity }
        val best = ranked.firstOrNull() ?: return null
        if (best.similarity < threshold) return null
        if (ranked.size > 1 && best.similarity - ranked[1].similarity < minimumMargin) return null
        return best
    }
}
