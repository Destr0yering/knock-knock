package com.knockknock.app

import android.content.Context
import com.google.firebase.messaging.FirebaseMessaging
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import com.google.android.gms.tasks.Tasks
import java.util.concurrent.TimeUnit

internal data class DeletionReceipt(val requestId: String, val receipt: String, val localDataCleared: Boolean)

internal object AccountDeletionClient {
    private val http = OkHttpClient()

    fun requestAndErase(context: Context, container: AppContainer): DeletionReceipt {
        val idToken = container.sessionProvider.currentSession().accessToken
            ?: error("Sign in again before requesting account deletion.")
        val payload = JSONObject().put("confirmation", "DELETE").toString()
            .toRequestBody("application/json".toMediaType())
        val request = Request.Builder().url(apiUrl("/v1/account/deletion"))
            .header("Authorization", "Bearer $idToken").post(payload).build()
        val result = http.newCall(request).execute().use { response ->
            check(response.code == 202) {
                if (response.code == 409) "Deletion is already in progress. Use the saved receipt to check status."
                else "The server did not accept the deletion request (${response.code})."
            }
            JSONObject(response.body?.string().orEmpty())
        }
        val receipt = DeletionReceipt(result.getString("request_id"), result.getString("receipt"), false)
        runCatching { Tasks.await(FirebaseMessaging.getInstance().deleteToken(), 10, TimeUnit.SECONDS) }
        val cleared = runCatching { container.clearLocalAccountData() }.isSuccess
        context.getSharedPreferences(RECEIPT_PREFS, Context.MODE_PRIVATE).edit()
            .putString("request_id", receipt.requestId).putString("receipt", receipt.receipt).commit()
        return receipt.copy(localDataCleared = cleared)
    }

    fun status(context: Context): String? {
        val prefs = context.getSharedPreferences(RECEIPT_PREFS, Context.MODE_PRIVATE)
        val requestId = prefs.getString("request_id", null) ?: return null
        val receipt = prefs.getString("receipt", null) ?: return "Deletion status receipt is missing."
        val request = Request.Builder().url(apiUrl("/v1/account/deletion/$requestId"))
            .header("X-Deletion-Receipt", receipt).get().build()
        return http.newCall(request).execute().use { response ->
            if (!response.isSuccessful) return@use "Deletion status: ${response.code}. Check the connection and try again."
            val status = JSONObject(response.body?.string().orEmpty()).optString("status", "queued")
            when (status) {
                "complete" -> "Account deletion is complete. Some AWS backup and operational log copies expire under their retention windows. Remove Knock Knock from Ring Appstore > My Apps to revoke Ring's one-way account link."
                "processing" -> "Deletion is processing. This page checks again automatically."
                else -> "Deletion is queued. This page checks again automatically."
            }
        }
    }

    private fun apiUrl(path: String) = BuildConfig.API_BASE_URL.trimEnd('/') + path
    private const val RECEIPT_PREFS = "account-deletion-receipt"
}
