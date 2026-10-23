package com.knockknock.core.privacy

import android.content.Context
import android.util.AtomicFile
import java.io.File
import java.security.MessageDigest
import java.security.SecureRandom

/** Only encrypted bytes reach disk; logical identifiers are bound into the authentication tag. */
class EncryptedFileVault(context: Context) {
    private val directory = File(context.noBackupFilesDir, "private-vault").apply { mkdirs() }
    private val cipher = AuthenticatedCipher(DeviceKeyStore.getOrCreate("knock-knock-vault-v1"))

    @Synchronized
    fun put(id: String, bytes: ByteArray) {
        val encrypted = cipher.encrypt(id, bytes)
        val target = AtomicFile(path(id))
        val stream = target.startWrite()
        try {
            stream.write(encrypted)
            target.finishWrite(stream)
        } catch (error: Exception) {
            target.failWrite(stream)
            throw error
        }
    }

    @Synchronized
    fun get(id: String): ByteArray = cipher.decrypt(id, AtomicFile(path(id)).readFully())

    @Synchronized
    fun delete(id: String) = AtomicFile(path(id)).delete()

    @Synchronized
    fun exists(id: String): Boolean = path(id).exists()

    private fun path(id: String): File {
        require(id.isNotBlank() && id.length <= 512)
        val digest = MessageDigest.getInstance("SHA-256").digest(id.toByteArray(Charsets.UTF_8))
        val filename = digest.joinToString("") { "%02x".format(it) }
        return File(directory, "$filename.kkv")
    }
}

/** Random SQLCipher secret, persisted only as Keystore-wrapped ciphertext. */
class DatabasePassphrase(context: Context) {
    private val vault = EncryptedFileVault(context)

    fun loadOrCreate(): ByteArray = synchronized(creationLock) {
        val id = "internal/sqlcipher-passphrase-v1"
        if (vault.exists(id)) return@synchronized vault.get(id)
        // ASCII avoids ambiguity between SQLCipher's byte[] and String handling.
        val random = ByteArray(32).also { SecureRandom().nextBytes(it) }
        val secret = random.joinToString("") { "%02x".format(it) }.toByteArray(Charsets.US_ASCII)
        random.fill(0)
        vault.put(id, secret)
        secret
    }

    private companion object { val creationLock = Any() }
}
