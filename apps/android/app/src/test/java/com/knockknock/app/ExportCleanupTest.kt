package com.knockknock.app

import java.io.File
import java.nio.file.Files
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ExportCleanupTest {
    @Test fun cleanupDeletesOnlyExpiredGeneratedExports() {
        val directory = Files.createTempDirectory("knock-knock-export-test").toFile()
        try {
            val now = System.currentTimeMillis()
            val expired = File(directory, "knock-knock-00000000-0000-0000-0000-000000000000.zip").apply { writeText("test"); setLastModified(now - 4_000_000) }
            val current = File(directory, "knock-knock-00000000-0000-0000-0000-000000000001.zip").apply { writeText("test") }
            val unrelated = File(directory, "owner-photo.jpg").apply { writeText("test"); setLastModified(now - 4_000_000) }
            cleanupRecordExports(directory, now)
            assertFalse(expired.exists())
            assertTrue(current.exists())
            assertTrue(unrelated.exists())
        } finally { directory.deleteRecursively() }
    }
}
