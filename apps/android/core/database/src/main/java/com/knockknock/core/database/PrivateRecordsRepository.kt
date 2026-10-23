package com.knockknock.core.database

import androidx.room.withTransaction
import com.knockknock.core.privacy.EncryptedFileVault
import com.knockknock.core.privacy.OwnerUnlock
import java.nio.ByteBuffer
import java.security.MessageDigest
import java.time.Instant
import java.time.temporal.ChronoUnit
import java.util.UUID
import kotlinx.coroutines.flow.first
import org.json.JSONArray
import org.json.JSONObject

data class PrivateFaceInput(val jpeg: ByteArray, val embedding: FloatArray, val confidence: Double)
data class PrivateReference(val profileId: String, val embedding: FloatArray)
data class RetentionSettings(val photoDays: Int = 30, val logDays: Int = 365) {
    init { require(photoDays in 1..365 && logDays in 1..3650) }
}

class PrivateRecordsRepository(
    private val db: KnockKnockDatabase,
    private val vault: EncryptedFileVault,
    private val unlock: OwnerUnlock,
) {
    private val dao get() = db.privateDao()
    fun retentionSettings(): RetentionSettings {
        unlock.requireUnlocked()
        if (!vault.exists("internal/retention-settings-v1")) return RetentionSettings()
        val encoded = ByteBuffer.wrap(vault.get("internal/retention-settings-v1"))
        return RetentionSettings(encoded.int, encoded.int)
    }

    suspend fun updateRetention(settings: RetentionSettings) {
        unlock.requireUnlocked()
        vault.put("internal/retention-settings-v1", ByteBuffer.allocate(8).putInt(settings.photoDays).putInt(settings.logDays).array())
        db.withTransaction {
            dao.allMedia().filter { !it.saved }.forEach {
                dao.updateMediaExpiry(it.id, Instant.parse(it.capturedAt).plus(settings.photoDays.toLong(), ChronoUnit.DAYS).toString())
            }
            audit("", null, "retention_changed", "Owner set photos=${settings.photoDays} days; logs=${settings.logDays} days")
        }
    }
    fun observeVisits() = db.visitDao().observeAll()
    fun observeProfiles() = db.reviewDao().observeProfiles()
    fun observeAudit() = db.reviewDao().observeAudit()
    suspend fun recordAccess() {
        unlock.requireUnlocked()
        audit("", null, "private_records_opened", "Device credential accepted; owner opened private records")
    }
    suspend fun personIdsForVisit(visitId: String): List<String> {
        unlock.requireUnlocked()
        return dao.orderedPersonIds(visitId)
    }

    suspend fun suggestIdentity(personId: String, profileId: String, similarity: Double) {
        unlock.requireUnlocked()
        require(similarity.isFinite() && similarity in -1.0..1.0)
        val profile = requireNotNull(dao.profile(profileId))
        val person = requireNotNull(db.visitDao().getPerson(personId))
        db.visitDao().upsertPerson(person.copy(suggestedProfileId = profileId, suggestedName = profile.name,
            similarity = similarity, confidenceBand = "possible_match", reviewState = "unreviewed", version = person.version + 1))
    }

    suspend fun setSuggestion(personId: String, profileId: String, similarity: Double) = suggestIdentity(personId, profileId, similarity)

    suspend fun savePhoto(personId: String) {
        unlock.requireUnlocked()
        requireNotNull(dao.mediaForPerson(personId)) { "Photo unavailable" }
        db.withTransaction {
            dao.saveMedia(personId)
            db.visitDao().getPerson(personId)?.let { db.visitDao().upsertPerson(it.copy(saved = true)) }
            audit(personId, null, "photo_saved", "Owner kept this image beyond the default 30-day window")
        }
    }

    suspend fun markUnknown(personId: String) {
        unlock.requireUnlocked()
        val references = dao.referencesForPerson(personId)
        references.forEach { vault.delete(it.vaultId) }
        db.withTransaction {
            val person = requireNotNull(db.visitDao().getPerson(personId))
            dao.deletePersonReferences(personId)
            references.map { it.profileId }.distinct().forEach { dao.recountSamples(it) }
            db.visitDao().upsertPerson(person.copy(confirmedProfileId = null, suggestedProfileId = null,
                suggestedName = null, similarity = 0.0, confidenceBand = "unknown", reviewState = "unknown", version = person.version + 1))
            audit(personId, null, "identity_cleared", "Owner marked the person unknown and removed that person's reference enrollment")
        }
    }

    suspend fun setVisitDirection(visitId: String, direction: String) {
        unlock.requireUnlocked()
        require(direction in setOf("arrival", "departure", "visit"))
        db.withTransaction {
            val visit = requireNotNull(db.visitDao().getById(visitId)).visit
            db.visitDao().upsertVisit(visit.copy(eventType = direction, version = visit.version + 1))
            audit("", null, "direction_labeled", "Owner labeled visit $visitId as $direction; direction is not inferred by AI")
        }
    }

    suspend fun importVisit(faces: List<PrivateFaceInput>, source: String = "owner-import"): String {
        unlock.requireUnlocked()
        require(faces.size <= 32 && source.length <= 120)
        val visitId = uuid()
        val now = Instant.now()
        val retention = retentionSettings()
        val writes = mutableListOf<String>()
        try {
            db.withTransaction {
                db.visitDao().upsertVisit(VisitEntity(visitId, "owner-import", now.toString(), "needs_review", source, faces.size, "${faces.size} people detected", "Review possible identities", 1))
                faces.forEach { face ->
                    require(face.jpeg.size <= 10 * 1024 * 1024 && face.jpeg.size >= 3)
                    require(face.jpeg[0] == 0xff.toByte() && face.jpeg[1] == 0xd8.toByte()) { "Image-only JPEG required" }
                    require(face.embedding.size in 1..2048 && face.embedding.all { it.isFinite() })
                    val personId = uuid()
                    val vaultId = "media/${uuid()}"
                    vault.put(vaultId, face.jpeg)
                    writes += vaultId
                    db.visitDao().upsertPerson(PersonEntity(personId, visitId, "unreviewed", "unknown", 0.0, null, null, null, true, false, 1))
                    dao.insertMedia(PrivateMediaEntity(uuid(), visitId, personId, vaultId, hash(face.jpeg), now.toString(), now.plus(retention.photoDays.toLong(), ChronoUnit.DAYS).toString(), false, encode(face.embedding)))
                }
                audit("", null, "visit_imported", "Image-only import; $source; ${faces.size} faces")
            }
        } catch (error: Exception) {
            writes.forEach(vault::delete)
            throw error
        }
        return visitId
    }

    suspend fun confirmIdentity(personId: String, profileId: String? = null, label: String = ""): String {
        unlock.requireUnlocked()
        require(label.length <= 120)
        val person = requireNotNull(db.visitDao().getPerson(personId))
        val media = requireNotNull(dao.mediaForPerson(personId)) { "Face photo has expired" }
        val referenceId = "reference/${uuid()}"
        val oldReferences = dao.referencesForPerson(personId)
        vault.put(referenceId, vault.get(media.vaultId))
        try {
            val enrolled = db.withTransaction {
                val id = profileId ?: uuid()
                val existing = if (profileId != null) requireNotNull(dao.profile(id)) else null
                val name = existing?.name ?: label.trim().ifEmpty { "Visitor ${dao.profileCount() + 1}" }
                db.reviewDao().upsertProfile(ProfileEntity(id, name, (existing?.sampleCount ?: 0) + 1, Instant.now().toString()))
                dao.deletePersonReferences(personId)
                dao.insertReference(PrivateReferenceEntity(uuid(), id, personId, referenceId, media.embedding, Instant.now().toString()))
                (oldReferences.map { it.profileId } + id).distinct().forEach { dao.recountSamples(it) }
                db.visitDao().upsertPerson(person.copy(confirmedProfileId = id, reviewState = "confirmed", suggestedProfileId = null, suggestedName = null, version = person.version + 1))
                audit(personId, id, "identity_confirmed", "Owner confirmed and enrolled reference")
                id
            }
            oldReferences.forEach { old -> vault.delete(old.vaultId) }
            return enrolled
        } catch (error: Exception) {
            vault.delete(referenceId)
            throw error
        }
    }

    suspend fun correctProfile(profileId: String, label: String) {
        unlock.requireUnlocked()
        require(label.isNotBlank() && label.length <= 120)
        db.withTransaction {
            val profile = requireNotNull(dao.profile(profileId))
            db.reviewDao().upsertProfile(profile.copy(name = label.trim(), updatedAt = Instant.now().toString()))
            audit("", profileId, "profile_corrected", "Owner changed profile label")
        }
    }

    suspend fun deleteProfile(profileId: String) {
        unlock.requireUnlocked()
        val references = dao.referencesForProfile(profileId)
        // Erase encrypted media first; interrupted cleanup can be retried using database rows.
        references.forEach { vault.delete(it.vaultId) }
        db.withTransaction {
            val profile = dao.profile(profileId) ?: return@withTransaction
            dao.deleteReferences(profileId)
            dao.unlinkProfile(profileId)
            dao.deleteProfileProposals(profile.name)
            dao.removeProfileAudit(profileId)
            dao.deleteProfile(profileId)
            // No deleted label or biometric identifier retained in this deletion receipt.
            audit("", null, "profile_deleted", "Owner erased a profile and its reference images")
        }
    }

    suspend fun deleteVisit(visitId: String) {
        unlock.requireUnlocked()
        val visit = db.visitDao().getById(visitId) ?: return
        dao.mediaForVisit(visitId).forEach { vault.delete(it.vaultId) }
        db.withTransaction {
            dao.mediaForVisit(visitId).forEach { dao.deleteMedia(it.id) }
            dao.removePersonAudit(visit.people.map { it.id })
            dao.removeVisitProposals(visitId)
            dao.deleteVisit(visitId)
            audit("", null, "visit_deleted", "Owner erased a visit")
        }
    }

    suspend fun applyRetention(now: Instant = Instant.now()) {
        unlock.requireUnlocked()
        val retention = retentionSettings()
        dao.expiredMedia(now.toString()).forEach { media ->
            vault.delete(media.vaultId)
            db.withTransaction {
                dao.deleteMedia(media.id)
                db.visitDao().getPerson(media.personId)?.let { db.visitDao().upsertPerson(it.copy(mediaAvailable = false)) }
                audit(media.personId, null, "photo_expired", "Unsaved image removed after configured retention window")
            }
        }
        dao.expiredVisits(now.minus(retention.logDays.toLong(), ChronoUnit.DAYS).toString()).forEach { deleteVisit(it.id) }
    }

    suspend fun faceImage(personId: String): ByteArray? {
        unlock.requireUnlocked()
        return dao.mediaForPerson(personId)?.let { vault.get(it.vaultId) }
    }

    suspend fun references(): List<PrivateReference> {
        unlock.requireUnlocked()
        return dao.references().map { PrivateReference(it.profileId, decode(it.embedding)) }
    }

    suspend fun exportRecords(): ByteArray {
        unlock.requireUnlocked()
        val exportedAt = Instant.now().toString()
        val media = dao.allMedia().associateBy { it.personId }
        // Authenticate stored images and rehash them before reporting integrity metadata.
        media.values.forEach { check(hash(vault.get(it.vaultId)) == it.sha256) { "Stored image integrity mismatch" } }
        val visits = observeVisits().first()
        val entries = JSONArray()
        val exportedProfiles = JSONArray()
        observeProfiles().first().forEach { profile ->
            exportedProfiles.put(JSONObject().put("profileId", profile.id)
                .put("ownerLabel", profile.name).put("updatedAt", profile.updatedAt))
        }
        visits.forEach { record ->
            val people = JSONArray()
            record.people.forEach { person ->
                val image = media[person.id]
                people.put(JSONObject().put("personId", person.id).put("confirmedProfileId", person.confirmedProfileId ?: JSONObject.NULL)
                    .put("reviewState", person.reviewState).put("mediaSha256", image?.sha256 ?: JSONObject.NULL)
                    .put("mediaTransformation", "Sanitized face crop; JPEG re-encoded; original imported file is not retained"))
            }
            entries.put(JSONObject().put("visitId", record.visit.id).put("source", record.visit.source).put("ownerLabeledDirection", record.visit.eventType)
                .put("recordedAt", record.visit.occurredAt).put("sourceCaptureTime", JSONObject.NULL).put("people", people))
        }
        val auditEntries = JSONArray()
        dao.audit().forEach { auditEntries.put(JSONObject().put("action", it.action).put("occurredAt", it.occurredAt).put("detail", it.detail)
            .put("actor", it.actor).put("personId", it.personId).put("profileId", it.profileId ?: JSONObject.NULL)) }
        audit("", null, "records_exported", "Owner exported ${visits.size} visit records")
        return JSONObject().put("formatVersion", 1).put("exportedAt", exportedAt)
            .put("description", "Owner records; hashes describe images at ingestion, not proof of authenticity or legal admissibility")
            .put("visits", entries).put("profiles", exportedProfiles).put("audit", auditEntries).toString(2).toByteArray()
    }

    private suspend fun audit(personId: String, profileId: String?, action: String, detail: String) {
        db.reviewDao().appendAudit(AuditEntity(uuid(), profileId, personId, "device-owner", action, detail, Instant.now().toString()))
    }

    private fun uuid() = UUID.randomUUID().toString()
    private fun hash(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
    private fun encode(values: FloatArray): ByteArray = ByteBuffer.allocate(values.size * 4).apply { values.forEach { putFloat(it) } }.array()
    private fun decode(bytes: ByteArray): FloatArray {
        require(bytes.size % 4 == 0)
        val buffer = ByteBuffer.wrap(bytes)
        return FloatArray(bytes.size / 4) { buffer.float }
    }
}
