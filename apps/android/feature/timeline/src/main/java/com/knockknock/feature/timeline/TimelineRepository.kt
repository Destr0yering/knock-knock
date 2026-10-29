package com.knockknock.feature.timeline

import com.knockknock.core.database.VisitCache
import com.knockknock.core.model.VisitSummary
import com.knockknock.core.network.KnockKnockApi
import kotlinx.coroutines.flow.Flow

data class SyncResult(
    val offline: Boolean,
    val message: String? = null,
)

class TimelineRepository(
    private val cache: VisitCache,
    private val api: KnockKnockApi? = null,
) {
    val visits: Flow<List<VisitSummary>> = cache.observeVisits()

    suspend fun refresh(): SyncResult {
        val remoteApi = api ?: return SyncResult(offline = true, message = "Synthetic demo stays on this device.")
        return runCatching {
        val remote = remoteApi.listVisits().map { it.toDomain() }
        cache.replaceAll(remote)
    }.fold(
        onSuccess = { SyncResult(offline = false) },
        onFailure = {
            SyncResult(
                offline = true,
                message = "The server is unavailable. Saved visits are still ready.",
            )
        },
    )
    }

    suspend fun runDemo(scenario: String): SyncResult {
        cache.seedDemoScenario(scenario)
        return SyncResult(offline = true, message = "Synthetic $scenario visit added for review.")
    }
}
