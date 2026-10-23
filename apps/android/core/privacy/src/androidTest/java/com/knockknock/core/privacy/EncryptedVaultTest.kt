package com.knockknock.core.privacy

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.util.UUID
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class EncryptedVaultTest {
    @Test fun vaultReopensWithKeystoreKeyAndDeletesRecord() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val id = "test/${UUID.randomUUID()}"
        val plaintext = "unique-private-image-bytes".toByteArray()
        val first = EncryptedFileVault(context)
        try {
            first.put(id, plaintext)
            assertArrayEquals(plaintext, EncryptedFileVault(context).get(id))
            first.delete(id)
            assertFalse(first.exists(id))
        } finally { first.delete(id) }
    }
}
