package com.knockknock.core.evidence

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import java.io.ByteArrayOutputStream
import java.io.File
import java.security.MessageDigest
import java.time.Instant
import java.util.UUID
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream
import org.json.JSONArray
import org.json.JSONObject

/** Plaintext share exports are created only on explicit owner request. */
class RecordExporter(private val context: Context) {
    fun export(manifest: JSONObject, files: Map<String, ByteArray>): File {
        val dir = File(context.cacheDir, "record-exports").apply { mkdirs() }
        dir.listFiles()?.filter { it.lastModified() < System.currentTimeMillis() - 3600_000 }?.forEach { it.delete() }
        val output = File(dir, "knock-knock-${UUID.randomUUID()}.zip")
        val entries = JSONArray()
        val document = JSONObject(manifest.toString()).apply {
            put("exported_at", Instant.now().toString()); put("format_version", 1); put("audio_included", false)
            put("integrity_scope", "SHA-256 checks files against this manifest; does not prove authenticity or legal admissibility.")
            put("files", entries)
            put("media_transformations", "Owner-imported image decoded and resized, face cropped, then JPEG reencoded for export. Original camera capture time and original media integrity are not established.")
        }
        try {
            ZipOutputStream(output.outputStream()).use { zip ->
                files.forEach { (name, bytes) ->
                    require(name.matches(Regex("[A-Za-z0-9_-]+\\.jpg"))) { "Exports accept JPEG frames only." }
                    val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: error("Invalid export image.")
                    val clean = ByteArrayOutputStream().use { stream ->
                        bitmap.compress(Bitmap.CompressFormat.JPEG, 90, stream); bitmap.recycle(); stream.toByteArray()
                    }
                    try {
                        val hash = MessageDigest.getInstance("SHA-256").digest(clean).joinToString("") { "%02x".format(it) }
                        entries.put(JSONObject().put("name", name).put("sha256", hash).put("bytes", clean.size))
                        zip.putNextEntry(ZipEntry(name)); zip.write(clean); zip.closeEntry()
                    } finally { clean.fill(0) }
                }
                zip.putNextEntry(ZipEntry("manifest.json"))
                zip.write(document.toString(2).toByteArray(Charsets.UTF_8)); zip.closeEntry()
            }
            return output
        } catch (error: Exception) { output.delete(); throw error }
    }
}
