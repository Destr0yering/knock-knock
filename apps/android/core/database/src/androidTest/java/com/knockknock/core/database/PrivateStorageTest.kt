package com.knockknock.core.database

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import android.graphics.Bitmap
import com.knockknock.core.privacy.EncryptedFileVault
import com.knockknock.core.privacy.OwnerUnlock
import java.time.Instant
import java.time.temporal.ChronoUnit
import java.io.ByteArrayOutputStream
import java.util.UUID
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PrivateStorageTest {
    private val context = InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun encryptedDatabaseReopensAndPlainSqliteCannotReadIt() = runBlocking {
        val databaseName = "private-storage-test-${UUID.randomUUID()}.db"
        val db = createPrivateDatabase(context, databaseName)
        db.reviewDao().upsertProfile(ProfileEntity("test-profile", "Unique secret visitor", 0, Instant.now().toString()))
        db.close()
        val disk = context.getDatabasePath(databaseName).readBytes()
        assertFalse(String(disk.copyOfRange(0, 16)).startsWith("SQLite format 3"))
        assertFalse(String(disk).contains("Unique secret visitor"))
        val reopened = createPrivateDatabase(context, databaseName)
        try { assertEquals("Unique secret visitor", reopened.privateDao().profile("test-profile")?.name) }
        finally { reopened.close(); context.deleteDatabase(databaseName) }
    }

    @Test fun ownerCorrectionRemovesWrongReferenceAndRetentionRemovesUnsavedMedia() = runBlocking {
        val databaseName = "private-storage-test-${UUID.randomUUID()}.db"
        val db = createPrivateDatabase(context, databaseName)
        val gate = OwnerUnlock(context).apply { confirmUnlock() }
        val vault = EncryptedFileVault(context)
        val repository = PrivateRecordsRepository(db, vault, gate)
        try {
            val bitmap = Bitmap.createBitmap(8, 8, Bitmap.Config.ARGB_8888)
            val jpeg = ByteArrayOutputStream().apply { bitmap.compress(Bitmap.CompressFormat.JPEG, 90, this) }.toByteArray()
            bitmap.recycle()
            val visit = repository.importVisit(listOf(PrivateFaceInput(jpeg, floatArrayOf(1f, 0f), 0.9)))
            val person = repository.personIdsForVisit(visit).single()
            val first = repository.confirmIdentity(person, label = "Original")
            val replacement = repository.confirmIdentity(person, label = "Corrected")
            assertTrue(repository.references().none { it.profileId == first })
            assertEquals(replacement, repository.references().single().profileId)
            repository.applyRetention(Instant.now().plus(31, ChronoUnit.DAYS))
            assertNull(repository.faceImage(person))
            assertEquals(1, repository.observeVisits().first().size)
            repository.deleteProfile(replacement)
            assertTrue(repository.references().isEmpty())
            gate.lock()
            try {
                repository.importVisit(emptyList())
                fail("Locked owner must not mutate records")
            } catch (_: IllegalStateException) { }
        } finally {
            db.close()
            context.deleteDatabase(databaseName)
        }
    }
}
