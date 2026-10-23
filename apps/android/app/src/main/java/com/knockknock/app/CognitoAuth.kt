package com.knockknock.app

import android.content.Context
import android.net.Uri
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import com.knockknock.core.model.AppSession
import com.knockknock.core.model.HouseholdRole
import com.knockknock.core.model.SessionProvider
import okhttp3.FormBody
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.security.KeyStore
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.UUID
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Native Cognito Hosted UI client. Public app clients use OAuth code + PKCE and no client secret. */
class CognitoAuth(context: Context) : SessionProvider {
    private val prefs = context.applicationContext.getSharedPreferences("cognito-session", Context.MODE_PRIVATE)
    private val http = OkHttpClient()
    private val redirectUri = "knockknock://auth/callback"
    private val domain = BuildConfig.COGNITO_DOMAIN_URL.trimEnd('/')
    private val clientId = BuildConfig.COGNITO_CLIENT_ID

    /** Reports local token presence only; never returns token material to the UI. */
    fun hasStoredSession(): Boolean = prefs.contains("id_token") && prefs.contains("refresh_token")

    @Synchronized
    fun authorizationUri(): Uri {
        check(domain.startsWith("https://") && clientId.isNotBlank()) {
            "Cognito is not configured for this build. Set cognitoDomainUrl and cognitoClientId in Gradle properties."
        }
        val verifier = randomUrlSafe(64)
        val challenge = Base64.encodeToString(
            MessageDigest.getInstance("SHA-256").digest(verifier.toByteArray(Charsets.US_ASCII)),
            Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING,
        )
        val state = UUID.randomUUID().toString()
        putSecret("pending_verifier", verifier)
        putSecret("pending_state", state)
        return Uri.parse("$domain/oauth2/authorize").buildUpon()
            .appendQueryParameter("response_type", "code")
            .appendQueryParameter("client_id", clientId)
            .appendQueryParameter("redirect_uri", redirectUri)
            .appendQueryParameter("scope", "openid email")
            .appendQueryParameter("state", state)
            .appendQueryParameter("code_challenge", challenge)
            .appendQueryParameter("code_challenge_method", "S256")
            .build()
    }

    /** Call on an IO dispatcher. State is single-use and the callback code is never logged. */
    @Synchronized
    fun completeCallback(uri: Uri) {
        require(uri.scheme == "knockknock" && uri.host == "auth" && uri.path == "/callback") { "Unexpected sign-in callback." }
        val expectedState = getSecret("pending_state")
        val verifier = getSecret("pending_verifier")
        require(!expectedState.isNullOrBlank() && uri.getQueryParameter("state") == expectedState) { "Sign-in state validation failed. Start again." }
        val code = uri.getQueryParameter("code")
        require(!code.isNullOrBlank()) { "Cognito did not return an authorization code." }
        prefs.edit().remove("pending_state").remove("pending_verifier").apply()
        val body = FormBody.Builder()
            .add("grant_type", "authorization_code")
            .add("client_id", clientId)
            .add("redirect_uri", redirectUri)
            .add("code", code)
            .add("code_verifier", verifier.orEmpty())
            .build()
        val response = http.newCall(Request.Builder().url("$domain/oauth2/token").post(body).build()).execute()
        response.use {
            check(it.isSuccessful) { "Cognito sign-in could not be completed (${it.code})." }
            saveTokens(JSONObject(it.body?.string().orEmpty()), null)
        }
    }

    @Synchronized
    override fun currentSession(): AppSession {
        if (!hasStoredSession()) return AppSession("signed-out", HouseholdRole.OWNER)
        val expiresAt = prefs.getLong("expires_at", 0L)
        if (System.currentTimeMillis() / 1000 >= expiresAt - 60) refreshTokens()
        val idToken = getSecret("id_token") ?: return AppSession("signed-out", HouseholdRole.OWNER)
        val claims = runCatching {
            val payload = idToken.split('.')[1]
            JSONObject(String(Base64.decode(payload, Base64.URL_SAFE or Base64.NO_WRAP), Charsets.UTF_8)).optString("sub")
        }.getOrDefault("")
        return AppSession(claims.ifBlank { "cognito-user" }, HouseholdRole.OWNER, accessToken = idToken)
    }

    override fun affirmAgeRequirement() = Unit

    @Synchronized
    fun signOut() { prefs.edit().clear().apply() }

    private fun refreshTokens() {
        val refresh = getSecret("refresh_token") ?: return
        val body = FormBody.Builder().add("grant_type", "refresh_token").add("client_id", clientId).add("refresh_token", refresh).build()
        val response = http.newCall(Request.Builder().url("$domain/oauth2/token").post(body).build()).execute()
        response.use {
            check(it.isSuccessful) { "Your sign-in expired. Sign in again to continue." }
            saveTokens(JSONObject(it.body?.string().orEmpty()), refresh)
        }
    }

    private fun saveTokens(json: JSONObject, oldRefresh: String?) {
        val access = json.optString("access_token").takeIf(String::isNotBlank) ?: error("Cognito returned no access token.")
        val id = json.optString("id_token").takeIf(String::isNotBlank) ?: error("Cognito returned no ID token.")
        putSecret("access_token", access)
        putSecret("id_token", id)
        putSecret("refresh_token", json.optString("refresh_token").takeIf(String::isNotBlank) ?: oldRefresh ?: error("Cognito returned no refresh token."))
        prefs.edit().putLong("expires_at", System.currentTimeMillis() / 1000 + json.optLong("expires_in", 3600)).apply()
    }

    private fun putSecret(name: String, value: String) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, key()) }
        val encrypted = Base64.encodeToString(cipher.iv + cipher.doFinal(value.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP)
        prefs.edit().putString(name, encrypted).apply()
    }

    private fun getSecret(name: String): String? {
        val stored = prefs.getString(name, null) ?: return null
        return runCatching {
            val bytes = Base64.decode(stored, Base64.NO_WRAP)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, bytes.copyOfRange(0, 12)))
            String(cipher.doFinal(bytes.copyOfRange(12, bytes.size)), Charsets.UTF_8)
        }.getOrNull()
    }

    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").run {
            init(KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
            generateKey()
        }
    }

    private fun randomUrlSafe(size: Int): String = ByteArray(size).also(SecureRandom()::nextBytes)
        .let { Base64.encodeToString(it, Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING) }

    private companion object { const val KEY_ALIAS = "knock-knock-cognito-tokens" }
}
