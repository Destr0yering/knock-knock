package com.knockknock.app

import android.app.Application
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

class KnockKnockApplication : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
        FirebaseSetup.initialize(this)
        // Cancel an older install's cloud refresh. Private mode never schedules remote work.
        WorkManager.getInstance(this).cancelUniqueWork("visit-refresh")
        runCatching { cleanupRecordExports(java.io.File(cacheDir, "record-exports")) }
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "local-export-cleanup",
            ExistingPeriodicWorkPolicy.KEEP,
            PeriodicWorkRequestBuilder<ExportCleanupWorker>(15, TimeUnit.MINUTES).build(),
        )
    }
}
