package com.knockknock.core.database

import com.knockknock.core.model.ConfidenceBand
import com.knockknock.core.model.PersonSummary
import com.knockknock.core.model.ReviewState
import com.knockknock.core.model.VisitStatus
import com.knockknock.core.model.VisitSummary
import java.time.Instant
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

class VisitCache(private val dao: VisitDao) {
    fun observeVisits(): Flow<List<VisitSummary>> = dao.observeAll().map { records ->
        records.map(VisitWithPeople::toDomain)
    }

    fun observeVisit(visitId: String): Flow<VisitSummary?> = dao.observeById(visitId).map {
        it?.toDomain()
    }

    suspend fun replaceAll(visits: List<VisitSummary>) {
        dao.replaceAll(visits.map(VisitSummary::toEntity))
    }

    suspend fun upsert(visit: VisitSummary) {
        dao.upsert(visit.toEntity())
    }

    suspend fun seedOfflineDemo(): VisitSummary {
        val visit = offlineDemoVisit()
        upsert(visit)
        return visit
    }

    suspend fun seedDemoScenario(scenario: String): VisitSummary {
        val visit = when (scenario) {
            "family" -> offlineDemoVisit()
            "delivery" -> offlineDeliveryVisit()
            "unknown" -> offlineUnknownVisit()
            else -> throw IllegalArgumentException("Unknown demo scenario")
        }
        upsert(visit)
        return visit
    }

    suspend fun ensureOfflineDemo(): VisitSummary =
        dao.getById("offline-demo-group-arrival")?.toDomain() ?: seedOfflineDemo()
}

fun VisitSummary.toEntity(): VisitWithPeople = VisitWithPeople(
    visit = VisitEntity(
        id = id,
        eventType = eventType,
        occurredAt = occurredAt.toString(),
        status = status.wireValue,
        source = source,
        personCount = personCount,
        alertTitle = alertTitle,
        alertBody = alertBody,
        version = version,
    ),
    people = people.map { person ->
        PersonEntity(
            id = person.id,
            visitId = id,
            reviewState = person.reviewState.wireValue,
            confidenceBand = person.confidenceBand.wireValue,
            similarity = person.similarity,
            suggestedProfileId = person.suggestedProfileId,
            suggestedName = person.suggestedName,
            confirmedProfileId = person.confirmedProfileId,
            mediaAvailable = person.mediaAvailable,
            saved = person.saved,
            version = person.version,
        )
    },
)

fun VisitWithPeople.toDomain(): VisitSummary = VisitSummary(
    id = visit.id,
    eventType = visit.eventType,
    occurredAt = Instant.parse(visit.occurredAt),
    status = VisitStatus.fromWire(visit.status),
    source = visit.source,
    personCount = visit.personCount,
    alertTitle = visit.alertTitle,
    alertBody = visit.alertBody,
    people = people.sortedBy(PersonEntity::id).map { person ->
        PersonSummary(
            id = person.id,
            reviewState = ReviewState.fromWire(person.reviewState),
            confidenceBand = ConfidenceBand.fromWire(person.confidenceBand),
            similarity = person.similarity,
            suggestedProfileId = person.suggestedProfileId,
            suggestedName = person.suggestedName,
            confirmedProfileId = person.confirmedProfileId,
            mediaAvailable = person.mediaAvailable,
            saved = person.saved,
            version = person.version,
        )
    },
    version = visit.version,
)

fun offlineDemoVisit(): VisitSummary = VisitSummary(
    id = "offline-demo-group-arrival",
    eventType = "button_press",
    occurredAt = Instant.parse("2026-09-29T18:51:56Z"),
    status = VisitStatus.READY,
    source = "offline fixture",
    personCount = 3,
    alertTitle = "Visitor detected",
    alertBody = "3 people detected",
    people = listOf(
        PersonSummary(
            id = "offline-person-1",
            reviewState = ReviewState.UNRESOLVED,
            confidenceBand = ConfidenceBand.HIGH,
            similarity = 0.96,
            suggestedProfileId = "demo-profile-morgan",
            suggestedName = "Possible match: Morgan",
            confirmedProfileId = null,
            mediaAvailable = true,
            saved = false,
            version = 1,
        ),
        PersonSummary(
            id = "offline-person-2",
            reviewState = ReviewState.UNKNOWN,
            confidenceBand = ConfidenceBand.UNKNOWN,
            similarity = 0.0,
            suggestedProfileId = null,
            suggestedName = null,
            confirmedProfileId = null,
            mediaAvailable = true,
            saved = true,
            version = 2,
        ),
        PersonSummary(
            id = "offline-person-3",
            reviewState = ReviewState.FACE_UNDETECTED,
            confidenceBand = ConfidenceBand.UNKNOWN,
            similarity = 0.0,
            suggestedProfileId = null,
            suggestedName = null,
            confirmedProfileId = null,
            mediaAvailable = false,
            saved = false,
            version = 1,
        ),
    ),
    version = 1,
)

fun offlineDeliveryVisit(): VisitSummary = VisitSummary(
    id = "offline-demo-delivery",
    eventType = "delivery_demo",
    occurredAt = Instant.now(),
    status = VisitStatus.READY,
    source = "synthetic demo",
    personCount = 1,
    alertTitle = "Delivery at the door",
    alertBody = "1 person detected; face not visible",
    people = listOf(
        PersonSummary("delivery-person-1", ReviewState.UNRESOLVED, ConfidenceBand.UNKNOWN,
            0.0, null, null, null, true, false, 1),
    ),
    version = 1,
)

fun offlineUnknownVisit(): VisitSummary = VisitSummary(
    id = "offline-demo-unknown",
    eventType = "motion_detected",
    occurredAt = Instant.now(),
    status = VisitStatus.READY,
    source = "synthetic demo",
    personCount = 1,
    alertTitle = "Visitor detected",
    alertBody = "1 person needs review",
    people = listOf(
        PersonSummary("unknown-person-1", ReviewState.UNRESOLVED, ConfidenceBand.UNKNOWN,
            0.0, null, null, null, true, false, 1),
    ),
    version = 1,
)
