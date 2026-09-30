package com.knockknock.feature.review

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.Lock
import androidx.compose.material.icons.rounded.Person
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.knockknock.core.model.FamiliarProfile
import com.knockknock.core.model.HouseholdRole
import com.knockknock.core.model.PersonSummary
import com.knockknock.core.model.ProfileProposal
import com.knockknock.core.model.ProposalStatus
import com.knockknock.core.model.ReviewState

@Composable
fun VisitReviewRoute(
    viewModel: ReviewViewModel,
    onBack: () -> Unit,
    onOpenApprovals: () -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    VisitReviewScreen(
        state = state,
        onBack = onBack,
        onOpenApprovals = onOpenApprovals,
        onRole = viewModel::setRole,
        onUnknown = viewModel::markUnknown,
        onFaceUndetected = viewModel::markFaceUndetected,
        onConfirm = viewModel::confirm,
        onSavePhoto = viewModel::savePhoto,
        onPropose = viewModel::propose,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VisitReviewScreen(
    state: VisitReviewUiState,
    onBack: () -> Unit,
    onOpenApprovals: () -> Unit,
    onRole: (HouseholdRole) -> Unit,
    onUnknown: (String) -> Unit,
    onFaceUndetected: (String) -> Unit,
    onConfirm: (String, FamiliarProfile) -> Unit,
    onSavePhoto: (String) -> Unit,
    onPropose: (String, String) -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Review this visit") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = onOpenApprovals) {
                        Icon(Icons.Rounded.History, contentDescription = "Approvals and history")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            RoleSelector(state.role, onRole)
            Text(
                text = "${state.visit?.personCount ?: 0} people detected",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
            )
            Text(
                "AI suggestions are clues, not facts. Confirm each person to help Knock Knock learn.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            state.visit?.people?.forEachIndexed { index, person ->
                PersonReviewCard(
                    index = index,
                    person = person,
                    profiles = state.profiles,
                    onUnknown = { onUnknown(person.id) },
                    onFaceUndetected = { onFaceUndetected(person.id) },
                    onConfirm = { onConfirm(person.id, it) },
                    onSavePhoto = { onSavePhoto(person.id) },
                    onPropose = { onPropose(person.id, it) },
                )
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}

@Composable
private fun RoleSelector(role: HouseholdRole, onRole: (HouseholdRole) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text("Demo household role", style = MaterialTheme.typography.labelLarge)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(
                selected = role == HouseholdRole.MEMBER,
                onClick = { onRole(HouseholdRole.MEMBER) },
                label = { Text("Member") },
            )
            FilterChip(
                selected = role == HouseholdRole.OWNER,
                onClick = { onRole(HouseholdRole.OWNER) },
                label = { Text("Ring owner") },
                leadingIcon = { Icon(Icons.Rounded.Lock, contentDescription = null) },
            )
        }
    }
}

@Composable
private fun PersonReviewCard(
    index: Int,
    person: PersonSummary,
    profiles: List<FamiliarProfile>,
    onUnknown: () -> Unit,
    onFaceUndetected: () -> Unit,
    onConfirm: (FamiliarProfile) -> Unit,
    onSavePhoto: () -> Unit,
    onPropose: (String) -> Unit,
) {
    var name by remember(person.id) { mutableStateOf("") }
    val suggestions = remember(name, profiles) {
        profiles.filter { name.isNotBlank() && it.name.contains(name, ignoreCase = true) }
    }
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(2.dp),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .background(MaterialTheme.colorScheme.secondaryContainer, RoundedCornerShape(16.dp))
                        .padding(14.dp),
                ) { Icon(Icons.Rounded.Person, contentDescription = null) }
                Column(Modifier.padding(start = 12.dp)) {
                    Text("Person ${index + 1}", style = MaterialTheme.typography.titleLarge)
                    Text(
                        person.reviewState.wireValue.replace('_', ' '),
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
            val suggestedName = person.suggestedName
            if (suggestedName != null) {
                Text(suggestedName, style = MaterialTheme.typography.titleMedium)
                Text(
                    "High-confidence suggestion · ${(person.similarity * 100).toInt()}% · confirmation required",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                profiles.firstOrNull { it.id == person.suggestedProfileId }?.let { profile ->
                    Button(onClick = { onConfirm(profile) }) { Text("Confirm ${profile.name}") }
                }
            } else if (!person.mediaAvailable) {
                Text("Photo expired · visit log retained", color = MaterialTheme.colorScheme.onSurfaceVariant)
            } else {
                Text("No reliable match", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Row(
                modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                AssistChip(onClick = onUnknown, label = { Text("Unknown") })
                AssistChip(onClick = onFaceUndetected, label = { Text("Face undetected") })
                AssistChip(
                    onClick = onSavePhoto,
                    label = { Text(if (person.saved) "Photo saved" else "Save photo") },
                )
            }
            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Search or name this person") },
                singleLine = true,
            )
            suggestions.forEach { profile ->
                TextButton(onClick = { onConfirm(profile) }) {
                    Text("Use existing profile: ${profile.name} (${profile.sampleCount} photos)")
                }
            }
            OutlinedButton(
                onClick = { onPropose(name); name = "" },
                enabled = name.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Submit profile proposal") }
        }
    }
}

@Composable
fun ApprovalRoute(viewModel: ApprovalViewModel, onBack: () -> Unit) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    ApprovalScreen(state, onBack, viewModel::setRole, viewModel::decide)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ApprovalScreen(
    state: ApprovalUiState,
    onBack: () -> Unit,
    onRole: (HouseholdRole) -> Unit,
    onDecision: (ProfileProposal, Boolean) -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Approvals & history") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            RoleSelector(state.role, onRole)
            Text("Owner approval queue", style = MaterialTheme.typography.headlineSmall)
            if (state.proposals.none { it.status == ProposalStatus.PENDING }) {
                Text("No proposals waiting", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            state.proposals.filter { it.status == ProposalStatus.PENDING }.forEach { proposal ->
                Card {
                    Column(Modifier.fillMaxWidth().padding(16.dp), Arrangement.spacedBy(8.dp)) {
                        Text(proposal.proposedName, style = MaterialTheme.typography.titleLarge)
                        Text("Proposed by ${proposal.proposer}")
                        if (state.role == HouseholdRole.OWNER) {
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Button(onClick = { onDecision(proposal, true) }) { Text("Approve") }
                                OutlinedButton(onClick = { onDecision(proposal, false) }) { Text("Reject") }
                            }
                        } else {
                            Text("Only the Ring account owner can decide.", color = MaterialTheme.colorScheme.primary)
                        }
                    }
                }
            }
            Text("Immutable modification history", style = MaterialTheme.typography.headlineSmall)
            state.audit.forEach { entry ->
                Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFF1F4EE))) {
                    Column(Modifier.fillMaxWidth().padding(14.dp), Arrangement.spacedBy(3.dp)) {
                        Text(entry.action.replace('_', ' '), fontWeight = FontWeight.Bold)
                        Text(entry.detail)
                        Text(
                            "${entry.actor} · ${entry.occurredAt}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }
    }
}
