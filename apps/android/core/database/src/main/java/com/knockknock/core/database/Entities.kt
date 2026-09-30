package com.knockknock.core.database

import androidx.room.Embedded
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.Relation

@Entity(tableName = "visits")
data class VisitEntity(
    @androidx.room.PrimaryKey val id: String,
    val eventType: String,
    val occurredAt: String,
    val status: String,
    val source: String,
    val personCount: Int,
    val alertTitle: String,
    val alertBody: String,
    val version: Int,
)

@Entity(
    tableName = "visit_people",
    foreignKeys = [
        ForeignKey(
            entity = VisitEntity::class,
            parentColumns = ["id"],
            childColumns = ["visitId"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [Index("visitId")],
)
data class PersonEntity(
    @androidx.room.PrimaryKey val id: String,
    val visitId: String,
    val reviewState: String,
    val confidenceBand: String,
    val similarity: Double,
    val suggestedProfileId: String?,
    val suggestedName: String?,
    val confirmedProfileId: String?,
    val mediaAvailable: Boolean,
    val saved: Boolean,
    val version: Int,
)

data class VisitWithPeople(
    @Embedded val visit: VisitEntity,
    @Relation(parentColumn = "id", entityColumn = "visitId")
    val people: List<PersonEntity>,
)
