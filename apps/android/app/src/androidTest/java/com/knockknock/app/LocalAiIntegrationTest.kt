package com.knockknock.app

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.knockknock.core.evidence.RecordExporter
import com.knockknock.core.database.createPrivateDatabase
import com.knockknock.core.database.PrivateRecordsRepository
import com.knockknock.core.database.PrivateFaceInput
import com.knockknock.core.privacy.EncryptedFileVault
import com.knockknock.core.privacy.OwnerUnlock
import com.knockknock.core.vision.FaceReference
import com.knockknock.core.vision.OpenCvLocalFaceEngine
import com.knockknock.core.vision.SimilarityMatcher
import java.security.MessageDigest
import java.util.zip.ZipFile
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.flow.first

@RunWith(AndroidJUnit4::class)
class LocalAiIntegrationTest {
    private val context = InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun privateBuildCannotOpenNetworkOrRecordAudio() {
        val permissions = context.packageManager.getPackageInfo(context.packageName, PackageManager.GET_PERMISSIONS)
            .requestedPermissions.orEmpty().toSet()
        assertFalse(permissions.contains(Manifest.permission.INTERNET))
        assertFalse(permissions.contains(Manifest.permission.RECORD_AUDIO))
    }

    @Test fun bundledModelsDetectSyntheticFaceAndExportHashesActualImageBytes() {
        val resource = context.resources.getIdentifier("demo_unknown_01", "drawable", context.packageName)
        assertTrue("Synthetic fixture must be bundled", resource != 0)
        val bitmap = BitmapFactory.decodeResource(context.resources, resource,
            BitmapFactory.Options().apply { inScaled = false })
        val faces = try { OpenCvLocalFaceEngine(context).analyze(bitmap) } finally { bitmap.recycle() }
        assertTrue("Actual model must detect the synthetic fixture face", faces.isNotEmpty())
        val face = faces.first()
        try {
            assertTrue(face.embedding.isNotEmpty() && face.embedding.all { it.isFinite() })
            assertEquals("fixture", SimilarityMatcher.suggest(face.embedding,
                listOf(FaceReference("fixture", face.embedding.copyOf())))?.profileId)
            val databaseName = "test-ai-${java.util.UUID.randomUUID()}.db"
            val db = createPrivateDatabase(context, databaseName)
            val repository = PrivateRecordsRepository(db, EncryptedFileVault(context), OwnerUnlock(context).apply { confirmUnlock() })
            try {
                runBlocking {
                    val firstVisit = repository.importVisit(listOf(PrivateFaceInput(face.jpeg, face.embedding, face.confidence.toDouble())), "synthetic-test")
                    val profile = repository.confirmIdentity(repository.personIdsForVisit(firstVisit).single(), label = "Synthetic fixture visitor")
                    val secondVisit = repository.importVisit(listOf(PrivateFaceInput(face.jpeg, face.embedding, face.confidence.toDouble())), "synthetic-test")
                    val suggestion = SimilarityMatcher.suggest(face.embedding, repository.references().map { FaceReference(it.profileId, it.embedding) })
                    assertEquals(profile, suggestion?.profileId)
                    val personId = repository.personIdsForVisit(secondVisit).single()
                    repository.suggestIdentity(personId, profile, requireNotNull(suggestion).similarity)
                    val person = repository.observeVisits().first().flatMap { it.people }.first { it.id == personId }
                    assertNull("AI cannot confirm an identity", person.confirmedProfileId)
                    assertEquals(profile, person.suggestedProfileId)
                    val manifest = JSONObject(String(repository.exportRecords(), Charsets.UTF_8))
                    assertEquals("Synthetic fixture visitor", manifest.getJSONArray("profiles").getJSONObject(0).getString("ownerLabel"))
                    repository.deleteProfile(profile)
                    repository.deleteVisit(firstVisit)
                    repository.deleteVisit(secondVisit)
                }
            } finally { db.close(); context.deleteDatabase(databaseName) }
            val exported = RecordExporter(context).export(JSONObject().put("source", "synthetic-test")
                .put("capture_time", JSONObject.NULL), mapOf("fixture.jpg" to face.jpeg))
            try {
                ZipFile(exported).use { zip ->
                    val document = JSONObject(zip.getInputStream(zip.getEntry("manifest.json")).bufferedReader().readText())
                    val bytes = zip.getInputStream(zip.getEntry("fixture.jpg")).readBytes()
                    val sha = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
                    assertEquals(sha, document.getJSONArray("files").getJSONObject(0).getString("sha256"))
                    assertFalse(document.getBoolean("audio_included"))
                    bytes.fill(0)
                }
            } finally { exported.delete() }
            try {
                RecordExporter(context).export(JSONObject(), mapOf("recording.mp4" to face.jpeg))
                fail("Audio/video containers cannot be exported")
            } catch (_: IllegalArgumentException) { }
        } finally { faces.forEach { it.jpeg.fill(0); it.embedding.fill(0f) } }
    }
}
