package com.knockknock.app

import android.content.Context
import androidx.room.Room
import com.knockknock.core.database.KnockKnockDatabase
import com.knockknock.core.database.VisitCache
import com.knockknock.core.model.DemoSessionProvider
import com.knockknock.core.network.NetworkFactory
import com.knockknock.feature.timeline.TimelineRepository
import com.knockknock.feature.timeline.TimelineViewModel

class AppContainer(context: Context) {
    val sessionProvider = DemoSessionProvider()

    private val database = Room.databaseBuilder(
        context,
        KnockKnockDatabase::class.java,
        "knock-knock-cache.db",
    ).build()

    private val api = NetworkFactory.create(
        baseUrl = BuildConfig.API_BASE_URL,
        sessionProvider = sessionProvider,
        debug = BuildConfig.DEBUG,
    )

    val timelineRepository = TimelineRepository(
        cache = VisitCache(database.visitDao()),
        api = api,
    )

    val timelineViewModelFactory = TimelineViewModel.Factory(timelineRepository)
}
