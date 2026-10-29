package com.knockknock.core.privacy

import java.nio.ByteBuffer
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Ciphertext format: magic/version + random 96-bit nonce + ciphertext and 128-bit tag. */
class AuthenticatedCipher(private val key: SecretKey) {
    fun encrypt(id: String, plaintext: ByteArray): ByteArray {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key)
        cipher.updateAAD(associatedData(id))
        val encrypted = cipher.doFinal(plaintext)
        return MAGIC + cipher.iv + encrypted
    }

    fun decrypt(id: String, encrypted: ByteArray): ByteArray {
        require(encrypted.size >= MAGIC.size + NONCE_SIZE + 16) { "Invalid encrypted record" }
        require(encrypted.copyOfRange(0, MAGIC.size).contentEquals(MAGIC)) { "Unknown vault format" }
        val nonce = encrypted.copyOfRange(MAGIC.size, MAGIC.size + NONCE_SIZE)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, nonce))
        cipher.updateAAD(associatedData(id))
        return cipher.doFinal(encrypted, MAGIC.size + NONCE_SIZE, encrypted.size - MAGIC.size - NONCE_SIZE)
    }

    private fun associatedData(id: String): ByteArray {
        require(id.isNotBlank())
        val bytes = id.toByteArray(Charsets.UTF_8)
        return MAGIC + ByteBuffer.allocate(4).putInt(bytes.size).array() + bytes
    }

    private companion object {
        val MAGIC = byteArrayOf(75, 75, 86, 1)
        const val NONCE_SIZE = 12
    }
}
