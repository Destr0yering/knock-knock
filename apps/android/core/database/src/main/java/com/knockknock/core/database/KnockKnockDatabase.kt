package com.knockknock.core.database

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [
        VisitEntity::class,
        PersonEntity::class,
        ProfileEntity::class,
        ProposalEntity::class,
        AuditEntity::class,
        PrivateMediaEntity::class,
        PrivateReferenceEntity::class,
    ],
    version = 3,
    exportSchema = true,
)
abstract class KnockKnockDatabase : RoomDatabase() {
    abstract fun visitDao(): VisitDao
    abstract fun reviewDao(): ReviewDao
    abstract fun privateDao(): PrivateDao

    companion object {
        val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("CREATE TABLE IF NOT EXISTS private_media (id TEXT NOT NULL PRIMARY KEY, visitId TEXT NOT NULL, personId TEXT NOT NULL, vaultId TEXT NOT NULL, sha256 TEXT NOT NULL, capturedAt TEXT NOT NULL, expiresAt TEXT NOT NULL, saved INTEGER NOT NULL, embedding BLOB NOT NULL)")
                db.execSQL("CREATE INDEX IF NOT EXISTS index_private_media_visitId ON private_media(visitId)")
                db.execSQL("CREATE INDEX IF NOT EXISTS index_private_media_personId ON private_media(personId)")
                db.execSQL("CREATE INDEX IF NOT EXISTS index_private_media_expiresAt ON private_media(expiresAt)")
                db.execSQL("CREATE TABLE IF NOT EXISTS private_references (id TEXT NOT NULL PRIMARY KEY, profileId TEXT NOT NULL, personId TEXT NOT NULL, vaultId TEXT NOT NULL, embedding BLOB NOT NULL, enrolledAt TEXT NOT NULL)")
                db.execSQL("CREATE INDEX IF NOT EXISTS index_private_references_profileId ON private_references(profileId)")
                db.execSQL("CREATE INDEX IF NOT EXISTS index_private_references_personId ON private_references(personId)")
            }
        }
        val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    "CREATE TABLE IF NOT EXISTS `profiles` (`id` TEXT NOT NULL, `name` TEXT NOT NULL, " +
                        "`sampleCount` INTEGER NOT NULL, `updatedAt` TEXT NOT NULL, PRIMARY KEY(`id`))",
                )
                db.execSQL(
                    "CREATE TABLE IF NOT EXISTS `profile_proposals` (`id` TEXT NOT NULL, `visitId` TEXT NOT NULL, " +
                        "`personId` TEXT NOT NULL, `proposedName` TEXT NOT NULL, `proposer` TEXT NOT NULL, " +
                        "`status` TEXT NOT NULL, `createdAt` TEXT NOT NULL, `decidedBy` TEXT, `decidedAt` TEXT, " +
                        "PRIMARY KEY(`id`))",
                )
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_profile_proposals_visitId` ON `profile_proposals` (`visitId`)")
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_profile_proposals_personId` ON `profile_proposals` (`personId`)")
                db.execSQL(
                    "CREATE TABLE IF NOT EXISTS `audit_entries` (`id` TEXT NOT NULL, `profileId` TEXT, " +
                        "`personId` TEXT NOT NULL, `actor` TEXT NOT NULL, `action` TEXT NOT NULL, " +
                        "`detail` TEXT NOT NULL, `occurredAt` TEXT NOT NULL, PRIMARY KEY(`id`))",
                )
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_audit_entries_personId` ON `audit_entries` (`personId`)")
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_audit_entries_occurredAt` ON `audit_entries` (`occurredAt`)")
            }
        }
    }
}
