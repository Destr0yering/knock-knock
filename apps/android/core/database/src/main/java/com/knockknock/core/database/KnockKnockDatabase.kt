package com.knockknock.core.database

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [VisitEntity::class, PersonEntity::class],
    version = 1,
    exportSchema = true,
)
abstract class KnockKnockDatabase : RoomDatabase() {
    abstract fun visitDao(): VisitDao
}
