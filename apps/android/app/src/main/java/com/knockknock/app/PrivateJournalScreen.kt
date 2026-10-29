package com.knockknock.app

import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.graphics.Bitmap
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Groups
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.Home
import androidx.compose.material.icons.rounded.Lock
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.knockknock.core.camera.ImageOnlyInput
import com.knockknock.core.database.PersonEntity
import com.knockknock.core.database.PrivateFaceInput
import com.knockknock.core.database.ProfileEntity
import com.knockknock.core.database.PrivateRecordsRepository
import com.knockknock.core.database.RetentionSettings
import com.knockknock.core.evidence.RecordExporter
import com.knockknock.core.vision.FaceReference
import com.knockknock.core.vision.OpenCvLocalFaceEngine
import com.knockknock.core.vision.SimilarityMatcher
import com.knockknock.core.ui.StatusPill
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.MediaType.Companion.toMediaType
import org.json.JSONObject

/** Local private journal with separate, explicit consent for cloud push delivery. */
@Composable
internal fun PrivateJournalRoute(
    container: AppContainer,
    onOpenDemo: () -> Unit,
    onImport: () -> Unit,
    pendingImage: Uri?,
    cloudVisitId: String?,
    onCloudVisitConsumed: () -> Unit,
    onImageConsumed: () -> Unit,
    signedIn: Boolean,
    authMessage: String,
    onEnableAlerts: () -> Unit,
    onSignIn: () -> Unit,
    onSignOut: () -> Unit,
    onOpenRingPortal: () -> Unit,
    onAccountDeleted: (Boolean) -> Unit,
) {
    val context = LocalContext.current
    val records = remember { container.privateRecords }
    val visitFlow = remember(records) { records.observeVisits() }
    val profileFlow = remember(records) { records.observeProfiles() }
    val auditFlow = remember(records) { records.observeAudit() }
    val visits by visitFlow.collectAsState(initial = emptyList())
    val profiles by profileFlow.collectAsState(initial = emptyList())
    val audit by auditFlow.collectAsState(initial = emptyList())
    val scope = rememberCoroutineScope()
    var status by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    val preferences = remember { context.getSharedPreferences("private-journal-notice", 0) }
    val pushPreferences = remember { context.getSharedPreferences("cloud-alert-consent", 0) }
    var consent by remember { mutableStateOf(preferences.getBoolean("accepted_v1", false)) }
    var pushConsent by remember { mutableStateOf(pushPreferences.getBoolean("accepted_v1", false)) }
    var age by remember { mutableStateOf(false) }
    var lawful by remember { mutableStateOf(false) }
    var exportWarning by remember { mutableStateOf(false) }
    var ringLinkAcknowledged by remember { mutableStateOf(false) }
    var showDataHelp by remember { mutableStateOf(false) }
    var showDeleteAccount by remember { mutableStateOf(false) }
    var deleteConfirmation by remember { mutableStateOf("") }
    var deletionStatus by remember { mutableStateOf<String?>(null) }
    var selectedRingVisitId by remember { mutableStateOf<String?>(null) }
    var ringVisits by remember { mutableStateOf<List<RingVisitHistoryItem>>(emptyList()) }
    var ringHistoryStatus by remember { mutableStateOf("Sign in and refresh to load Ring events.") }
    var ringHistoryLoading by remember { mutableStateOf(false) }
    var visitPage by remember { mutableStateOf(0) }
    var selectedTab by remember { mutableIntStateOf(0) }
    var retention by remember { mutableStateOf(RetentionSettings()) }
    var photoDays by remember { mutableStateOf("30") }
    var logDays by remember { mutableStateOf("365") }
    fun perform(block: suspend () -> String) {
        if (busy) return
        scope.launch {
            busy = true
            status = runCatching { withContext(Dispatchers.IO) { block() } }
                .getOrElse { "Operation could not complete. Unlock again if the session expired. ${it.message.orEmpty()}" }
            busy = false
        }
    }
    fun refreshRingVisits() {
        if (!signedIn || ringHistoryLoading) return
        scope.launch {
            ringHistoryLoading = true
            runCatching {
                withContext(Dispatchers.IO) { fetchRingVisitHistory(container) }
            }.onSuccess { result ->
                ringVisits = result
                ringHistoryStatus = if (result.isEmpty()) {
                    "No Ring visits are available for this account yet."
                } else {
                    "${result.size} recent Ring visit(s). Tap one to review its still image."
                }
            }.onFailure {
                ringHistoryStatus = "Ring history is unavailable. Check sign-in and connection."
            }
            ringHistoryLoading = false
        }
    }
    LaunchedEffect(signedIn) {
        if (signedIn) refreshRingVisits() else {
            ringVisits = emptyList()
            ringHistoryStatus = "Sign in and refresh to load Ring events."
        }
    }
    LaunchedEffect(records) {
        runCatching { withContext(Dispatchers.IO) { records.recordAccess(); records.applyRetention(); records.retentionSettings() } }
            .onSuccess { retention = it; photoDays = it.photoDays.toString(); logDays = it.logDays.toString() }
            .onFailure { status = "Retention check needs an unlocked session." }
    }
    LaunchedEffect(context) {
        while (true) {
            runCatching { withContext(Dispatchers.IO) { AccountDeletionClient.status(context) } }
                .getOrNull()?.let { deletionStatus = it }
            if (deletionStatus?.startsWith("Account deletion is complete") == true) break
            kotlinx.coroutines.delay(10_000)
        }
    }
    val activeCloudVisitId = cloudVisitId ?: selectedRingVisitId
    if (activeCloudVisitId != null) {
        CloudRingVisitReview(container, activeCloudVisitId, onClose = {
            if (cloudVisitId != null) onCloudVisitConsumed() else selectedRingVisitId = null
        })
    }
    LaunchedEffect(pendingImage, consent) {
        if (pendingImage == null || !consent) return@LaunchedEffect
        busy = true
        status = "Analyzing image on this tablet…"
        status = runCatching {
            withContext(Dispatchers.IO) {
                val bitmap = ImageOnlyInput(context).read(pendingImage)
                val faces = try { OpenCvLocalFaceEngine(context).analyze(bitmap) } finally { bitmap.recycle() }
                val references = records.references().map { FaceReference(it.profileId, it.embedding) }
                try {
                    val visitId = records.importVisit(faces.map { PrivateFaceInput(it.jpeg, it.embedding, it.confidence.toDouble()) })
                    val people = records.personIdsForVisit(visitId)
                    faces.forEachIndexed { index, face ->
                        SimilarityMatcher.suggest(face.embedding, references)?.let { suggestion ->
                            records.setSuggestion(people[index], suggestion.profileId, suggestion.similarity)
                        }
                    }
                    LocalVisitorNotificationGateway(context).showVisitAlert(visitId,
                        com.knockknock.core.model.VisitorAlert("Visitor event", "Open the private journal to review.", false))
                    if (faces.isEmpty()) "No clear face detected. Visit saved; number of people is unknown."
                    else "${faces.size} face(s) detected. Review each person; matches are suggestions only."
                } finally {
                    faces.forEach { it.embedding.fill(0f); it.jpeg.fill(0) }
                    references.forEach { it.embedding.fill(0f) }
                }
            }
        }.getOrElse { "Image import failed: ${it.message.orEmpty()}" }
        busy = false
        onImageConsumed()
    }
    if (exportWarning) {
        AlertDialog(onDismissRequest = { exportWarning = false },
            title = { Text("Share decrypted records?") },
            text = { Text("This export contains readable records and face images. The app you choose can retain them. Local share ZIPs become eligible for cleanup after one hour; Android may delay background cleanup. The local database and vault remain encrypted. Hashes help check file integrity; they do not prove identity or legal admissibility.") },
            dismissButton = { TextButton(onClick = { exportWarning = false }) { Text("Cancel") } },
            confirmButton = { TextButton(onClick = {
                exportWarning = false
                scope.launch {
                    busy = true
                    runCatching {
                        val file = withContext(Dispatchers.IO) {
                            val manifest = JSONObject(String(records.exportRecords(), Charsets.UTF_8))
                            val images = mutableMapOf<String, ByteArray>()
                            try {
                                visits.flatMap { it.people }.forEach { person ->
                                    records.faceImage(person.id)?.let { images["face-${person.id}.jpg"] = it }
                                }
                                RecordExporter(context).export(manifest, images)
                            } finally { images.values.forEach { it.fill(0) } }
                        }
                        val uri = FileProvider.getUriForFile(context, "${context.packageName}.exports", file)
                        context.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
                            type = "application/zip"
                            putExtra(Intent.EXTRA_STREAM, uri)
                            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                            clipData = android.content.ClipData.newRawUri("DoorMemo records", uri)
                        }, "Share private records"))
                    }.onFailure { status = "Export failed: ${it.message.orEmpty()}" }
                    busy = false
                }
            }) { Text("Create export") } },
        )
    }
    if (showDataHelp) {
        AlertDialog(
            onDismissRequest = { showDataHelp = false },
            title = { Text("Remove DoorMemo's Ring access") },
            text = { Text("Ring's one-way Appstore linking flow requires you to remove the app in Ring: open Ring Appstore > My Apps > Knock Knock (the current staging listing) > Remove App. Ring then invalidates the app tokens and stops its webhooks. Deleting your DoorMemo account also removes cloud records and local tablet data, but Ring access must be removed in Ring separately. Ring may retain operational data under its own terms.") },
            confirmButton = { TextButton(onClick = { showDataHelp = false }) { Text("Close") } },
        )
    }
    if (showDeleteAccount) {
        AlertDialog(
            onDismissRequest = { if (!busy) showDeleteAccount = false },
            title = { Text("Delete account and data?") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("This stops Ring event processing, queues deletion of your DoorMemo cloud records, images, Ring tokens, push tokens, and isolated face collection, deletes your DoorMemo sign-in account, and erases this tablet's local data. AWS backups and short-lived operational logs age out under their retention windows. Remove the Knock Knock staging listing separately from Ring Appstore > My Apps to revoke Ring's one-way link. This cannot be undone.")
                    OutlinedTextField(value = deleteConfirmation, onValueChange = { deleteConfirmation = it }, label = { Text("Type DELETE to confirm") }, singleLine = true)
                }
            },
            dismissButton = { TextButton(onClick = { showDeleteAccount = false }, enabled = !busy) { Text("Cancel") } },
            confirmButton = {
                TextButton(enabled = !busy && deleteConfirmation == "DELETE", onClick = {
                    scope.launch {
                        busy = true
                        status = "Submitting account deletion and erasing this tablet's local data."
                        val outcome = runCatching {
                            withContext(Dispatchers.IO) { AccountDeletionClient.requestAndErase(context, container) }
                        }
                        busy = false
                        showDeleteAccount = false
                        deleteConfirmation = ""
                        outcome.onSuccess {
                            deletionStatus = "Deletion is queued. Your receipt is saved on this tablet."
                            status = if (it.localDataCleared) "Deletion request ${it.requestId} was accepted." else "Deletion request ${it.requestId} was accepted, but local cleanup was incomplete. Use Android Settings > Apps > DoorMemo > Storage > Clear data."
                            onAccountDeleted(it.localDataCleared)
                        }.onFailure { status = "Deletion was not accepted; local data was not cleared. ${it.message.orEmpty()}" }
                    }
                }) { Text("Delete my account") }
            },
        )
    }
    Scaffold(
        bottomBar = {
            NavigationBar {
                NavigationBarItem(selectedTab == 0, { selectedTab = 0 }, icon = { Icon(Icons.Rounded.Home, null) }, label = { Text("Door") })
                NavigationBarItem(selectedTab == 1, { selectedTab = 1 }, icon = { Icon(Icons.Rounded.History, null) }, label = { Text("Activity") })
                NavigationBarItem(selectedTab == 2, { selectedTab = 2 }, icon = { Icon(Icons.Rounded.Groups, null) }, label = { Text("People") })
                NavigationBarItem(selectedTab == 3, { selectedTab = 3 }, icon = { Icon(Icons.Rounded.Lock, null) }, label = { Text("Privacy") })
            }
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(horizontal = 20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(Modifier.fillMaxWidth().padding(top = 18.dp), horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text("DOORMEMO", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
                    Text(when (selectedTab) { 0 -> "Your front door"; 1 -> "Door activity"; 2 -> "People you know"; else -> "Privacy & controls" },
                        style = MaterialTheme.typography.headlineSmall)
                }
                StatusPill(if (signedIn) "Account active" else "Sign in")
            }
            if (selectedTab == 0) {
                DoorHomeCard(
                    ringStatus = if (!signedIn) "Sign in to check the Ring event feed" else ringHistoryStatus,
                    eventCount = ringVisits.size,
                    localCount = visits.size,
                    refreshing = ringHistoryLoading,
                    onRefresh = { refreshRingVisits() },
                    onActivity = { selectedTab = 1 },
                    onPrivacy = { selectedTab = 3 },
                )
                Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    Text("Latest from Ring", modifier = Modifier.weight(1f), style = MaterialTheme.typography.titleLarge)
                    TextButton(onClick = { selectedTab = 1 }) { Text("See activity") }
                }
                if (ringVisits.isEmpty()) {
                    Text("Your Ring events will appear here after sign-in and a successful refresh.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant)
                } else ringVisits.take(3).forEach { visit ->
                    RingVisitRow(visit, busy, selectedRingVisitId != null) { selectedRingVisitId = visit.visitId }
                }
                Card {
                    Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("A more thoughtful way to remember a visit", style = MaterialTheme.typography.titleMedium)
                        Text("Review still images yourself. Any identity suggestion stays a suggestion until you confirm it.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant)
                        TextButton(onClick = onOpenDemo, enabled = !busy) { Text("Explore the synthetic demo") }
                    }
                }
            }
            if (selectedTab == 3) {
            Card {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("DoorMemo account", style = MaterialTheme.typography.titleMedium)
                    Text(authMessage)
                    deletionStatus?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                    TextButton(onClick = {
                        val url = BuildConfig.API_BASE_URL.trimEnd('/') + "/privacy"
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    }) { Text("Read the privacy notice") }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        if (signedIn) {
                            OutlinedButton(onClick = onSignOut, enabled = !busy) { Text("Sign out on this device") }
                        } else {
                            Button(onClick = onSignIn, enabled = !busy) { Text("Sign in") }
                        }
                    }
                }
            }
            Card {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Ring test account", style = MaterialTheme.typography.titleMedium)
                    Text("Staging access is enabled for this tester. Start linking in the Ring mobile app: open Appstore, find DoorMemo, choose the Ring device or devices, and confirm. Ring will then open DoorMemo's hosted consent flow. This app never asks for your Ring password. DoorMemo processes still snapshots only, but Ring may present broader app-level camera, video, device, or account permissions. Review those permissions before continuing.")
                    Text("Ring snapshots and face analysis go to AWS in US East (N. Virginia). Unsaved images expire after 30 days and visit records after 365 days. Account deletion stops processing and removes active cloud and local account data; AWS backup and operational log copies expire under their retention windows. Remove the Knock Knock staging listing separately from Ring Appstore > My Apps to revoke Ring's one-way link. Use only a Ring account you control, notify household members, and test with consenting adults. Do not include minors, neighbors, or passersby.", style = MaterialTheme.typography.bodySmall)
                    Row {
                        Checkbox(checked = ringLinkAcknowledged, onCheckedChange = { ringLinkAcknowledged = it })
                        Text("I am an adult account owner authorized to connect this Ring account, and I understand these processing and deletion limits.")
                    }
                    Button(onClick = {
                        context.getSharedPreferences("ring-link-notice", 0).edit()
                            .putBoolean("accepted_v1", true)
                            .putString("accepted_at", java.time.Instant.now().toString())
                            .putString("notice_version", "2026-10-21-v1")
                            .apply()
                        onOpenRingPortal()
                    }, enabled = signedIn && ringLinkAcknowledged && !busy) {
                        Text("Open Ring app")
                    }
                    if (!signedIn) Text("Sign in to DoorMemo before starting the Ring test-account link.", style = MaterialTheme.typography.bodySmall)
                    TextButton(onClick = { showDataHelp = true }) { Text("Unlink Ring and remove data") }
                    TextButton(onClick = { showDeleteAccount = true }) { Text("Delete DoorMemo account and data") }
                    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                        Text("Recent Ring events", modifier = Modifier.weight(1f), style = MaterialTheme.typography.titleSmall)
                        TextButton(onClick = { refreshRingVisits() }, enabled = signedIn && !ringHistoryLoading) {
                            Text(if (ringHistoryLoading) "Loading…" else "Refresh")
                        }
                    }
                    Text(ringHistoryStatus, style = MaterialTheme.typography.bodySmall)
                    ringVisits.forEach { visit ->
                        OutlinedButton(
                            onClick = { selectedRingVisitId = visit.visitId },
                            enabled = !busy && selectedRingVisitId == null && visit.snapshotAvailable,
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Text(if (visit.snapshotAvailable) {
                                "${visit.occurredAt} · ${visit.personCount} detected · ${visit.eventType} · ${visit.status}"
                            } else {
                                "${visit.occurredAt} · ${visit.personCount} detected · Photo expired"
                            })
                        }
                    }
                }
            }
            Card {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Optional cloud visitor alerts", style = MaterialTheme.typography.titleMedium)
                    Text("Ring snapshots and face analysis are processed by AWS after the separate Ring connection consent. Firebase Cloud Messaging (FCM) receives only a generic visitor alert and visit link. It never receives a visitor name or image. Android may show the generic alert on the lock screen; open DoorMemo and unlock the tablet to review.")
                    Row {
                        Checkbox(checked = pushConsent, onCheckedChange = { accepted ->
                            pushConsent = accepted
                            FcmPushCoordinator(context).setConsent(accepted) { status = it }
                        })
                        Text("I agree to optional generic push alerts through FCM.")
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = onEnableAlerts, enabled = pushConsent && !busy) { Text("Enable alerts") }
                    }
                }
            }
            Card {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Stored and analyzed on this tablet")
                    Text("Encrypted records and photos • Android backups disabled • no audio input")
                    Text("Ring links only through its hosted account-link and consent flow. Local image imports are analyzed on this tablet. Face counts do not count people whose faces are hidden.")
                    Text("Unsaved visit photos: ${retention.photoDays} days. Visit logs: ${retention.logDays} days. Saved visit photos last until their visit is deleted. Confirmed profile references remain until you delete the profile. Retention runs when you unlock the journal.")
                }
            }
            }
            if (selectedTab == 1) {
                Text("Ring events", style = MaterialTheme.typography.titleLarge)
                ringVisits.forEach { visit ->
                    RingVisitRow(visit, busy, selectedRingVisitId != null) { selectedRingVisitId = visit.visitId }
                }
                if (ringVisits.isEmpty()) Text(ringHistoryStatus, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            if (selectedTab == 1) {
            if (!consent) {
                Text("Before importing visitor photos")
                Row { Checkbox(age, { age = it }); Text("I am at least 13 years old.") }
                Row { Checkbox(lawful, { lawful = it }); Text("I will import and label only images I am permitted to use. Identity suggestions can be wrong.") }
                Button(enabled = age && lawful, onClick = {
                    preferences.edit().putBoolean("accepted_v1", true).putString("accepted_at", java.time.Instant.now().toString()).apply()
                    consent = true
                }) { Text("Enable private image imports") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onImport, enabled = consent && !busy) { Text("Import image") }
                OutlinedButton(onClick = { exportWarning = true }, enabled = consent && !busy && visits.isNotEmpty()) { Text("Export records") }
            }
            TextButton(onClick = onEnableAlerts, enabled = !busy) { Text("Enable Android notifications") }
            }
            if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            status?.let { Text(it, style = MaterialTheme.typography.bodyMedium) }
            if (selectedTab == 3) {
            Text("Owner retention settings", style = MaterialTheme.typography.titleMedium)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(photoDays, { if (it.length <= 3 && it.all(Char::isDigit)) photoDays = it },
                    modifier = Modifier.weight(1f), label = { Text("Photo days (1–365)") }, singleLine = true)
                OutlinedTextField(logDays, { if (it.length <= 4 && it.all(Char::isDigit)) logDays = it },
                    modifier = Modifier.weight(1f), label = { Text("Log days (1–3650)") }, singleLine = true)
            }
            Text("Applying a shorter window removes records already past that age. Saved profile references remain separate.", style = MaterialTheme.typography.bodySmall)
            OutlinedButton(enabled = !busy && (photoDays.toIntOrNull() ?: 0) in 1..365 && (logDays.toIntOrNull() ?: 0) in 1..3650,
                onClick = { perform {
                    val chosen = RetentionSettings(photoDays.toInt(), logDays.toInt())
                    records.updateRetention(chosen); records.applyRetention(); retention = chosen
                    "Retention settings saved and applied."
                } }) { Text("Apply retention") }
            }
            if (selectedTab == 1) {
            Text("Visit history", style = MaterialTheme.typography.titleLarge)
            if (visits.isEmpty()) Text("No private visits yet. Import a photo to review faces locally.")
            val pageStart = (visitPage * 20).coerceAtMost(((visits.size - 1).coerceAtLeast(0) / 20) * 20)
            if (visits.size > 20) Row {
                TextButton(enabled = pageStart > 0, onClick = { visitPage = pageStart / 20 - 1 }) { Text("Newer visits") }
                TextButton(enabled = pageStart + 20 < visits.size, onClick = { visitPage = pageStart / 20 + 1 }) { Text("Older visits") }
            }
            visits.drop(pageStart).take(20).forEach { record ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(record.visit.occurredAt)
                        Text("Source: ${record.visit.source} · ${record.people.size} detected face(s)")
                        Text("Owner-labelled direction: ${record.visit.eventType.takeIf { it in listOf("arrival", "departure", "visit") } ?: "unspecified"}")
                        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                            listOf("arrival", "departure", "visit").forEach { direction ->
                                TextButton(enabled = !busy, onClick = { perform { records.setVisitDirection(record.visit.id, direction); "Visit direction recorded by owner." } }) { Text(direction.replaceFirstChar { it.uppercase() }) }
                            }
                        }
                        Text("Import time is recorded; camera capture time is not verified.", style = MaterialTheme.typography.bodySmall)
                        if (record.people.isEmpty()) Text("Face undetected; number and identity of people unknown.")
                        record.people.forEach { person ->
                            PrivatePersonCard(person, profiles, records, busy) { operation -> perform(operation) }
                        }
                        TextButton(enabled = !busy, onClick = { perform { records.deleteVisit(record.visit.id); "Visit and its photos removed. Profile references are managed separately." } }) { Text("Delete visit") }
                    }
                }
            }
            }
            if (selectedTab == 2) {
            Text("Saved profiles", style = MaterialTheme.typography.titleLarge)
            profiles.forEach { profile ->
                ProfileEditor(profile, busy,
                    onRename = { label -> perform { records.correctProfile(profile.id, label); "Profile correction logged." } },
                    onDelete = { perform { records.deleteProfile(profile.id); "Profile and its biometric references removed." } })
            }
            Text("Owner activity · ${audit.size} entries", style = MaterialTheme.typography.titleLarge)
            audit.take(30).forEach { entry ->
                val profile = profiles.find { it.id == entry.profileId }
                Text("${entry.occurredAt} · ${entry.action}${profile?.let { " · ${it.name}" }.orEmpty()}\n${entry.detail}", style = MaterialTheme.typography.bodySmall)
            }
            }
        }
    }
}

@Composable
private fun DoorHomeCard(
    ringStatus: String,
    eventCount: Int,
    localCount: Int,
    refreshing: Boolean,
    onRefresh: () -> Unit,
    onActivity: () -> Unit,
    onPrivacy: () -> Unit,
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFF173B34)),
        shape = MaterialTheme.shapes.extraLarge,
    ) {
        Column(Modifier.fillMaxWidth().padding(22.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("A CALMER WAY TO KEEP TRACK", style = MaterialTheme.typography.labelLarge, color = Color(0xFFB6D7C8))
            Text("Your door,\nremembered.", style = MaterialTheme.typography.displaySmall, color = Color.White)
            Text(ringStatus, style = MaterialTheme.typography.bodyMedium, color = Color(0xFFE2EEE7))
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Button(
                    onClick = onRefresh,
                    enabled = !refreshing,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFF1BD70), contentColor = Color(0xFF19231F)),
                ) { Text(if (refreshing) "Checking" else "Check events") }
                TextButton(onClick = onPrivacy) { Text("Privacy", color = Color.White) }
            }
            HorizontalDivider(color = Color(0xFF45655B))
            Row(horizontalArrangement = Arrangement.spacedBy(22.dp), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Column {
                    Text("$eventCount", style = MaterialTheme.typography.titleLarge, color = Color.White)
                    Text("Ring events", style = MaterialTheme.typography.bodySmall, color = Color(0xFFB6D7C8))
                }
                Column {
                    Text("$localCount", style = MaterialTheme.typography.titleLarge, color = Color.White)
                    Text("On this tablet", style = MaterialTheme.typography.bodySmall, color = Color(0xFFB6D7C8))
                }
                TextButton(onClick = onActivity) { Text("View all") }
            }
        }
    }
}

@Composable
private fun RingVisitRow(
    visit: RingVisitHistoryItem,
    busy: Boolean,
    anotherVisitOpen: Boolean,
    onClick: () -> Unit,
) {
    Card(
        onClick = onClick,
        enabled = !busy && !anotherVisitOpen && visit.snapshotAvailable,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = MaterialTheme.shapes.large,
    ) {
        Row(
            Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
        ) {
            Surface(
                color = MaterialTheme.colorScheme.primaryContainer,
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.size(48.dp),
            ) {
                Box(contentAlignment = androidx.compose.ui.Alignment.Center) {
                    Icon(Icons.Rounded.Groups, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                }
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(visit.eventType.replace('_', ' ').replaceFirstChar { it.uppercase() }, style = MaterialTheme.typography.titleMedium)
                Text("${visit.personCount} detected · ${visit.occurredAt}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(
                    if (visit.snapshotAvailable) "Still image ready to review" else "Photo expired · log retained",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Text("›", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
        }
    }
}

private data class CloudRingVisitSnapshot(
    val bitmap: Bitmap,
    val eventType: String,
    val occurredAt: String,
    val personCount: Int,
    val people: List<CloudRingPerson>,
)

private data class CloudRingPerson(
    val personId: String,
    val bitmap: Bitmap?,
    val ownerLabel: String,
)

private data class RingVisitHistoryItem(
    val visitId: String,
    val eventType: String,
    val occurredAt: String,
    val personCount: Int,
    val status: String,
    val snapshotAvailable: Boolean,
)

private fun fetchRingVisitHistory(container: AppContainer): List<RingVisitHistoryItem> {
    val token = container.sessionProvider.currentSession().accessToken
        ?: error("Owner sign-in is required")
    val request = Request.Builder()
        .url("${BuildConfig.API_BASE_URL.trimEnd('/')}/v1/ring/visits?limit=30&offset=0")
        .header("Authorization", "Bearer $token")
        .get()
        .build()
    val payload = OkHttpClient().newCall(request).execute().use { response ->
        check(response.isSuccessful) { "Ring visit history request failed" }
        JSONObject(response.body?.string().orEmpty())
    }
    val visits = payload.optJSONArray("visits") ?: return emptyList()
    return (0 until visits.length()).mapNotNull { index ->
        val item = visits.optJSONObject(index) ?: return@mapNotNull null
        val visitId = item.optString("visit_id")
        if (!visitId.matches(Regex("^[0-9a-fA-F-]{36}$"))) return@mapNotNull null
        RingVisitHistoryItem(
            visitId = visitId,
            eventType = item.optString("event_type", "visitor event"),
            occurredAt = item.optString("occurred_at", "time unavailable"),
            personCount = item.optInt("person_count", 0).coerceAtLeast(0),
            status = item.optString("status", "processing"),
            snapshotAvailable = item.optBoolean("snapshot_available", false),
        )
    }
}

@Composable
private fun CloudRingVisitReview(container: AppContainer, visitId: String, onClose: () -> Unit) {
    var result by remember(visitId) { mutableStateOf<CloudRingVisitSnapshot?>(null) }
    var message by remember(visitId) { mutableStateOf("Loading this Ring still snapshot securely.") }
    var labels by remember(visitId) { mutableStateOf<Map<String, String>>(emptyMap()) }
    var savedLabels by remember(visitId) { mutableStateOf<Map<String, String>>(emptyMap()) }
    var savingPerson by remember(visitId) { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    LaunchedEffect(visitId) {
        val loaded = runCatching { withContext(Dispatchers.IO) { fetchRingVisitSnapshot(container, visitId) } }
        loaded.onSuccess {
            result = it
            labels = it.people.associate { person -> person.personId to person.ownerLabel }
            savedLabels = it.people.associate { person -> person.personId to person.ownerLabel }
            message = "Review each detected face. Labels apply to this visit only."
        }.onFailure {
            message = "This Ring visit could not be loaded. Sign in again or reopen the alert while online."
        }
    }
    DisposableEffect(result) {
        val bitmap = result?.bitmap
        val crops = result?.people.orEmpty().mapNotNull { it.bitmap }
        onDispose { bitmap?.recycle(); crops.forEach { it.recycle() } }
    }
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text("Ring visitor snapshot") },
        text = {
            Column(
                Modifier.heightIn(max = 500.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                result?.let { snapshot ->
                    Image(snapshot.bitmap.asImageBitmap(), "Private Ring visitor still snapshot", Modifier.fillMaxWidth())
                    Text("${snapshot.eventType} · ${snapshot.occurredAt}")
                    Text(if (snapshot.personCount > 0) {
                        "${snapshot.personCount} face(s) detected. Matches are suggestions only; identity is not verified."
                    } else {
                        "Face undetected. The number and identity of people are unknown."
                    })
                    snapshot.people.forEach { person ->
                        HorizontalDivider()
                        person.bitmap?.let {
                            Image(it.asImageBitmap(), "Detected face for owner review", Modifier.size(120.dp))
                        }
                        Text(if (!savedLabels[person.personId].isNullOrBlank()) {
                            "Owner reviewed label for this visit: ${savedLabels[person.personId]}"
                        } else "Identity unknown · owner review required")
                        OutlinedTextField(
                            value = labels[person.personId].orEmpty(),
                            onValueChange = { value ->
                                if (value.length <= 120) labels = labels + (person.personId to value)
                            },
                            label = { Text("Name for this visit only") },
                            singleLine = true,
                            enabled = savingPerson == null,
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(
                                enabled = savingPerson == null && !labels[person.personId].isNullOrBlank(),
                                onClick = {
                                    val label = labels[person.personId].orEmpty().trim()
                                    scope.launch {
                                        savingPerson = person.personId
                                        message = runCatching {
                                            withContext(Dispatchers.IO) {
                                                saveRingVisitPersonReview(container, visitId, person.personId, label)
                                            }
                                        }.getOrElse { "Review could not be saved. Sign in again and retry." }
                                        if (message.startsWith("Owner-confirmed")) {
                                            savedLabels = savedLabels + (person.personId to label)
                                        }
                                        savingPerson = null
                                    }
                                },
                            ) { Text("Save visit label") }
                            TextButton(
                                enabled = savingPerson == null &&
                                    (!savedLabels[person.personId].isNullOrBlank() ||
                                        !labels[person.personId].isNullOrBlank()),
                                onClick = {
                                    scope.launch {
                                        savingPerson = person.personId
                                        message = runCatching {
                                            withContext(Dispatchers.IO) {
                                                saveRingVisitPersonReview(container, visitId, person.personId, "")
                                            }
                                        }.getOrElse { "Review could not be cleared. Sign in again and retry." }
                                        if (message.startsWith("Owner label cleared")) {
                                            labels = labels + (person.personId to "")
                                            savedLabels = savedLabels + (person.personId to "")
                                        }
                                        savingPerson = null
                                    }
                                },
                            ) { Text("Keep unknown") }
                        }
                    }
                }
                Text(message)
                Text("This is one still image. DoorMemo does not retrieve video clips.", style = MaterialTheme.typography.bodySmall)
                Text("Labels are saved only on this visit. They do not enroll face templates or enable automatic identity alerts.", style = MaterialTheme.typography.bodySmall)
            }
        },
        confirmButton = { TextButton(onClick = onClose) { Text("Close") } },
    )
}

private fun fetchRingVisitSnapshot(container: AppContainer, visitId: String): CloudRingVisitSnapshot {
    require(visitId.matches(Regex("^[0-9a-fA-F-]{36}$")))
    val token = container.sessionProvider.currentSession().accessToken
        ?: error("Owner sign-in is required")
    val http = OkHttpClient()
    val baseUrl = BuildConfig.API_BASE_URL.trimEnd('/')
    val metadataRequest = Request.Builder()
        .url("$baseUrl/v1/ring/visits/$visitId")
        .header("Authorization", "Bearer $token")
        .get()
        .build()
    val metadata = http.newCall(metadataRequest).execute().use { response ->
        check(response.isSuccessful) { "Ring visit request failed" }
        JSONObject(response.body?.string().orEmpty())
    }
    val imageUrl = Uri.parse(metadata.getString("snapshot_url"))
    require(imageUrl.scheme == "https" && imageUrl.host != null) { "Secure snapshot URL is required" }
    val imageRequest = Request.Builder().url(imageUrl.toString()).get().build()
    val imageBytes = http.newCall(imageRequest).execute().use { response ->
        check(response.isSuccessful && (response.body?.contentLength() ?: -1L) <= 8L * 1024 * 1024) {
            "Ring snapshot download failed"
        }
        response.body?.bytes() ?: error("Ring snapshot is empty")
    }
    check(imageBytes.size <= 8 * 1024 * 1024)
    val bitmap = try { BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size) }
    finally { imageBytes.fill(0) }
    val peopleRequest = Request.Builder()
        .url("$baseUrl/v1/ring/visits/$visitId/people")
        .header("Authorization", "Bearer $token")
        .get()
        .build()
    val peoplePayload = http.newCall(peopleRequest).execute().use { response ->
        check(response.isSuccessful) { "Ring person review request failed" }
        JSONObject(response.body?.string().orEmpty())
    }
    val peopleJson = peoplePayload.optJSONArray("people")
    val people = (0 until (peopleJson?.length() ?: 0)).mapNotNull { index ->
        val person = peopleJson?.optJSONObject(index) ?: return@mapNotNull null
        val personId = person.optString("person_id")
        if (!personId.matches(Regex("^[0-9a-fA-F-]{36}-[A-Za-z0-9_-]{1,80}$"))) return@mapNotNull null
        val cropUrl = Uri.parse(person.optString("crop_url").takeIf { it.isNotBlank() })
        val crop = if (cropUrl.scheme == "https" && cropUrl.host != null) {
            val bytes = http.newCall(Request.Builder().url(cropUrl.toString()).get().build())
                .execute().use { response ->
                    check(response.isSuccessful && (response.body?.contentLength() ?: -1L) <= 2L * 1024 * 1024) {
                        "Ring face crop download failed"
                    }
                    response.body?.bytes() ?: error("Ring face crop is empty")
                }
            try {
                check(bytes.size <= 2 * 1024 * 1024)
                BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            } finally { bytes.fill(0) }
        } else null
        CloudRingPerson(personId, crop, person.optString("owner_reviewed_label"))
    }
    return CloudRingVisitSnapshot(
        bitmap = bitmap ?: error("Ring snapshot image is invalid"),
        eventType = metadata.optString("event_type", "visitor event"),
        occurredAt = metadata.optString("occurred_at", "time unavailable"),
        personCount = metadata.optInt("person_count", 0),
        people = people,
    )
}

private fun saveRingVisitPersonReview(
    container: AppContainer,
    visitId: String,
    personId: String,
    label: String,
): String {
    require(visitId.matches(Regex("^[0-9a-fA-F-]{36}$")))
    require(personId.matches(Regex("^[0-9a-fA-F-]{36}-[A-Za-z0-9_-]{1,80}$")))
    require(label.length <= 120)
    val token = container.sessionProvider.currentSession().accessToken
        ?: error("Owner sign-in is required")
    val body = JSONObject().put("label", label).toString()
        .toRequestBody("application/json".toMediaType())
    val request = Request.Builder()
        .url("${BuildConfig.API_BASE_URL.trimEnd('/')}/v1/ring/visits/$visitId/people/$personId/review")
        .header("Authorization", "Bearer $token")
        .post(body)
        .build()
    val result = OkHttpClient().newCall(request).execute().use { response ->
        check(response.isSuccessful) { "Ring person review update failed" }
        JSONObject(response.body?.string().orEmpty())
    }
    return if (result.optString("review_state") == "owner_confirmed") {
        "Owner-confirmed label saved for this visit."
    } else "Owner label cleared; identity remains unknown."
}

@Composable
private fun PrivatePersonCard(
    person: PersonEntity,
    profiles: List<ProfileEntity>,
    records: PrivateRecordsRepository,
    busy: Boolean,
    perform: (suspend () -> String) -> Unit,
) {
    val image by produceState<android.graphics.Bitmap?>(null, person.id, person.mediaAvailable) {
        value = withContext(Dispatchers.IO) {
            runCatching {
                records.faceImage(person.id)?.let { bytes ->
                    try { BitmapFactory.decodeByteArray(bytes, 0, bytes.size) } finally { bytes.fill(0) }
                }
            }.getOrNull()
        }
    }
    val visibleBitmap = image
    DisposableEffect(visibleBitmap) { onDispose { visibleBitmap?.recycle() } }
    var label by remember(person.id) { mutableStateOf("") }
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        image?.let { Image(it.asImageBitmap(), "Detected face for owner review", Modifier.size(140.dp)) }
        val confirmed = profiles.find { it.id == person.confirmedProfileId }
        Text(if (confirmed != null) "Owner confirmed: ${confirmed.name}" else "Identity unknown · owner review required")
        if (confirmed != null) {
            TextButton(enabled = !busy, onClick = { perform { records.markUnknown(person.id); "Identity cleared and its enrolled reference removed. Review this person again." } }) { Text("Correct identity") }
        }
        if (!person.mediaAvailable) Text("Photo expired or removed; this visit log is retained.")
        val suggested = profiles.find { it.id == person.suggestedProfileId }
        if (suggested != null && confirmed == null) {
            Text("Possible match: ${suggested.name}. Confirm only if you recognize this person.")
            Button(enabled = !busy, onClick = { perform { records.confirmIdentity(person.id, suggested.id); "Owner-confirmed match saved." } }) { Text("Confirm possible match") }
        }
        if (confirmed == null && person.mediaAvailable) {
            TextButton(enabled = !busy, onClick = { perform { records.markUnknown(person.id); "Marked unknown; no identity reference enrolled." } }) { Text("Keep identity unknown") }
            OutlinedTextField(value = label, onValueChange = { if (it.length <= 120) label = it }, label = { Text("Profile label (optional)") }, singleLine = true)
            Button(enabled = !busy, onClick = { perform { records.confirmIdentity(person.id, label = label); "Profile saved. Future matches still require confirmation." } }) { Text("Save new profile") }
            profiles.forEach { profile ->
                TextButton(enabled = !busy, onClick = { perform { records.confirmIdentity(person.id, profile.id); "Identity confirmed by owner." } }) { Text("Assign ${profile.name}") }
            }
        }
        if (person.mediaAvailable && !person.saved) TextButton(enabled = !busy, onClick = { perform { records.savePhoto(person.id); "Visit photo saved until this visit is deleted." } }) { Text("Keep this visit photo") }
    }
}

@Composable
private fun ProfileEditor(profile: ProfileEntity, busy: Boolean, onRename: (String) -> Unit, onDelete: () -> Unit) {
    var label by remember(profile.id, profile.name) { mutableStateOf(profile.name) }
    var deleting by remember { mutableStateOf(false) }
    if (deleting) AlertDialog(onDismissRequest = { deleting = false }, title = { Text("Delete profile?") },
        text = { Text("Remove this label and its saved face references. Existing visits lose this identity association.") },
        dismissButton = { TextButton(onClick = { deleting = false }) { Text("Cancel") } },
        confirmButton = { TextButton(onClick = { deleting = false; onDelete() }) { Text("Delete profile") } })
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp)) {
            Text("${profile.sampleCount} owner-approved reference(s)")
            OutlinedTextField(label, { if (it.length <= 120) label = it }, label = { Text("Profile label") }, singleLine = true)
            Row {
                TextButton(enabled = !busy && label.isNotBlank() && label != profile.name, onClick = { onRename(label) }) { Text("Save correction") }
                TextButton(enabled = !busy, onClick = { deleting = true }) { Text("Delete profile") }
            }
        }
    }
}
