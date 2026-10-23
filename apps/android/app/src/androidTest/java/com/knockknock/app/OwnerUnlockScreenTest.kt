package com.knockknock.app

import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.knockknock.core.ui.KnockKnockTheme
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class OwnerUnlockScreenTest {
    @get:Rule val compose = createComposeRule()
    @Test fun insecureTabletCannotOpenJournal() {
        compose.setContent { KnockKnockTheme { OwnerUnlockScreen({}, secureDevice = false) } }
        compose.onNodeWithText("Unlock private journal").assertIsNotEnabled()
    }
    @Test fun secureTabletRequestsCredentialBeforeRecords() {
        var requests = 0
        compose.setContent { KnockKnockTheme { OwnerUnlockScreen({ requests++ }, secureDevice = true) } }
        compose.onNodeWithText("Unlock private journal").assertIsEnabled().performClick()
        compose.runOnIdle { assertEquals(1, requests) }
    }
}
