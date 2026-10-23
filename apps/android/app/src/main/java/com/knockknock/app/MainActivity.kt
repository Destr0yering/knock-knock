package com.knockknock.app

import android.Manifest
import android.app.KeyguardManager
import android.app.Activity
import android.view.WindowManager
import androidx.activity.result.contract.ActivityResultContracts
import android.content.pm.PackageManager
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.knockknock.core.model.ConfidenceBand
import com.knockknock.core.model.VisitDeepLink
import com.knockknock.core.model.VisitorTrustPolicy
import com.knockknock.core.ui.KnockKnockTheme
import com.knockknock.feature.review.ApprovalRoute
import com.knockknock.feature.review.ApprovalViewModel
import com.knockknock.feature.review.ReviewViewModel
import com.knockknock.feature.review.VisitReviewRoute
import com.knockknock.feature.timeline.TimelineRoute
import com.knockknock.feature.timeline.TimelineViewModel
import java.time.Instant
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {
    private var ownerUnlocked by mutableStateOf(false)
    private var pendingImage by mutableStateOf<android.net.Uri?>(null)
    private var pendingCloudVisitId by mutableStateOf<String?>(null)
    private var signedIn by mutableStateOf(false)
    private var authMessage by mutableStateOf("Not signed in to Knock Knock.")
    private val importImage = registerForActivityResult(ActivityResultContracts.GetContent()) { pendingImage = it }
    private val unlockOwner = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) {
        ownerUnlocked = it.resultCode == Activity.RESULT_OK
        if (ownerUnlocked) (application as KnockKnockApplication).container.ownerUnlock.confirmUnlock()
    }
    private lateinit var notifications: VisitorNotificationGateway
    private val testerNoticePreferences by lazy {
        getSharedPreferences("tester-notice", MODE_PRIVATE)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)
        enableEdgeToEdge()
        notifications = LocalVisitorNotificationGateway(this)
        val container = (application as KnockKnockApplication).container
        signedIn = container.sessionProvider.hasStoredSession()
        authMessage = if (signedIn) "Signed in to Knock Knock." else "Not signed in to Knock Knock."
        val initialCallback = intent?.data?.takeIf { it.scheme == "knockknock" && it.host == "auth" }
        if (initialCallback != null) {
            setIntent(Intent(this, MainActivity::class.java))
            handleAuthCallback(initialCallback, container)
        }
        val noticeAccepted = testerNoticePreferences.getBoolean("accepted_v1", false)
        if (noticeAccepted) container.sessionProvider.affirmAgeRequirement()
        val initialVisitId = VisitDeepLink.parse(intent?.dataString)
        pendingCloudVisitId = initialVisitId
        setContent {
            KnockKnockTheme {
                androidx.compose.runtime.LaunchedEffect(ownerUnlocked) {
                    if (ownerUnlocked) {
                        kotlinx.coroutines.delay(300_000)
                        container.lockPrivateSession()
                        ownerUnlocked = false
                    }
                }
                if (!ownerUnlocked) {
                    OwnerUnlockScreen(onUnlock = {
                        val keyguard = getSystemService(KeyguardManager::class.java)
                        @Suppress("DEPRECATION")
                        val credential = keyguard.createConfirmDeviceCredentialIntent("Knock Knock", "Unlock your private visitor journal")
                        if (keyguard.isDeviceSecure && credential != null) unlockOwner.launch(credential)
                    }, secureDevice = getSystemService(KeyguardManager::class.java).isDeviceSecure)
                } else {
                var demo by remember { mutableStateOf(false) }
                if (!demo) {
                    PrivateJournalRoute(container = container, onOpenDemo = { demo = true },
                        signedIn = signedIn, authMessage = authMessage,
                        onImport = { importImage.launch("image/*") }, pendingImage = pendingImage,
                        cloudVisitId = pendingCloudVisitId,
                        onCloudVisitConsumed = { pendingCloudVisitId = null },
                        onImageConsumed = { pendingImage = null }, onEnableAlerts = {
                            if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                                requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 42)
                            } else {
                                FcmPushCoordinator(this).syncToken { message ->
                                    runOnUiThread { android.widget.Toast.makeText(this, message, android.widget.Toast.LENGTH_LONG).show() }
                                }
                            }
                        }, onSignIn = {
                            runCatching { container.sessionProvider.authorizationUri() }
                                .onSuccess {
                                    authMessage = "Complete Knock Knock sign-in in the hosted page."
                                    startActivity(Intent(Intent.ACTION_VIEW, it))
                                }
                                .onFailure { android.widget.Toast.makeText(this, it.message ?: "Sign-in is not configured.", android.widget.Toast.LENGTH_LONG).show() }
                        }, onSignOut = {
                            container.sessionProvider.signOut()
                            signedIn = false
                            authMessage = "Signed out on this device."
                        }, onAccountDeleted = { localDataCleared ->
                            signedIn = false
                            authMessage = if (localDataCleared) "Account deletion requested. Sign-in credentials and local records were removed." else "Account deletion requested. Clear Knock Knock app storage in Android Settings to finish local cleanup."
                            ownerUnlocked = false
                        }, onOpenRingPortal = {
                            val ringAppIntent = packageManager.getLaunchIntentForPackage("com.ringapp")
                            if (ringAppIntent != null) {
                                startActivity(ringAppIntent)
                            } else {
                                startActivity(
                                    Intent(
                                        Intent.ACTION_VIEW,
                                        Uri.parse("https://play.google.com/store/apps/details?id=com.ringapp"),
                                    ),
                                )
                            }
                        })
                } else {
                androidx.activity.compose.BackHandler { demo = false }
                androidx.compose.foundation.layout.Box {
                KnockKnockNavHost(
                    container = container,
                    initialVisitId = initialVisitId,
                    onTestAlert = ::postTestAlert,
                    noticeAccepted = noticeAccepted,
                    onAcceptNotice = {
                        container.sessionProvider.affirmAgeRequirement()
                        testerNoticePreferences.edit()
                            .putBoolean("accepted_v1", true)
                            .putString("accepted_at", Instant.now().toString())
                            .putString("notice_version", "2026-10-05-v1")
                            .apply()
                    },
                    authMessage = authMessage,
                    onSignIn = {
                        runCatching { container.sessionProvider.authorizationUri() }
                            .onSuccess { startActivity(Intent(Intent.ACTION_VIEW, it)) }
                            .onFailure { authMessage = it.message ?: "Cognito sign-in is not configured." }
                    },
                )
                }
                }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        val container = (application as KnockKnockApplication).container
        val callback = intent.data?.takeIf { it.scheme == "knockknock" && it.host == "auth" }
        if (callback != null) {
            setIntent(Intent(this, MainActivity::class.java))
            handleAuthCallback(callback, container)
        } else {
            pendingCloudVisitId = VisitDeepLink.parse(intent.dataString)
            setIntent(intent)
        }
    }

    private fun handleAuthCallback(uri: Uri?, container: AppContainer) {
        if (uri == null) return
        lifecycleScope.launch {
            authMessage = "Completing secure sign-in…"
            authMessage = runCatching {
                withContext(Dispatchers.IO) { container.sessionProvider.completeCallback(uri) }
                "Signed in securely with Cognito."
            }.getOrElse { it.message ?: "Sign-in could not be completed. Start again." }
            signedIn = container.sessionProvider.hasStoredSession()
            if (!signedIn && authMessage == "Signed in securely with Cognito.") {
                authMessage = "Sign-in did not persist. Start again."
            }
        }
    }

    override fun onStop() {
        ownerUnlocked = false
        (application as KnockKnockApplication).container.lockPrivateSession()
        super.onStop()
    }

    private fun postTestAlert() {
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 41)
            return
        }
        notifications.showVisitAlert(
            visitId = "offline-demo-group-arrival",
            alert = VisitorTrustPolicy.alert(
                peopleCount = 3,
                learningDay = 1,
                candidateName = "Morgan",
                confidenceBand = ConfidenceBand.HIGH,
            ),
        )
    }
}

@Composable
internal fun OwnerUnlockScreen(onUnlock: () -> Unit, secureDevice: Boolean) {
    Scaffold { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text("Knock Knock", style = MaterialTheme.typography.headlineLarge)
            Text("Your private visitor journal")
            Text(if (secureDevice) "Unlock with the tablet owner's device credential to access records." else "Set a screen lock PIN or password in Android settings to use the private journal.")
            Button(onClick = onUnlock, enabled = secureDevice) { Text("Unlock private journal") }
        }
    }
}

@Composable
private fun KnockKnockNavHost(
    container: AppContainer,
    initialVisitId: String?,
    onTestAlert: () -> Unit,
    noticeAccepted: Boolean,
    onAcceptNotice: () -> Unit,
    authMessage: String,
    onSignIn: () -> Unit,
) {
    var accepted by remember { mutableStateOf(noticeAccepted) }
    if (!accepted) {
        TesterSafetyNotice(onAccept = {
            onAcceptNotice()
            accepted = true
        })
        return
    }
    val navController = rememberNavController()
    val start = initialVisitId?.let { "visit/$it" } ?: "timeline"
    Column(Modifier.fillMaxSize()) {
    Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(authMessage, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodySmall)
        Button(onClick = onSignIn) { Text("Sign in") }
    }
    NavHost(navController = navController, startDestination = start, modifier = Modifier.weight(1f)) {
        composable("timeline") {
            val timelineViewModel: TimelineViewModel = viewModel(
                factory = container.timelineViewModelFactory,
            )
            TimelineRoute(
                viewModel = timelineViewModel,
                onVisitClick = { visitId -> navController.navigate("visit/$visitId") },
                onTestAlert = onTestAlert,
            )
        }
        composable(
            route = "visit/{visitId}",
            arguments = listOf(navArgument("visitId") { type = NavType.StringType }),
        ) { entry ->
            val visitId = entry.arguments?.getString("visitId").orEmpty()
            val reviewViewModel: ReviewViewModel = viewModel(
                key = "review-$visitId",
                factory = container.reviewViewModelFactory(visitId),
            )
            VisitReviewRoute(
                viewModel = reviewViewModel,
                onBack = {
                    if (!navController.popBackStack()) navController.navigate("timeline")
                },
                onOpenApprovals = { navController.navigate("approvals") },
            )
        }
        composable("approvals") {
            val approvalViewModel: ApprovalViewModel = viewModel(
                factory = container.approvalViewModelFactory,
            )
            ApprovalRoute(approvalViewModel, onBack = navController::popBackStack)
        }
    }
    }
}

@Composable
private fun TesterSafetyNotice(onAccept: () -> Unit) {
    var is13OrOlder by remember { mutableStateOf(false) }
    var syntheticOnly by remember { mutableStateOf(false) }

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 22.dp, vertical = 24.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text("Before you try Knock Knock", style = MaterialTheme.typography.headlineSmall)
            Text(
                "This build is a private demo. Do not connect a personal Ring account or use real visitor images until the public tester notice, deletion process, and live credentials are ready.",
                style = MaterialTheme.typography.bodyLarge,
            )

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier.padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Text("What this demo does", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "You can browse generated demo visitor images, test alerts, review visit cards, " +
                            "and try profile labeling. The bundled examples are synthetic. Ring linking uses " +
                            "a separate hosted consent flow.",
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    Text("Data in this build", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "Demo visit labels, profile edits, and settings are stored in this app's private " +
                            "local database/preferences. This build has no real-person enrollment flow. " +
                            "Do not add actual visitor photos, names, or identifying details. Removing app " +
                            "data from Android clears the local demo cache.",
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    Text("Before any real-camera pilot", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "We will provide a separate privacy policy, tester terms, face-processing notice, " +
                            "consent choices, Ring unlinking instructions, and data-request process before " +
                            "asking testers to connect Ring or use real people's images.",
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }

            ConsentAcknowledgement(
                checked = is13OrOlder,
                onCheckedChange = { is13OrOlder = it },
                label = "I confirm that I am at least 13 years old.",
            )
            ConsentAcknowledgement(
                checked = syntheticOnly,
                onCheckedChange = { syntheticOnly = it },
                label = "I understand this is a synthetic-data demo and will not enter real visitor information.",
            )

            Spacer(Modifier.height(2.dp))
            Button(
                onClick = onAccept,
                enabled = is13OrOlder && syntheticOnly,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Continue to demo")
            }
            Text(
                "This acknowledgement is for the synthetic demo only. It is not consent to biometric " +
                    "processing or a substitute for the future tester documents.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun ConsentAcknowledgement(
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    label: String,
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Checkbox(checked = checked, onCheckedChange = onCheckedChange)
        Text(label, style = MaterialTheme.typography.bodyMedium)
    }
}
