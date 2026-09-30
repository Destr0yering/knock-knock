package com.knockknock.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.knockknock.core.ui.KnockKnockTheme
import com.knockknock.feature.timeline.TimelineRoute
import com.knockknock.feature.timeline.TimelineViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val container = (application as KnockKnockApplication).container
        setContent {
            KnockKnockTheme {
                val timelineViewModel: TimelineViewModel = viewModel(
                    factory = container.timelineViewModelFactory,
                )
                KnockKnockNavHost(timelineViewModel)
            }
        }
    }
}

@Composable
private fun KnockKnockNavHost(timelineViewModel: TimelineViewModel) {
    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = "timeline") {
        composable("timeline") {
            TimelineRoute(
                viewModel = timelineViewModel,
                onVisitClick = { visitId -> navController.navigate("visit/$visitId") },
            )
        }
        composable(
            route = "visit/{visitId}",
            arguments = listOf(navArgument("visitId") { type = NavType.StringType }),
        ) { entry ->
            FoundationVisitScreen(
                visitId = entry.arguments?.getString("visitId").orEmpty(),
                onBack = navController::popBackStack,
            )
        }
    }
}

@Composable
@OptIn(ExperimentalMaterial3Api::class)
private fun FoundationVisitScreen(visitId: String, onBack: () -> Unit) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Visit details") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Review screen coming next", style = MaterialTheme.typography.headlineSmall)
            Text(
                "Cached visit: $visitId",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
