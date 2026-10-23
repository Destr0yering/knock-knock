package com.knockknock.app

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import java.io.File

/** This worker only removes expired, generated share ZIPs; it has no network work. */
class ExportCleanupWorker(context: Context, parameters: WorkerParameters) : CoroutineWorker(context, parameters) {
    override suspend fun doWork(): Result = runCatching {
        cleanupRecordExports(File(applicationContext.cacheDir, "record-exports"))
        Result.success()
    }.getOrElse { Result.retry() }
}

internal fun cleanupRecordExports(directory: File, now: Long = System.currentTimeMillis()) {
    val expected = directory.canonicalFile
    if (!expected.exists()) return
    expected.listFiles()?.forEach { file ->
        // Follow neither nested folders nor links escaping the app's dedicated export directory.
        if (file.isFile && file.canonicalFile.parentFile == expected &&
            file.name.matches(Regex("knock-knock-[0-9a-fA-F-]{36}\\.zip")) &&
            file.lastModified() < now - 3_600_000
        ) check(file.delete() || !file.exists()) { "Expired export cleanup must be retried" }
    }
}
