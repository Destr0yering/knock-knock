package com.knockknock.app

import android.content.Context
import androidx.room.Room
import com.knockknock.core.database.KnockKnockDatabase
import com.knockknock.core.database.VisitCache
import com.knockknock.core.database.ReviewCache
import com.knockknock.feature.timeline.TimelineRepository
import com.knockknock.feature.timeline.TimelineViewModel
import com.knockknock.feature.review.ApprovalViewModel
import com.knockknock.feature.review.ReviewRepository
import com.knockknock.feature.review.ReviewViewModel
import java.security.KeyStore

class AppContainer(context: Context) {
    val ownerUnlock = com.knockknock.core.privacy.OwnerUnlock(context)
    private val appContext = context.applicationContext
    private var privateDatabase: KnockKnockDatabase? = null
    private var privateRepository: com.knockknock.core.database.PrivateRecordsRepository? = null
    val privateRecords: com.knockknock.core.database.PrivateRecordsRepository
        get() {
            ownerUnlock.requireUnlocked()
            return privateRepository ?: com.knockknock.core.database.PrivateRecordsRepository(
                com.knockknock.core.database.createPrivateDatabase(appContext).also { privateDatabase = it },
                com.knockknock.core.privacy.EncryptedFileVault(appContext),
                ownerUnlock,
            ).also { privateRepository = it }
        }
    fun lockPrivateSession() {
        ownerUnlock.lock()
        privateDatabase?.close()
        privateDatabase = null
        privateRepository = null
    }

    fun clearLocalAccountData() {
        lockPrivateSession()
        database.close()
        appContext.databaseList().forEach(appContext::deleteDatabase)
        com.knockknock.core.privacy.destroyPrivateJournalMaterial(appContext)
        appContext.cacheDir.deleteRecursively()
        appContext.externalCacheDir?.deleteRecursively()
        appContext.filesDir.deleteRecursively()
        appContext.getExternalFilesDir(null)?.deleteRecursively()
        appContext.getSharedPreferences("cognito-session", Context.MODE_PRIVATE).edit().clear().commit()
        appContext.getSharedPreferences("cloud-alert-consent", Context.MODE_PRIVATE).edit().clear().commit()
        appContext.getSharedPreferences("private-journal-notice", Context.MODE_PRIVATE).edit().clear().commit()
        appContext.getSharedPreferences("ring-link-notice", Context.MODE_PRIVATE).edit().clear().commit()
        appContext.getSharedPreferences("tester-notice", Context.MODE_PRIVATE).edit().clear().commit()
        java.io.File(appContext.applicationInfo.dataDir, "shared_prefs").deleteRecursively()
        runCatching {
            KeyStore.getInstance("AndroidKeyStore").apply {
                load(null)
                deleteEntry("knock-knock-cognito-tokens")
            }
        }
    }
    val sessionProvider = CognitoAuth(appContext)

    private val database = Room.databaseBuilder(
        context,
        KnockKnockDatabase::class.java,
        "knock-knock-cache.db",
    ).addMigrations(KnockKnockDatabase.MIGRATION_1_2, KnockKnockDatabase.MIGRATION_2_3).build()

    val timelineRepository = TimelineRepository(
        cache = VisitCache(database.visitDao()),
    )

    val timelineViewModelFactory = TimelineViewModel.Factory(timelineRepository)

    private val reviewRepository = ReviewRepository(
        visits = VisitCache(database.visitDao()),
        reviews = ReviewCache(database.visitDao(), database.reviewDao()),
    )

    fun reviewViewModelFactory(visitId: String) = ReviewViewModel.Factory(visitId, reviewRepository)
    val approvalViewModelFactory = ApprovalViewModel.Factory(reviewRepository)
}
