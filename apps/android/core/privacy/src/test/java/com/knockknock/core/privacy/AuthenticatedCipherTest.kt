package com.knockknock.core.privacy

import javax.crypto.AEADBadTagException
import javax.crypto.KeyGenerator
import org.junit.Assert.*
import org.junit.Test

class AuthenticatedCipherTest {
    private val cipher = AuthenticatedCipher(KeyGenerator.getInstance("AES").apply { init(256) }.generateKey())

    @Test fun ciphertextHidesContentAndUsesFreshNonces() {
        val plain = "private visitor profile".toByteArray()
        val first = cipher.encrypt("photo/1", plain)
        val second = cipher.encrypt("photo/1", plain)
        assertFalse(first.contentEquals(second))
        assertFalse(String(first).contains("private visitor"))
        assertArrayEquals(plain, cipher.decrypt("photo/1", first))
    }

    @Test(expected = AEADBadTagException::class)
    fun cannotSwapRecords() { cipher.decrypt("photo/2", cipher.encrypt("photo/1", byteArrayOf(1))) }

    @Test(expected = AEADBadTagException::class)
    fun rejectsTampering() {
        val bytes = cipher.encrypt("photo/1", byteArrayOf(1))
        bytes[bytes.lastIndex] = (bytes.last().toInt() xor 1).toByte()
        cipher.decrypt("photo/1", bytes)
    }
}
