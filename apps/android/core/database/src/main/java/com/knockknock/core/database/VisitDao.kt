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

    @Upsert
    suspend fun upsertVisit(visit: VisitEntity)

    @Upsert
    suspend fun upsertPeople(people: List<PersonEntity>)

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
