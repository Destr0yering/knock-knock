package com.knockknock.core.database

import android.content.Context
import androidx.room.Dao
import androidx.room.Entity
import androidx.room.Index
import androidx.room.Insert
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.Room
import com.knockknock.core.privacy.DatabasePassphrase
import net.zetetic.database.sqlcipher.SupportOpenHelperFactory

/** Separate file: legacy plaintext synthetic demo data is never mistaken for private records. */
fun createPrivateDatabase(context: Context, databaseName: String = "knock-knock-private.db"): KnockKnockDatabase {
    require(databaseName.matches(Regex("[A-Za-z0-9._-]+"))) { "Invalid database filename" }
    System.loadLibrary("sqlcipher")
    val passphrase = DatabasePassphrase(context).loadOrCreate()
    return Room.databaseBuilder(context.applicationContext, KnockKnockDatabase::class.java, databaseName)
        .openHelperFactory(SupportOpenHelperFactory(passphrase))
        .addMigrations(KnockKnockDatabase.MIGRATION_1_2, KnockKnockDatabase.MIGRATION_2_3)
        .build()
}

@Entity(tableName = "private_media", indices = [Index("visitId"), Index("personId"), Index("expiresAt")])
data class PrivateMediaEntity(
    @PrimaryKey val id: String,
    val visitId: String,
    val personId: String,
    val vaultId: String,
    val sha256: String,
    val capturedAt: String,
    val expiresAt: String,
    val saved: Boolean,
    val embedding: ByteArray,
)

@Entity(tableName = "private_references", indices = [Index("profileId"), Index("personId")])
data class PrivateReferenceEntity(
    @PrimaryKey val id: String,
    val profileId: String,
    val personId: String,
    val vaultId: String,
    val embedding: ByteArray,
    val enrolledAt: String,
)

@Dao
interface PrivateDao {
    @Insert suspend fun insertMedia(media: PrivateMediaEntity)
    @Insert suspend fun insertReference(reference: PrivateReferenceEntity)
    @Query("SELECT * FROM private_media WHERE personId = :personId LIMIT 1")
    suspend fun mediaForPerson(personId: String): PrivateMediaEntity?
    @Query("SELECT * FROM private_media WHERE visitId = :visitId")
    suspend fun mediaForVisit(visitId: String): List<PrivateMediaEntity>
    @Query("SELECT personId FROM private_media WHERE visitId = :visitId ORDER BY rowid")
    suspend fun orderedPersonIds(visitId: String): List<String>
    @Query("SELECT * FROM private_media WHERE saved = 0 AND expiresAt <= :now")
    suspend fun expiredMedia(now: String): List<PrivateMediaEntity>
    @Query("DELETE FROM private_media WHERE id = :id") suspend fun deleteMedia(id: String)
    @Query("SELECT * FROM private_references") suspend fun references(): List<PrivateReferenceEntity>
    @Query("SELECT * FROM private_references WHERE profileId = :profileId")
    suspend fun referencesForProfile(profileId: String): List<PrivateReferenceEntity>
    @Query("SELECT * FROM private_references WHERE personId = :personId")
    suspend fun referencesForPerson(personId: String): List<PrivateReferenceEntity>
    @Query("DELETE FROM private_references WHERE personId = :personId") suspend fun deletePersonReferences(personId: String)
    @Query("UPDATE profiles SET sampleCount = (SELECT COUNT(*) FROM private_references WHERE profileId = :id) WHERE id = :id")
    suspend fun recountSamples(id: String)
    @Query("UPDATE private_media SET saved = 1 WHERE personId = :personId") suspend fun saveMedia(personId: String)
    @Query("UPDATE private_media SET expiresAt = :expiresAt WHERE id = :id")
    suspend fun updateMediaExpiry(id: String, expiresAt: String)
    @Query("DELETE FROM private_references WHERE profileId = :profileId") suspend fun deleteReferences(profileId: String)
    @Query("SELECT * FROM profiles WHERE id = :id") suspend fun profile(id: String): ProfileEntity?
    @Query("DELETE FROM profiles WHERE id = :id") suspend fun deleteProfile(id: String)
    @Query("SELECT COUNT(*) FROM profiles") suspend fun profileCount(): Int
    @Query("UPDATE visit_people SET confirmedProfileId = NULL, suggestedProfileId = NULL, suggestedName = NULL, reviewState = 'unreviewed' WHERE confirmedProfileId = :profileId OR suggestedProfileId = :profileId")
    suspend fun unlinkProfile(profileId: String)
    @Query("DELETE FROM profile_proposals WHERE proposedName = :name") suspend fun deleteProfileProposals(name: String)
    @Query("DELETE FROM visits WHERE id = :id") suspend fun deleteVisit(id: String)
    @Query("SELECT * FROM visits WHERE occurredAt <= :cutoff") suspend fun expiredVisits(cutoff: String): List<VisitEntity>
    @Query("SELECT * FROM audit_entries ORDER BY occurredAt") suspend fun audit(): List<AuditEntity>
    @Query("DELETE FROM audit_entries WHERE profileId = :profileId") suspend fun removeProfileAudit(profileId: String)
    @Query("DELETE FROM audit_entries WHERE personId IN (:personIds)") suspend fun removePersonAudit(personIds: List<String>)
    @Query("DELETE FROM profile_proposals WHERE visitId = :visitId") suspend fun removeVisitProposals(visitId: String)
    @Query("SELECT * FROM private_media") suspend fun allMedia(): List<PrivateMediaEntity>
}
