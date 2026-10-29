package com.knockknock.app

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import androidx.core.app.NotificationManagerCompat
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.messaging.FirebaseMessaging
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.Executors

internal object FirebaseSetup {
    fun initialize(context: Context): Boolean {
        if (BuildConfig.FIREBASE_PROJECT_ID.isBlank() ||
            BuildConfig.FIREBASE_APPLICATION_ID.isBlank() ||
            BuildConfig.FIREBASE_API_KEY.isBlank() ||
            BuildConfig.FIREBASE_SENDER_ID.isBlank()
        ) return false
        return runCatching {
            if (FirebaseApp.getApps(context).isEmpty()) {
                FirebaseApp.initializeApp(context, FirebaseOptions.Builder()
                    .setProjectId(BuildConfig.FIREBASE_PROJECT_ID)
                    .setApplicationId(BuildConfig.FIREBASE_APPLICATION_ID)
                    .setApiKey(BuildConfig.FIREBASE_API_KEY)
                    .setGcmSenderId(BuildConfig.FIREBASE_SENDER_ID)
                    .build())
            }
            FirebaseApp.getApps(context).isNotEmpty()
        }.getOrDefault(false)
    }
}

internal class FcmPushCoordinator(context: Context) {
    private val app = context.applicationContext
    private val preferences = app.getSharedPreferences("cloud-alert-consent", Context.MODE_PRIVATE)
    private val http = OkHttpClient()
    private val executor = PUSH_EXECUTOR

    fun setConsent(enabled: Boolean, onResult: (String) -> Unit = {}) {
        preferences.edit().putBoolean(CONSENT_KEY, enabled).apply()
        if (!enabled) {
            val fingerprint = preferences.getString(FINGERPRINT_KEY, null)
            if (fingerprint == null) {
                report(onResult, "Push alerts are off on this tablet.")
                return
            }
            executor.execute {
                val idToken = (app as KnockKnockApplication).container.sessionProvider.currentSession().accessToken
                if (idToken.isNullOrBlank()) {
                    report(onResult, "Alerts are hidden locally. Sign in to revoke this device token from the server.")
                    return@execute
                }
                val request = Request.Builder()
                    .url(apiUrl("/v1/devices/tokens/$fingerprint"))
                    .header("Authorization", "Bearer $idToken")
                    .delete()
                    .build()
                val result = runCatching { http.newCall(request).execute().use { it.isSuccessful } }.getOrDefault(false)
                if (result) preferences.edit().remove(FINGERPRINT_KEY).apply()
                report(onResult, if (result) "Push consent withdrawn and device token revoked." else "Push alerts are off locally; server token revocation needs a connection and sign-in.")
            }
            return
        }
        report(onResult, "Push consent saved. Enable Android notifications and sign in to register this tablet.")
    }

    fun syncToken(onResult: (String) -> Unit) {
        if (!preferences.getBoolean(CONSENT_KEY, false)) {
            report(onResult, "Turn on push alert consent first.")
            return
        }
        if (Build.VERSION.SDK_INT >= 33 && app.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            report(onResult, "Allow Android notifications, then tap Enable alerts again.")
            return
        }
        if (!FirebaseSetup.initialize(app)) {
            report(onResult, "Firebase is not configured for this Android app yet.")
            return
        }
        val session = (app as KnockKnockApplication).container.sessionProvider.currentSession()
        val idToken = session.accessToken
        if (idToken.isNullOrBlank()) {
            report(onResult, "Sign in with the DoorMemo account before registering push alerts.")
            return
        }
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (!task.isSuccessful || task.result.isNullOrBlank()) {
                report(onResult, "Firebase could not create a device token.")
                return@addOnCompleteListener
            }
            executor.execute {
                val payload = JSONObject()
                    .put("token", task.result)
                    .put("alerts_consent", true)
                    .put("consent_version", CONSENT_VERSION)
                    .toString()
                    .toRequestBody("application/json".toMediaType())
                val request = Request.Builder()
                    .url(apiUrl("/v1/devices/tokens"))
                    .header("Authorization", "Bearer $idToken")
                    .post(payload)
                    .build()
                val previous = preferences.getString(FINGERPRINT_KEY, null)
                val fingerprint = runCatching {
                    http.newCall(request).execute().use { response ->
                        if (!response.isSuccessful) return@use null
                        JSONObject(response.body?.string().orEmpty()).optString("fingerprint").takeIf(String::isNotBlank)
                    }
                }.getOrNull()
                if (fingerprint == null) {
                    report(onResult, "The server could not register push alerts. Check sign-in and connection.")
                    return@execute
                }
                preferences.edit().putString(FINGERPRINT_KEY, fingerprint).apply()
                if (previous != null && previous != fingerprint) revokeOld(previous, idToken)
                report(onResult, "Generic visitor alerts are enabled on this tablet.")
            }
        }
    }

    private fun revokeOld(fingerprint: String, idToken: String) {
        val request = Request.Builder().url(apiUrl("/v1/devices/tokens/$fingerprint"))
            .header("Authorization", "Bearer $idToken").delete().build()
        runCatching { http.newCall(request).execute().close() }
    }

    private fun apiUrl(path: String) = BuildConfig.API_BASE_URL.trimEnd('/') + path

    private fun report(callback: (String) -> Unit, value: String) {
        MAIN_HANDLER.post { callback(value) }
    }

    private companion object {
        val PUSH_EXECUTOR = Executors.newSingleThreadExecutor()
        val MAIN_HANDLER = Handler(Looper.getMainLooper())
        const val CONSENT_KEY = "accepted_v1"
        const val FINGERPRINT_KEY = "token_fingerprint"
        const val CONSENT_VERSION = "2026-10-15-v1"
    }
}

internal class KnockKnockMessagingService : com.google.firebase.messaging.FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        FcmPushCoordinator(this).syncToken { }
    }

    override fun onMessageReceived(message: com.google.firebase.messaging.RemoteMessage) {
        val visitId = message.data["visit_id"] ?: return
        if (!visitId.matches(Regex("^[0-9a-fA-F-]{36}$"))) return
        if (!getSharedPreferences("cloud-alert-consent", Context.MODE_PRIVATE)
                .getBoolean("accepted_v1", false)) return
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return
        if (!NotificationManagerCompat.from(this).areNotificationsEnabled()) return
        LocalVisitorNotificationGateway(this).showVisitAlert(
            visitId,
            com.knockknock.core.model.VisitorAlert("DoorMemo", "A visitor event is ready. Unlock to review.", false),
        )
    }
}
