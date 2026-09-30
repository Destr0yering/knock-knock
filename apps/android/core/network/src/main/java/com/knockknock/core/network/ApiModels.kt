package com.knockknock.core.network

import com.knockknock.core.model.ConfidenceBand
import com.knockknock.core.model.PersonSummary
import com.knockknock.core.model.ReviewState
import com.knockknock.core.model.VisitStatus
import com.knockknock.core.model.VisitSummary
import java.time.Instant

data class FixtureRequestDto(val fixture: String = "group-arrival")

data class AlertDto(
    val title: String,
    val body: String,
    val includesIdentity: Boolean,
)

data class PersonDto(
    val id: String,
    val reviewState: String,
    val confidenceBand: String,
    val similarity: Double,
    val suggestedProfileId: String?,
    val suggestedName: String?,
    val confirmedProfileId: String?,
    val mediaAvailable: Boolean,
    val saved: Boolean,
    val version: Int,
) {
    fun toDomain(): PersonSummary = PersonSummary(
        id = id,
        reviewState = ReviewState.fromWire(reviewState),
        confidenceBand = ConfidenceBand.fromWire(confidenceBand),
        similarity = similarity,
        suggestedProfileId = suggestedProfileId,
        suggestedName = suggestedName,
        confirmedProfileId = confirmedProfileId,
        mediaAvailable = mediaAvailable,
        saved = saved,
        version = version,
    )
}

data class VisitDto(
    val id: String,
    val eventType: String,
    val occurredAt: String,
    val status: String,
    val source: String,
    val personCount: Int,
    val alert: AlertDto,
    val people: List<PersonDto>,
    val version: Int,
) {
    fun toDomain(): VisitSummary = VisitSummary(
        id = id,
        eventType = eventType,
        occurredAt = Instant.parse(occurredAt),
        status = VisitStatus.fromWire(status),
        source = source,
        personCount = personCount,
        alertTitle = alert.title,
        alertBody = alert.body,
        people = people.map(PersonDto::toDomain),
        version = version,
    )
}
