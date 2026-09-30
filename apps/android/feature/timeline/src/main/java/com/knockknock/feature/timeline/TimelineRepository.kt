package com.knockknock.feature.timeline

import com.knockknock.core.database.VisitCache
import com.knockknock.core.model.VisitSummary
import com.knockknock.core.network.FixtureRequestDto
import com.knockknock.core.network.KnockKnockApi
import kotlinx.coroutines.flow.Flow

data class SyncResult(
    val offline: Boolean,
    val message: String? = null,
)

class TimelineRepository(
    private val cache: VisitCache,
    private val api: KnockKnockApi,
) {
    val visits: Flow<List<VisitSummary>> = cache.observeVisits()

    suspend fun refresh(): SyncResult = runCatching {
        val remote = api.listVisits().map { it.toDomain() }
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

    suspend fun runDemo(): SyncResult = runCatching {
        val created = api.createDemoEvent(FixtureRequestDto()).toDomain()
        cache.upsert(created)
    }.fold(
        onSuccess = { SyncResult(offline = false) },
        onFailure = {
            cache.seedOfflineDemo()
            SyncResult(
                offline = true,
                message = "Loaded the private offline fixture. Connect the local API to sync.",
            )
        },
    )
}
