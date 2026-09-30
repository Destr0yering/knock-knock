package com.knockknock.app

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters

class VisitRefreshWorker(
    context: Context,
    parameters: WorkerParameters,
) : CoroutineWorker(context, parameters) {
    override suspend fun doWork(): Result {
        val app = applicationContext as KnockKnockApplication
        val result = app.container.timelineRepository.refresh()
        return if (result.offline) Result.retry() else Result.success()
    }
}
