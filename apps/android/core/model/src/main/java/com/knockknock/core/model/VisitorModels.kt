package com.knockknock.core.model

import java.time.Instant

enum class ReviewState(val wireValue: String) {
    UNRESOLVED("unresolved"),
    UNKNOWN("unknown"),
    FACE_UNDETECTED("face_undetected"),
    PROPOSED("proposed"),
    CONFIRMED("confirmed"),
    CORRECTED("corrected");

    companion object {
        fun fromWire(value: String): ReviewState = entries.firstOrNull { it.wireValue == value }
            ?: UNRESOLVED
    }
}

enum class ConfidenceBand(val wireValue: String) {
    HIGH("high"),
    REVIEW("review"),
    UNKNOWN("unknown");

    companion object {
        fun fromWire(value: String): ConfidenceBand = entries.firstOrNull { it.wireValue == value }
            ?: UNKNOWN
    }
}

enum class VisitStatus(val wireValue: String) {
    PROCESSING("processing"),
    READY("ready"),
    FAILED("failed");

    companion object {
        fun fromWire(value: String): VisitStatus = entries.firstOrNull { it.wireValue == value }
            ?: PROCESSING
    }
}

data class PersonSummary(
    val id: String,
    val reviewState: ReviewState,
    val confidenceBand: ConfidenceBand,
    val similarity: Double,
    val suggestedProfileId: String?,
    val suggestedName: String?,
    val confirmedProfileId: String?,
    val mediaAvailable: Boolean,
    val saved: Boolean,
    val version: Int,
)

data class VisitSummary(
    val id: String,
    val eventType: String,
    val occurredAt: Instant,
    val status: VisitStatus,
    val source: String,
    val personCount: Int,
    val alertTitle: String,
    val alertBody: String,
    val people: List<PersonSummary>,
    val version: Int,
) {
    val labels: List<String>
        get() = people.mapNotNull { person ->
            person.suggestedName ?: person.confirmedProfileId?.let { "Familiar" }
        }.distinct()

    val hasExpiredPhoto: Boolean
        get() = people.any { !it.mediaAvailable }

    val hasSavedPhoto: Boolean
        get() = people.any { it.saved }
}

enum class TimelineFilter(val label: String) {
    ALL("All"),
    FAMILIAR("Familiar"),
    UNKNOWN("Unknown"),
    FACE_UNDETECTED("Face undetected"),
    UNRESOLVED("Needs review"),
    SAVED("Saved");
}

fun VisitSummary.matches(filter: TimelineFilter): Boolean = when (filter) {
    TimelineFilter.ALL -> true
    TimelineFilter.FAMILIAR -> people.any {
        it.reviewState == ReviewState.CONFIRMED || it.reviewState == ReviewState.CORRECTED
    }
    TimelineFilter.UNKNOWN -> people.any { it.reviewState == ReviewState.UNKNOWN }
    TimelineFilter.FACE_UNDETECTED -> people.any { it.reviewState == ReviewState.FACE_UNDETECTED }
    TimelineFilter.UNRESOLVED -> people.any {
        it.reviewState == ReviewState.UNRESOLVED || it.reviewState == ReviewState.PROPOSED
    }
    TimelineFilter.SAVED -> hasSavedPhoto
}
