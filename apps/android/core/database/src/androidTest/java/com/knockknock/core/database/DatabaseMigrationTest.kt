package com.knockknock.core.database

import androidx.room.testing.MigrationTestHelper
import androidx.sqlite.db.framework.FrameworkSQLiteOpenHelperFactory
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DatabaseMigrationTest {
    @get:Rule
    val helper = MigrationTestHelper(
        InstrumentationRegistry.getInstrumentation(),
        KnockKnockDatabase::class.java,
        emptyList(),
        FrameworkSQLiteOpenHelperFactory(),
    )

    @Test
    fun migrate1To2CreatesReviewHistoryTables() {
        helper.createDatabase(DB_NAME, 1).close()
        helper.runMigrationsAndValidate(DB_NAME, 2, true, KnockKnockDatabase.MIGRATION_1_2).use { db ->
            db.query("SELECT COUNT(*) FROM profiles").close()
            db.query("SELECT COUNT(*) FROM profile_proposals").close()
            db.query("SELECT COUNT(*) FROM audit_entries").close()
        }
    }

    private companion object { const val DB_NAME = "migration-test" }
}
