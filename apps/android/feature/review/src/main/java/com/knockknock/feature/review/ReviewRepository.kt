package com.knockknock.feature.review

import com.knockknock.core.database.ReviewCache
import com.knockknock.core.database.VisitCache
import com.knockknock.core.model.AuditEntry
import com.knockknock.core.model.FamiliarProfile
import com.knockknock.core.model.HouseholdRole
import com.knockknock.core.model.ProfileProposal
import com.knockknock.core.model.ProfilePermissionPolicy
import com.knockknock.core.model.ProposalStatus
import com.knockknock.core.model.ReviewState
import com.knockknock.core.model.VisitSummary
import java.time.Clock
import java.time.Instant
import java.util.UUID
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class ReviewRepository(
    private val visits: VisitCache,
    private val reviews: ReviewCache,
    private val clock: Clock = Clock.systemUTC(),
) {
    private val mutableRole = MutableStateFlow(HouseholdRole.MEMBER)
    val role: StateFlow<HouseholdRole> = mutableRole
    val profiles: Flow<List<FamiliarProfile>> = reviews.profiles
    val proposals: Flow<List<ProfileProposal>> = reviews.proposals
    val audit: Flow<List<AuditEntry>> = reviews.audit

    fun visit(visitId: String): Flow<VisitSummary?> = visits.observeVisit(visitId)

    suspend fun prepareDemo(visitId: String) {
        if (visitId == "offline-demo-group-arrival") visits.ensureOfflineDemo()
        reviews.seedProfile(
            FamiliarProfile(
                id = "demo-profile-morgan",
                name = "Morgan",
                sampleCount = 4,
                updatedAt = Instant.parse("2026-09-25T15:00:00Z"),
            ),
        )
    }

    fun setRole(role: HouseholdRole) {
        mutableRole.value = role
    }

    suspend fun markUnknown(personId: String) {
        reviews.updatePerson(personId, state = ReviewState.UNKNOWN)
        append(personId, "VISITOR_MARKED_UNKNOWN", "Visitor kept separate from familiar profiles")
    }

    suspend fun markFaceUndetected(personId: String) {
        reviews.updatePerson(personId, state = ReviewState.FACE_UNDETECTED)
        append(personId, "FACE_UNDETECTED_CONFIRMED", "No usable face was present in this visit")
    }

    suspend fun confirmProfile(personId: String, profile: FamiliarProfile) {
        reviews.updatePerson(
            personId = personId,
            state = ReviewState.CONFIRMED,
            confirmedProfileId = profile.id,
        )
        append(
            personId = personId,
            action = "VISIT_IDENTITY_CONFIRMED",
            detail = "Linked this visit to ${profile.name}",
            profileId = profile.id,
        )
    }

    suspend fun savePhoto(personId: String) {
        reviews.updatePerson(personId, saved = true)
        append(personId, "PHOTO_SAVED", "Photo retained beyond the 30-day review window")
    }

    suspend fun proposeProfile(visitId: String, personId: String, name: String): Boolean {
        val cleanName = name.trim()
        if (cleanName.isBlank()) return false
        val now = clock.instant()
        val proposal = ProfileProposal(
            id = UUID.randomUUID().toString(),
            visitId = visitId,
            personId = personId,
            proposedName = cleanName,
            proposer = actorName(),
            status = ProposalStatus.PENDING,
            createdAt = now,
        )
        reviews.upsertProposal(proposal)
        reviews.updatePerson(personId, state = ReviewState.PROPOSED)
        append(personId, "PROFILE_CHANGE_PROPOSED", "Proposed familiar profile: $cleanName")
        return true
    }

    suspend fun decide(proposal: ProfileProposal, approve: Boolean): Boolean {
        if (!ProfilePermissionPolicy.canDecide(mutableRole.value) || proposal.status != ProposalStatus.PENDING) {
            return false
        }
        val now = clock.instant()
        val profileId = "profile-${proposal.personId}"
        reviews.upsertProposal(
            proposal.copy(
                status = if (approve) ProposalStatus.APPROVED else ProposalStatus.REJECTED,
                decidedBy = actorName(),
                decidedAt = now,
            ),
        )
        if (approve) {
            reviews.upsertProfile(
                FamiliarProfile(profileId, proposal.proposedName, sampleCount = 1, updatedAt = now),
            )
            reviews.updatePerson(
                personId = proposal.personId,
                state = ReviewState.CONFIRMED,
                confirmedProfileId = profileId,
            )
        } else {
            reviews.updatePerson(proposal.personId, state = ReviewState.UNKNOWN)
        }
        append(
            personId = proposal.personId,
            action = if (approve) "PROFILE_CHANGE_APPROVED" else "PROFILE_CHANGE_REJECTED",
            detail = "${proposal.proposedName} · proposed by ${proposal.proposer}",
            profileId = profileId.takeIf { approve },
        )
        return true
    }

    private suspend fun append(
        personId: String,
        action: String,
        detail: String,
        profileId: String? = null,
    ) {
        reviews.appendAudit(
            AuditEntry(
                id = UUID.randomUUID().toString(),
                profileId = profileId,
                personId = personId,
                actor = actorName(),
                action = action,
                detail = detail,
                occurredAt = clock.instant(),
            ),
        )
    }

    private fun actorName(): String = when (mutableRole.value) {
        HouseholdRole.OWNER -> "Thomas · Ring owner"
        HouseholdRole.MEMBER -> "Household member"
    }
}
