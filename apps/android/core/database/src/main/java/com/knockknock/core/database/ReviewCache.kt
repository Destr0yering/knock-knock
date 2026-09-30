package com.knockknock.core.database

import com.knockknock.core.model.AuditEntry
import com.knockknock.core.model.FamiliarProfile
import com.knockknock.core.model.ProfileProposal
import com.knockknock.core.model.ProposalStatus
import com.knockknock.core.model.ReviewState
import java.time.Instant
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

class ReviewCache(
    private val visitDao: VisitDao,
    private val reviewDao: ReviewDao,
) {
    val profiles: Flow<List<FamiliarProfile>> = reviewDao.observeProfiles().map { rows ->
        rows.map { FamiliarProfile(it.id, it.name, it.sampleCount, Instant.parse(it.updatedAt)) }
    }

    val proposals: Flow<List<ProfileProposal>> = reviewDao.observeProposals().map { rows ->
        rows.map { row ->
            ProfileProposal(
                id = row.id,
                visitId = row.visitId,
                personId = row.personId,
                proposedName = row.proposedName,
                proposer = row.proposer,
                status = ProposalStatus.valueOf(row.status),
                createdAt = Instant.parse(row.createdAt),
                decidedBy = row.decidedBy,
                decidedAt = row.decidedAt?.let(Instant::parse),
            )
        }
    }

    val audit: Flow<List<AuditEntry>> = reviewDao.observeAudit().map { rows ->
        rows.map { row ->
            AuditEntry(
                id = row.id,
                profileId = row.profileId,
                personId = row.personId,
                actor = row.actor,
                action = row.action,
                detail = row.detail,
                occurredAt = Instant.parse(row.occurredAt),
            )
        }
    }

    suspend fun seedProfile(profile: FamiliarProfile) = reviewDao.upsertProfile(profile.toEntity())

    suspend fun upsertProfile(profile: FamiliarProfile) = reviewDao.upsertProfile(profile.toEntity())

    suspend fun upsertProposal(proposal: ProfileProposal) = reviewDao.upsertProposal(
        ProposalEntity(
            id = proposal.id,
            visitId = proposal.visitId,
            personId = proposal.personId,
            proposedName = proposal.proposedName,
            proposer = proposal.proposer,
            status = proposal.status.name,
            createdAt = proposal.createdAt.toString(),
            decidedBy = proposal.decidedBy,
            decidedAt = proposal.decidedAt?.toString(),
        ),
    )

    suspend fun appendAudit(entry: AuditEntry) = reviewDao.appendAudit(
        AuditEntity(
            id = entry.id,
            profileId = entry.profileId,
            personId = entry.personId,
            actor = entry.actor,
            action = entry.action,
            detail = entry.detail,
            occurredAt = entry.occurredAt.toString(),
        ),
    )

    suspend fun updatePerson(
        personId: String,
        state: ReviewState? = null,
        confirmedProfileId: String? = null,
        saved: Boolean? = null,
    ) {
        val current = visitDao.getPerson(personId) ?: return
        visitDao.upsertPerson(
            current.copy(
                reviewState = state?.wireValue ?: current.reviewState,
                confirmedProfileId = confirmedProfileId ?: current.confirmedProfileId,
                saved = saved ?: current.saved,
                version = current.version + 1,
            ),
        )
    }
}

private fun FamiliarProfile.toEntity() = ProfileEntity(
    id = id,
    name = name,
    sampleCount = sampleCount,
    updatedAt = updatedAt.toString(),
)
