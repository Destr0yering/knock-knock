package com.knockknock.core.privacy

import android.app.KeyguardManager
import android.content.Context
import android.content.Intent
import android.os.SystemClock

/** UI authorization gate: call confirmUnlock ONLY after RESULT_OK from the credential screen. */
class OwnerUnlock(private val context: Context) {
    private var expiresAt = 0L
    val isUnlocked: Boolean get() = SystemClock.elapsedRealtime() < expiresAt

    @Suppress("DEPRECATION")
    fun credentialIntent(): Intent? {
        val keyguard = context.getSystemService(KeyguardManager::class.java)
        if (!keyguard.isDeviceSecure) return null
        return keyguard.createConfirmDeviceCredentialIntent("Unlock Knock Knock", "Access private visitor records")
    }

    fun confirmUnlock() { expiresAt = SystemClock.elapsedRealtime() + 300_000 }
    fun lock() { expiresAt = 0L }
    fun requireUnlocked() { check(isUnlocked) { "Device-owner unlock required" } }
}
