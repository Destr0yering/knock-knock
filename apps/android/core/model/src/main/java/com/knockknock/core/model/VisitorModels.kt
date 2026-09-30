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

object ProfilePermissionPolicy {
    fun canDecide(role: HouseholdRole): Boolean = role == HouseholdRole.OWNER
}

enum class ProposalStatus { PENDING, APPROVED, REJECTED }

data class FamiliarProfile(
    val id: String,
    val name: String,
    val sampleCount: Int,
    val updatedAt: Instant,
)

data class ProfileProposal(
    val id: String,
    val visitId: String,
    val personId: String,
    val proposedName: String,
    val proposer: String,
    val status: ProposalStatus,
    val createdAt: Instant,
    val decidedBy: String? = null,
    val decidedAt: Instant? = null,
)

data class AuditEntry(
    val id: String,
    val profileId: String?,
    val personId: String,
    val actor: String,
    val action: String,
    val detail: String,
    val occurredAt: Instant,
)

data class VisitorAlert(
    val title: String,
    val body: String,
    val includesIdentity: Boolean,
)

object VisitorTrustPolicy {
    fun alert(
        peopleCount: Int,
        learningDay: Int,
        candidateName: String?,
        confidenceBand: ConfidenceBand,
        disputed: Boolean = false,
    ): VisitorAlert {
        val generic = VisitorAlert(
            title = "Visitor detected",
            body = "$peopleCount ${if (peopleCount == 1) "person" else "people"} detected",
            includesIdentity = false,
        )
        if (learningDay <= 30 || candidateName == null ||
            confidenceBand != ConfidenceBand.HIGH || disputed
        ) return generic
        return VisitorAlert(
            title = "Possible match: $candidateName",
            body = generic.body,
            includesIdentity = true,
        )
    }
}

object VisitDeepLink {
    private const val PREFIX = "knockknock://visits/"

    fun create(visitId: String): String = "$PREFIX$visitId"

    fun parse(value: String?): String? = value
        ?.takeIf { it.startsWith(PREFIX) }
        ?.removePrefix(PREFIX)
        ?.takeIf { it.isNotBlank() && !it.contains('/') }
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
