package com.knockknock.feature.timeline

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AddAlert
import androidx.compose.material.icons.rounded.BookmarkAdded
import androidx.compose.material.icons.rounded.BrokenImage
import androidx.compose.material.icons.rounded.ChevronRight
import androidx.compose.material.icons.rounded.Groups
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.knockknock.core.model.ReviewState
import com.knockknock.core.model.TimelineFilter
import com.knockknock.core.model.VisitSummary
import com.knockknock.core.ui.Amber
import com.knockknock.core.ui.LearningBanner
import com.knockknock.core.ui.OfflineBadge
import com.knockknock.core.ui.Pine
import com.knockknock.core.ui.StatusPill
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@Composable
fun TimelineRoute(
    viewModel: TimelineViewModel,
    onVisitClick: (String) -> Unit,
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    TimelineScreen(
        state = state,
        onFilterSelected = viewModel::selectFilter,
        onRefresh = viewModel::refresh,
        onRunDemo = viewModel::runDemo,
        onDismissMessage = viewModel::dismissMessage,
        onVisitClick = onVisitClick,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TimelineScreen(
    state: TimelineUiState,
    onFilterSelected: (TimelineFilter) -> Unit,
    onRefresh: () -> Unit,
    onRunDemo: () -> Unit,
    onDismissMessage: () -> Unit,
    onVisitClick: (String) -> Unit,
) {
    val snackbar = remember { SnackbarHostState() }
    LaunchedEffect(state.message) {
        state.message?.let {
            snackbar.showSnackbar(it)
            onDismissMessage()
        }
    }
    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Knock Knock", style = MaterialTheme.typography.titleLarge)
                        Text(
                            "Know who's at the door",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                },
                actions = {
                    IconButton(onClick = onRefresh) {
                        Icon(Icons.Rounded.Refresh, contentDescription = "Refresh visits")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background,
                ),
            )
        },
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(start = 18.dp, end = 18.dp, top = 8.dp, bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item { LearningBanner() }
            if (state.isOffline) {
                item { OfflineBadge() }
            }
            item {
                FilterRow(state.selectedFilter, onFilterSelected)
            }
            if (state.isLoading && state.visits.isEmpty()) {
                item { LoadingState() }
            } else if (state.visits.isEmpty()) {
                item { EmptyTimeline(onRunDemo) }
            } else {
                item {
                    Text(
                        "Recent visits",
                        style = MaterialTheme.typography.headlineSmall,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                }
                items(state.visits, key = VisitSummary::id) { visit ->
                    VisitCard(visit = visit, onClick = { onVisitClick(visit.id) })
                }
            }
        }
    }
}

@Composable
private fun FilterRow(
    selected: TimelineFilter,
    onFilterSelected: (TimelineFilter) -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        TimelineFilter.entries.forEach { filter ->
            FilterChip(
                selected = selected == filter,
                onClick = { onFilterSelected(filter) },
                label = { Text(filter.label) },
            )
        }
    }
}

@Composable
private fun EmptyTimeline(onRunDemo: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(26.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 26.dp, vertical = 34.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Icon(
                Icons.Rounded.AddAlert,
                contentDescription = null,
                tint = Pine,
                modifier = Modifier.size(44.dp),
            )
            Spacer(Modifier.height(16.dp))
            Text("Your front-door story starts here", style = MaterialTheme.typography.titleLarge)
            Spacer(Modifier.height(8.dp))
            Text(
                "Wait for Ring activity or load the private three-person demo. " +
                    "Nothing is identified without your household's review.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(22.dp))
            Button(
                onClick = onRunDemo,
                colors = ButtonDefaults.buttonColors(containerColor = Pine),
            ) {
                Text("Run demo event")
            }
        }
    }
}

@Composable
private fun LoadingState() {
    Box(
        modifier = Modifier.fillMaxWidth().padding(48.dp),
        contentAlignment = Alignment.Center,
    ) {
        CircularProgressIndicator(color = Pine)
    }
}

@Composable
private fun VisitCard(visit: VisitSummary, onClick: () -> Unit) {
    val formatter = remember {
        DateTimeFormatter.ofPattern("EEE, MMM d · h:mm a").withZone(ZoneId.systemDefault())
    }
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
    ) {
        Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(13.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f)) {
                    Text("Front door", style = MaterialTheme.typography.titleLarge)
                    Text(
                        formatter.format(visit.occurredAt),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Icon(Icons.Rounded.ChevronRight, contentDescription = "Open visit")
            }
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(9.dp),
            ) {
                Icon(Icons.Rounded.Groups, contentDescription = null, tint = Pine)
                Text(
                    "${visit.personCount} people detected",
                    style = MaterialTheme.typography.titleMedium,
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                val unresolved = visit.people.count {
                    it.reviewState == ReviewState.UNRESOLVED || it.reviewState == ReviewState.PROPOSED
                }
                if (unresolved > 0) StatusPill("$unresolved need review", Amber, Pine)
                if (visit.hasSavedPhoto) {
                    StatusPill("Saved photo")
                }
            }
            if (visit.labels.isNotEmpty()) {
                Text(
                    visit.labels.joinToString(" · "),
                    style = MaterialTheme.typography.bodyLarge,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                if (visit.hasExpiredPhoto) {
                    Icon(
                        Icons.Rounded.BrokenImage,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                        tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        "Photo expired · visit log retained",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                } else if (visit.hasSavedPhoto) {
                    Icon(
                        Icons.Rounded.BookmarkAdded,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                        tint = Pine,
                    )
                    Text("Photo saved", style = MaterialTheme.typography.bodyMedium)
                } else {
                    Text(
                        "Photos expire after 30 days unless saved",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}
