package com.knockknock.core.privacy

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey

/** Keys never leave Android Keystore; no credentials or keys are stored in preferences. */
internal object DeviceKeyStore {
    @Synchronized
    fun getOrCreate(alias: String): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(alias, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .setRandomizedEncryptionRequired(true)
                .build(),
        )
        return generator.generateKey()
    }

    @Synchronized
    fun delete(alias: String) {
        KeyStore.getInstance("AndroidKeyStore").apply { load(null); deleteEntry(alias) }
    }
}

/** Irreversibly removes local encrypted journal material by deleting its wrapping key. */
fun destroyPrivateJournalMaterial(context: android.content.Context) {
    DeviceKeyStore.delete("knock-knock-vault-v1")
    context.deleteDatabase("knock-knock-private.db")
    context.noBackupFilesDir.resolve("private-vault").deleteRecursively()
}
