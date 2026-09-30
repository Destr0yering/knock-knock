package com.knockknock.app

import android.content.Context
import androidx.room.Room
import com.knockknock.core.database.KnockKnockDatabase
import com.knockknock.core.database.VisitCache
import com.knockknock.core.database.ReviewCache
import com.knockknock.core.model.DemoSessionProvider
import com.knockknock.core.network.NetworkFactory
import com.knockknock.feature.timeline.TimelineRepository
import com.knockknock.feature.timeline.TimelineViewModel
import com.knockknock.feature.review.ApprovalViewModel
import com.knockknock.feature.review.ReviewRepository
import com.knockknock.feature.review.ReviewViewModel

class AppContainer(context: Context) {
    val sessionProvider = DemoSessionProvider()

    private val database = Room.databaseBuilder(
        context,
        KnockKnockDatabase::class.java,
        "knock-knock-cache.db",
    ).addMigrations(KnockKnockDatabase.MIGRATION_1_2).build()

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

    private val reviewRepository = ReviewRepository(
        visits = VisitCache(database.visitDao()),
        reviews = ReviewCache(database.visitDao(), database.reviewDao()),
    )

    fun reviewViewModelFactory(visitId: String) = ReviewViewModel.Factory(visitId, reviewRepository)
    val approvalViewModelFactory = ApprovalViewModel.Factory(reviewRepository)
}
