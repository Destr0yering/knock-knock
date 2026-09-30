package com.knockknock.core.database

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Transaction
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

@Dao
interface VisitDao {
    @Transaction
    @Query("SELECT * FROM visits ORDER BY occurredAt DESC")
    fun observeAll(): Flow<List<VisitWithPeople>>

    @Transaction
    @Query("SELECT * FROM visits WHERE id = :visitId")
    fun observeById(visitId: String): Flow<VisitWithPeople?>

    @Transaction
    @Query("SELECT * FROM visits WHERE id = :visitId")
    suspend fun getById(visitId: String): VisitWithPeople?

    @Upsert
    suspend fun upsertVisit(visit: VisitEntity)

    @Upsert
    suspend fun upsertPeople(people: List<PersonEntity>)

    @Query("SELECT * FROM visit_people WHERE id = :personId LIMIT 1")
    suspend fun getPerson(personId: String): PersonEntity?

    @Upsert
    suspend fun upsertPerson(person: PersonEntity)

    @Query("DELETE FROM visits")
    suspend fun deleteAllVisits()

    @Transaction
    suspend fun replaceAll(visits: List<VisitWithPeople>) {
        deleteAllVisits()
        visits.forEach { record ->
            upsertVisit(record.visit)
            upsertPeople(record.people)
        }
    }

    @Transaction
    suspend fun upsert(record: VisitWithPeople) {
        upsertVisit(record.visit)
        upsertPeople(record.people)
    }
}

@Dao
interface ReviewDao {
    @Query("SELECT * FROM profiles ORDER BY name COLLATE NOCASE")
    fun observeProfiles(): Flow<List<ProfileEntity>>

    @Query("SELECT * FROM profile_proposals ORDER BY createdAt DESC")
    fun observeProposals(): Flow<List<ProposalEntity>>

    @Query("SELECT * FROM audit_entries ORDER BY occurredAt DESC")
    fun observeAudit(): Flow<List<AuditEntity>>

    @Upsert
    suspend fun upsertProfile(profile: ProfileEntity)

    @Upsert
    suspend fun upsertProposal(proposal: ProposalEntity)

    @androidx.room.Insert(onConflict = androidx.room.OnConflictStrategy.ABORT)
    suspend fun appendAudit(entry: AuditEntity)
}
